"""Data Platform Forecast Streamlit Page Main Code."""

import asyncio
import os
import dataclasses
import datetime

import pandas as pd
import streamlit as st
import grpc.aio
from ocf.dp.dp import common_pb2
from ocf.dp.dp_data import service_pb2_grpc

from dataplatform.forecast.constant import (
    metrics,
    observer_names,
    t0_chart_min_height,
    t0_chart_screen_fraction,
    theme_background,
)
from dataplatform.forecast.backend import (
    fetch_observations,
    fetch_timeseries,
    fetch_all_forecasts,
)
from dataplatform.forecast.plot import (
    plot_forecast_metric_per_day,
    plot_forecast_metric_vs_horizon_minutes,
    plot_forecast_time_series,
    plot_forecast_time_series_by_t0,
    make_summary_data,
    make_summary_data_metric_vs_horizon_minutes,
    plot_quantile_plot
)
from dataplatform.forecast.setup import setup_page

data_platform_host = os.getenv("DATA_PLATFORM_HOST", "localhost")
data_platform_port = int(os.getenv("DATA_PLATFORM_PORT", "50051"))


def render_animated_chart(fig) -> None:
    """Render a figure that uses Plotly animation frames, inside an iframe.

    st.plotly_chart persists the figure to Streamlit element state on every update and
    re-reads it when the component remounts (e.g. toggling fullscreen). Animation frames
    don't survive that round trip, so the slider silently stops redrawing. Rendering the
    figure as standalone HTML keeps the frames registered with Plotly directly.
    """
    chart_html = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        auto_play=False,
        default_height="100%",
        config={"displaylogo": False, "responsive": True},
    )
    # Size the chart to a fraction of the viewer's screen so it fits laptops and big monitors
    # alike. window.innerHeight is the iframe's own height here (circular), so we key off
    # window.screen.availHeight, which is readable cross-origin. st.iframe(height="content")
    # then tracks the resulting height via its ResizeObserver.
    sizing_script = f"""
    <script>
    (function () {{
      function sizeChart() {{
        var gd = document.querySelector('.plotly-graph-div');
        if (!gd || !window.Plotly) {{ return false; }}
        var target = Math.max(
          {t0_chart_min_height},
          Math.round(window.screen.availHeight * {t0_chart_screen_fraction})
        );
        window.Plotly.relayout(gd, {{height: target}});
        return true;
      }}
      // Plotly (from the CDN) and the graph div may not exist yet, so retry briefly.
      var tries = 0;
      var timer = setInterval(function () {{
        if (sizeChart() || ++tries > 40) {{ clearInterval(timer); }}
      }}, 50);
      window.addEventListener('resize', sizeChart);
    }})();
    </script>
    """
    st.iframe(
        f'<html><head><meta charset="utf-8"></head>'
        f'<body style="margin:0;background-color:{theme_background};">'
        f"{chart_html}{sizing_script}</body></html>",
        height="content",
    )


def init_session_state():
    if "forecast_df" not in st.session_state:
        st.session_state.forecast_df = None
    if "observations_df" not in st.session_state:
        st.session_state.observations_df = None
    if "merged_metrics_df" not in st.session_state:
        st.session_state.merged_metrics_df = None
    if "fetch_time_stats" not in st.session_state:
        st.session_state.fetch_time_stats = ""
    if "locked_params" not in st.session_state:
        st.session_state.locked_params = None


def dp_forecast_page() -> None:
    """Wrapper function that is not async to call the main async function."""
    init_session_state()
    asyncio.run(async_dp_forecast_page())


async def async_dp_forecast_page() -> None:
    """Async Main function for the Data Platform Forecast Streamlit page."""
    st.title("Data Platform Forecast Page")
    st.write("This is the forecast page from the Data Platform module.")

    channel = grpc.aio.insecure_channel(f"{data_platform_host}:{data_platform_port}")
    client = service_pb2_grpc.DataPlatformDataServiceStub(channel)

    try:
        cfg = await setup_page(client)
        st.divider()
        st.subheader("View Forecasts & Observations")

        if st.button("Fetch Forecast & Observations", type="primary"):
            with st.spinner("Fetching data from gRPC API..."):
                start_time = datetime.datetime.now()

                df_forecast = await fetch_timeseries(
                    client=client,
                    location_uuid=cfg.location.location_uuid,
                    start_date=cfg.start_date,
                    end_date=cfg.end_date,
                    horizon_mins=cfg.forecast_horizon,
                    forecasters=cfg.forecasters,
                    init_times_utc=cfg.t0s,
                )

                df_obs = await fetch_observations(
                    client=client,
                    location_uuid=cfg.location.location_uuid,
                    start_date=cfg.start_date,
                    end_date=cfg.end_date,
                    observers=observer_names,
                    energy_source=common_pb2.EnergySource.ENERGY_SOURCE_SOLAR,
                )

                fetch_duration = (datetime.datetime.now() - start_time).total_seconds()

                st.session_state.forecast_df = df_forecast
                st.session_state.observations_df = df_obs
                st.session_state.merged_metrics_df = None  # Reset metrics on new fetch
                st.session_state.locked_config = dataclasses.replace(
                    cfg
                )  # Copy the config to a new instance

                st.session_state.fetch_time_stats = (
                    f"Fetched `{len(df_forecast)}` forecast rows "
                    f"in `{fetch_duration:.2f}` seconds."
                )

        if st.session_state.fetch_time_stats:
            st.success(st.session_state.fetch_time_stats)

        # Ensure we have data before trying to plot
        if (
            st.session_state.forecast_df is not None
            and not st.session_state.forecast_df.empty
        ):
            all_forecast_data_df = st.session_state.forecast_df
            all_observations_df = st.session_state.observations_df

            csv = all_forecast_data_df.to_csv().encode("utf-8")
            st.download_button(
                label="⬇️ Download Raw Forecast Data",
                data=csv,
                file_name=f"site_forecast_{cfg.location.location_uuid}_{cfg.start_date}_{cfg.end_date}.csv",
                mime="text/csv",
            )

            st.header("Time Series Plot")
            show_probabilistic = st.checkbox("Show Probabilistic Forecasts", value=True)

            lcfg = st.session_state.locked_config
            forecaster_names = list({f.forecaster_name for f in lcfg.forecasters})

            # Stepping through t0s one at a time only makes sense for the t0 forecast type,
            # where we have a forecast per initialisation time to step through.
            step_through_t0s = False
            if lcfg.forecast_type == "t0" and lcfg.t0s:
                step_through_t0s = st.checkbox(
                    "Step through t0s",
                    value=False,
                    help="Show one t0 at a time with a slider, to see how the forecast "
                    "evolved through the day.",
                )

            if step_through_t0s:
                show_trail = st.checkbox(
                    "Show faded trail of earlier t0s",
                    value=True,
                    help="Draws every earlier t0 faintly behind the current one, so drift "
                    "accumulates visibly.",
                )
                fig = plot_forecast_time_series_by_t0(
                    all_forecast_data_df=all_forecast_data_df,
                    all_observations_df=all_observations_df,
                    forecaster_names=forecaster_names,
                    observer_names=observer_names,
                    scale_factor=lcfg.scale_factor,
                    units=lcfg.units,
                    selected_t0s=lcfg.t0s,
                    show_probabilistic=show_probabilistic,
                    show_trail=show_trail,
                )
                render_animated_chart(fig)
            else:
                fig = plot_forecast_time_series(
                    all_forecast_data_df=all_forecast_data_df,
                    all_observations_df=all_observations_df,
                    forecaster_names=forecaster_names,
                    observer_names=observer_names,
                    scale_factor=lcfg.scale_factor,
                    units=lcfg.units,
                    selected_forecast_type=lcfg.forecast_type,
                    selected_forecast_horizon=lcfg.forecast_horizon,
                    selected_t0s=lcfg.t0s,
                    show_probabilistic=show_probabilistic,
                    strict_horizon_filtering=lcfg.strict_horizon_filtering,
                )
                st.plotly_chart(fig)

            st.divider()
            st.header("Accuracy & Metrics")
            st.write(
                "Calculating metrics requires fetching all the forecasts for the given time frame. It can take a while."
            )

            align_t0s_ui = st.checkbox(
                "Align t0s (Only common t0s across all forecaster are used)", value=True
            )

            if st.button("Calculate Metrics"):
                with st.spinner(
                    "Fetching data across all horizons and computing metrics..."
                ):
                    start_time = datetime.datetime.now(tz=datetime.UTC)
                    all_horizons_df = await fetch_all_forecasts(
                        client=client,
                        location_uuid=lcfg.location.location_uuid,
                        start_date=lcfg.start_date,
                        end_date=lcfg.end_date,
                        forecasters=lcfg.forecasters,
                    )
                    fetch_duration = (
                        datetime.datetime.now(tz=datetime.UTC) - start_time
                    ).total_seconds()
                    st.session_state.fetch_time_stats = (
                        f"Fetched `{len(all_horizons_df)}` forecast rows "
                        f"in `{fetch_duration:.2f}` seconds."
                    )
                    if st.session_state.fetch_time_stats:
                        st.success(st.session_state.fetch_time_stats)

                    merged_df = pd.merge(
                        all_horizons_df,
                        all_observations_df,
                        on="target_timestamp_utc",
                        suffixes=("", "_observation"),
                    )

                    if align_t0s_ui:
                        num_forecasters = merged_df["forecaster_name"].nunique()
                        # Count number of forecasters that have each t0 time
                        counts = merged_df.groupby("initialization_timestamp_utc")[
                            "forecaster_name"
                        ].nunique()
                        # Filter to just those t0s that all forecasters have
                        common_t0s = counts[counts == num_forecasters].index
                        merged_df = merged_df[merged_df["initialization_timestamp_utc"].isin(common_t0s)]

                    merged_df["error"] = (
                        merged_df["p50_watts"] - merged_df["value_watts"]
                    )
                    merged_df["absolute_error"] = merged_df["error"].abs()

                    st.session_state.merged_metrics_df = merged_df

            # Render Metrics if calculated
            if st.session_state.merged_metrics_df is not None:
                merged_df = st.session_state.merged_metrics_df

                st.write(metrics)
                st.subheader("Metric vs Forecast Horizon")

                show_sem = False
                if cfg.metric == "MAE":  # This is not locked on purpose
                    show_sem = st.checkbox(
                        "Show Uncertainty",
                        value=True,
                        help="Shows uncertainty bands associated with the MAE using SEM.",
                    )

                summary_df = make_summary_data_metric_vs_horizon_minutes(merged_df)

                fig2 = plot_forecast_metric_vs_horizon_minutes(
                    summary_df,
                    list({f.forecaster_name for f in lcfg.forecasters}),
                    cfg.metric,  # This is not locked on purpose
                    lcfg.scale_factor,
                    lcfg.units,
                    show_sem,
                )
                st.plotly_chart(fig2)

                csv_summary = summary_df.to_csv().encode("utf-8")
                st.download_button(
                    label="⬇️ Download Summary",
                    data=csv_summary,
                    file_name=f"summary_accuracy_{cfg.location.location_uuid}.csv",
                    mime="text/csv",
                )

                st.subheader("Summary Accuracy Table")
                if len(summary_df) > 0:
                    default_min_horizon = int(summary_df["horizon_mins"].min())
                    default_max_horizon = int(summary_df["horizon_mins"].max())
                else:
                    default_min_horizon, default_max_horizon = 0, 1440

                min_horizon, max_horizon = st.slider(
                    "Select Horizon Mins Range",
                    default_min_horizon,
                    default_max_horizon,
                    (default_min_horizon, default_max_horizon),
                    step=30,
                )

                summary_table_df = make_summary_data(
                    merged_df=merged_df,
                    min_horizon=min_horizon,
                    max_horizon=max_horizon,
                    scale_factor=lcfg.scale_factor,
                    units=lcfg.units,
                )
                st.dataframe(summary_table_df)

                st.subheader("Daily Metrics Plots")
                fig3 = plot_forecast_metric_per_day(
                    merged_df=merged_df,
                    forecaster_names=[f.forecaster_name for f in lcfg.forecasters],
                    scale_factor=lcfg.scale_factor,
                    units=lcfg.units,
                    selected_metric=cfg.metric,  # This is also not locked on purpose
                )
                st.plotly_chart(fig3)

                st.subheader("Quantile Plots")
                st.text("We plot the probability of the observed value being less than "
                         "the forecasted plevel value.")
                fig4 = plot_quantile_plot(
                    merged_df=merged_df,
                    forecaster_names=[f.forecaster_name for f in lcfg.forecasters],
                    )
                st.plotly_chart(fig4)

        else:
            st.info(
                "Configure your filters in the sidebar and click 'Fetch Forecast & Observations' to begin."
            )

    finally:
        await channel.close()
