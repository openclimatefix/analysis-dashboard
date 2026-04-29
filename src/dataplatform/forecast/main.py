"""Data Platform Forecast Streamlit Page Main Code."""

import asyncio
import os
import dataclasses
import datetime

import pandas as pd
import streamlit as st
from grpclib.client import Channel

from ocf import dp

from dataplatform.forecast.constant import metrics, observer_names
from dataplatform.forecast.plot import (
    plot_forecast_metric_per_day,
    plot_forecast_metric_vs_horizon_minutes,
    plot_forecast_time_series,
)
from dataplatform.forecast.setup import setup_page

data_platform_host = os.getenv("DATA_PLATFORM_HOST", "localhost")
data_platform_port = int(os.getenv("DATA_PLATFORM_PORT", "50051"))


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


async def fetch_timeseries(
    client: dp.DataPlatformDataServiceStub,
    location_uuid: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    horizon_mins: int,
    forecasters: list[dp.Forecaster],
    init_times_utc: list[datetime.datetime] | None = None,
) -> pd.DataFrame:
    """Directly calls GetForecastAsTimeseries for selected models and init times."""

    time_window = dp.TimeWindow(
        start_timestamp_utc=start_date, end_timestamp_utc=end_date
    )

    times_to_fetch = init_times_utc if init_times_utc else [None]

    async def fetch_one(
        forecaster_obj: dp.Forecaster, init_time: datetime.datetime | None
    ):
        req = dp.GetForecastAsTimeseriesRequest(
            location_uuid=location_uuid,
            energy_source=dp.EnergySource.SOLAR,
            horizon_mins=horizon_mins,
            time_window=time_window,
            forecaster=forecaster_obj,
            initialization_timestamp_utc=init_time,
        )

        try:
            resp = await client.get_forecast_as_timeseries(req)
            rows = []
            for val in resp.values:
                row = {
                    "target_timestamp_utc": val.target_timestamp_utc,
                    "initialization_timestamp_utc": val.initialization_timestamp_utc,
                    "created_timestamp_utc": val.created_timestamp_utc,
                    "effective_capacity_watts": val.effective_capacity_watts,
                    "forecaster_name": forecaster_obj.forecaster_name,
                    "location_uuid": resp.location_uuid,
                    "horizon_mins": (
                        val.target_timestamp_utc - val.initialization_timestamp_utc
                    ).total_seconds()
                    // 60,
                    "p50_watts": int(
                        val.p50_value_fraction * val.effective_capacity_watts
                    ),
                }

                if val.other_statistics_fractions:
                    row.update(
                        {
                            f"{k}_watts": int(v * val.effective_capacity_watts)
                            for k, v in val.other_statistics_fractions.items()
                        }
                    )
                rows.append(row)

            return rows
        except Exception as e:
            time_str = init_time.isoformat() if init_time else "Latest"
            st.error(
                f"Failed to fetch {forecaster_obj.forecaster_name} at {time_str}: {e}"
            )
            return []

    tasks = [fetch_one(f, t) for f in forecasters for t in times_to_fetch]

    results = await asyncio.gather(*tasks)
    all_rows = [item for sublist in results for item in sublist]

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df["target_timestamp_utc"] = pd.to_datetime(df["target_timestamp_utc"])
        if "initialization_timestamp_utc" in df.columns:
            df["initialization_timestamp_utc"] = pd.to_datetime(
                df["initialization_timestamp_utc"]
            )

    return df


async def fetch_observations(
    client: dp.DataPlatformDataServiceStub,
    location_uuid: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    observers: list[str],
    energy_source: dp.EnergySource = dp.EnergySource.SOLAR,
) -> pd.DataFrame:
    """Directly calls GetObservationsAsTimeseries for selected observers."""

    time_window = dp.TimeWindow(
        start_timestamp_utc=start_date, end_timestamp_utc=end_date
    )

    # Run requests concurrently for all selected observers
    async def fetch_one(obs_name: str):
        req = dp.GetObservationsAsTimeseriesRequest(
            location_uuid=location_uuid,
            observer_name=obs_name,
            energy_source=energy_source,
            time_window=time_window,
        )

        try:
            resp = await client.get_observations_as_timeseries(req)
            rows = []
            for val in resp.values:
                rows.append(
                    {
                        "target_timestamp_utc": val.timestamp_utc,
                        "value_fraction": val.value_fraction,
                        "effective_capacity_watts": val.effective_capacity_watts,
                        "observer_name": obs_name,
                        "location_uuid": resp.location_uuid,
                        "value_watts": int(
                            val.value_fraction * val.effective_capacity_watts
                        ),
                    }
                )
            return rows
        except Exception as e:
            st.error(f"Failed to fetch observations for {obs_name}: {e}")
            return []

    results = await asyncio.gather(*[fetch_one(obs) for obs in observers])
    all_rows = [item for sublist in results for item in sublist]

    df = pd.DataFrame(all_rows)

    if not df.empty:
        df["target_timestamp_utc"] = pd.to_datetime(df["target_timestamp_utc"])

    return df


def dp_forecast_page() -> None:
    """Wrapper function that is not async to call the main async function."""
    init_session_state()
    asyncio.run(async_dp_forecast_page())


async def async_dp_forecast_page() -> None:
    """Async Main function for the Data Platform Forecast Streamlit page."""
    st.title("Data Platform Forecast Page")
    st.write("This is the forecast page from the Data Platform module.")

    async with Channel(host=data_platform_host, port=data_platform_port) as channel:
        client = dp.DataPlatformDataServiceStub(channel)

        cfg = await setup_page(client)
        st.divider()
        st.subheader("1. Fetch Data")

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
                    energy_source=dp.EnergySource.SOLAR,
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

        # Display fetch stats if they exist
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
            fig = plot_forecast_time_series(
                all_forecast_data_df=all_forecast_data_df,
                all_observations_df=all_observations_df,
                forecaster_names=list({f.forecaster_name for f in lcfg.forecasters}),
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
                "Calculating metrics requires merging forecasts with observations. This is CPU intensive."
            )

            align_t0s_ui = st.checkbox(
                "Align t0s (Only common t0s across all forecaster are used)", value=True
            )

            if st.button("🧮 Calculate Metrics"):
                with st.spinner("Aligning data and computing metrics..."):
                    merged_df = pd.merge(
                        all_forecast_data_df,
                        all_observations_df,
                        on="target_timestamp_utc",
                        suffixes=("", "_observation"),
                    )

                    if align_t0s_ui:
                        merged_df = align_t0(merged_df)

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
                if cfg.metric == "MAE":
                    show_sem = st.checkbox(
                        "Show Uncertainty",
                        value=True,
                        help="Shows uncertainty bands associated with the MAE using SEM.",
                    )

                summary_df = make_summary_data_metric_vs_horizon_minutes(merged_df)

                fig2 = plot_forecast_metric_vs_horizon_minutes(
                    summary_df,
                    [f.forecaster_name for f in lcfg.forecasters],
                    lcfg.metric,
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
                    forecaster_names=list({f.forecaster_name for f in lcfg.forecasters}),
                    scale_factor=lcfg.scale_factor,
                    units=lcfg.units,
                    selected_metric=lcfg.metric,
                )
                st.plotly_chart(fig3)

        else:
            st.info(
                "Configure your filters in the sidebar and click 'Fetch Forecast & Observations' to begin."
            )


def make_summary_data(
    merged_df: pd.DataFrame,
    min_horizon: int,
    max_horizon: int,
    scale_factor: float,
    units: str,
) -> pd.DataFrame:
    """Make summary data table for given min and max horizon mins."""
    # Reduce by horizon mins
    summary_table_df = merged_df[
        (merged_df["horizon_mins"] >= min_horizon)
        & (merged_df["horizon_mins"] <= max_horizon)
    ]

    capacity_watts_col = "effective_capacity_watts"

    value_columns = [
        "error",
        "absolute_error",
        "value_watts",
        capacity_watts_col,
    ]
    plevels = [10, 25, 50, 75, 90]
    plevel_metrics = []
    for plevel in plevels:
        if f"p{plevel}_below" in summary_table_df.columns:
            plevel_metrics.append(f"p{plevel}_below")
            value_columns.append(f"p{plevel}_below")
    summary_table_df = summary_table_df[["forecaster_name", *value_columns]]

    summary_table_df = summary_table_df.groupby("forecaster_name").mean()

    # Scale by units
    non_plevel_columns = [
        col for col in summary_table_df.columns if col not in plevel_metrics
    ]
    summary_table_df[non_plevel_columns] = (
        summary_table_df[non_plevel_columns] / scale_factor
    )
    summary_table_df[plevel_metrics] = summary_table_df[plevel_metrics] * 100
    summary_table_df = summary_table_df.rename(
        {
            col: f"{col} [{units}]"
            for col in summary_table_df.columns
            if col not in plevel_metrics
        },
        axis=1,
    )
    summary_table_df = summary_table_df.rename(
        {
            col: f"{col} [%]"
            for col in summary_table_df.columns
            if col in plevel_metrics
        },
        axis=1,
    )

    # Pivot table, so forecaster_name is columns
    summary_table_df = summary_table_df.pivot_table(
        columns=summary_table_df.index,
        values=summary_table_df.columns.tolist(),
    )

    # Rename
    summary_table_df = summary_table_df.rename(
        columns={
            "error": "ME",
            "absolute_error": "MAE",
            capacity_watts_col: "Mean Capacity",
            "value_watts": "Mean Observed Generation",
        },
    )

    return summary_table_df


def make_summary_data_metric_vs_horizon_minutes(
    merged_df: pd.DataFrame,
) -> pd.DataFrame:
    """Make summary data for forecast metric vs horizon minutes."""
    # Get the mean observed generation
    mean_observed_generation = merged_df["value_watts"].mean()

    summary_df = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg(
            {
                "absolute_error": ["mean", "std", "count"],
                "error": "mean",
            },
        )
        .reset_index()
    )

    summary_df.columns = ["_".join(col).strip() for col in summary_df.columns.values]
    summary_df.columns = [
        col[:-1] if col.endswith("_") else col for col in summary_df.columns
    ]

    # Calculate sem of MAE
    summary_df["sem"] = summary_df["absolute_error_std"] / (
        summary_df["absolute_error_count"] ** 0.5
    )

    summary_df["effective_capacity_watts_observation"] = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg({"effective_capacity_watts": "mean"})
        .reset_index()["effective_capacity_watts"]
    )

    summary_df = summary_df.rename(
        columns={"absolute_error_mean": "MAE", "error_mean": "ME"}
    )
    summary_df["NMAE (by capacity)"] = (
        summary_df["MAE"] / summary_df["effective_capacity_watts"]
    )
    summary_df["NMAE (by mean observed generation)"] = (
        summary_df["MAE"] / mean_observed_generation
    )

    return summary_df


def align_t0(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Align t0 forecasts for different forecasters."""
    num_forecasters = merged_df["forecaster_name"].nunique()
    # Count number of forecasters that have each t0 time
    counts = merged_df.groupby("initialization_timestamp_utc")[
        "forecaster_name"
    ].nunique()
    # Filter to just those t0s that all forecasters have
    common_t0s = counts[counts == num_forecasters].index
    return merged_df[merged_df["initialization_timestamp_utc"].isin(common_t0s)]
