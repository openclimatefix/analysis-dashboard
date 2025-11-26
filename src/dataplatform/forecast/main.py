"""Data Platform Forecast Streamlit Page Main Code."""

import asyncio
import os

import pandas as pd
import streamlit as st
from dp_sdk.ocf import dp
from grpclib.client import Channel

from dataplatform.forecast.constant import metrics
from dataplatform.forecast.data import align_t0, get_all_data
from dataplatform.forecast.plot import (
    plot_forecast_metric_per_day,
    plot_forecast_metric_vs_horizon_minutes,
    plot_forecast_time_series,
)
from dataplatform.forecast.setup import setup_page

data_platform_host = os.getenv("DATA_PLATFORM_HOST", "localhost")
data_platform_port = int(os.getenv("DATA_PLATFORM_PORT", "50051"))

# TODO make this dynamic
observer_names = ["pvlive_in_day", "pvlive_day_after"]


def dp_forecast_page() -> None:
    """Wrapper function that is not async to call the main async function."""
    asyncio.run(async_dp_forecast_page())


async def async_dp_forecast_page() -> None:
    """Async Main function for the Data Platform Forecast Streamlit page."""
    st.title("Data Platform Forecast Page")
    st.write("This is the forecast page from the Data Platform module. This is very much a WIP")

    async with Channel(host=data_platform_host, port=data_platform_port) as channel:
        client = dp.DataPlatformDataServiceStub(channel)

        setup_page_dict = await setup_page(client)
        selected_location = setup_page_dict["selected_location"]
        start_date = setup_page_dict["start_date"]
        end_date = setup_page_dict["end_date"]
        selected_forecasters = setup_page_dict["selected_forecasters"]
        forecaster_names = setup_page_dict["forecaster_names"]
        selected_metric = setup_page_dict["selected_metric"]
        selected_forecast_type = setup_page_dict["selected_forecast_type"]
        scale_factor = setup_page_dict["scale_factor"]
        selected_forecast_horizon = setup_page_dict["selected_forecast_horizon"]
        selected_t0s = setup_page_dict["selected_t0s"]
        units = setup_page_dict["units"]

        ### 1. Get all the data ###
        all_data_dict = await get_all_data(
            client=client,
            start_date=start_date,
            end_date=end_date,
            selected_forecasters=selected_forecasters,
            selected_location=selected_location,
        )
        merged_df = all_data_dict["merged_df"]
        all_forecast_data_df = all_data_dict["all_forecast_data_df"]
        all_observations_df = all_data_dict["all_observations_df"]
        forecast_seconds = all_data_dict["forecast_seconds"]
        observation_seconds = all_data_dict["observation_seconds"]

        st.write(f"Selected Location uuid: `{selected_location.location_uuid}`.")
        st.write(
            f"Fetched `{len(all_forecast_data_df)}` rows of forecast data \
            in `{forecast_seconds:.2f}` seconds. \
            Fetched `{len(all_observations_df)}` rows of observation data \
            in `{observation_seconds:.2f}` seconds. \
            We cache data for 5 minutses to speed up repeated requests.",
        )

        # add download button
        csv = all_forecast_data_df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️",
            data=csv,
            file_name=f"site_forecast_{selected_location.location_uuid}_{start_date}_{end_date}.csv",
            mime="text/csv",
        )

        ### 2. Plot of raw forecast data. ###
        st.header("Time Series Plot")

        show_probabilistic = st.checkbox("Show Probabilistic Forecasts", value=True)

        fig = plot_forecast_time_series(
            all_forecast_data_df=all_forecast_data_df,
            all_observations_df=all_observations_df,
            forecaster_names=forecaster_names,
            observer_names=observer_names,
            scale_factor=scale_factor,
            units=units,
            selected_forecast_type=selected_forecast_type,
            selected_forecast_horizon=selected_forecast_horizon,
            selected_t0s=selected_t0s,
            show_probabilistic=show_probabilistic,
        )
        st.plotly_chart(fig)

        ### 3. Summary Accuracy Graph. ###
        st.header("Accuracy")

        st.write(metrics)

        align_t0s = st.checkbox(
            "Align t0s (Only common t0s across all forecaster are used)",
            value=True,
        )
        if align_t0s:
            merged_df = align_t0(merged_df)

        st.subheader("Metric vs Forecast Horizon")

        show_sem = st.checkbox("Show SEM", value=True) if selected_metric == "MAE" else False

        fig2, summary_df = plot_forecast_metric_vs_horizon_minutes(
            merged_df,
            forecaster_names,
            selected_metric,
            scale_factor,
            units,
            show_sem,
        )

        st.plotly_chart(fig2)

        csv = summary_df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️",
            data=csv,
            file_name=f"summary_accuracy_{selected_location.location_uuid}_{start_date}_{end_date}.csv",
            mime="text/csv",
        )

        ### 4. Summary Accuracy Table, with slider to select min and max horizon mins. ###
        st.subheader("Summary Accuracy Table")

        # add slider to select min and max horizon mins
        min_horizon, max_horizon = st.slider(
            "Select Horizon Mins Range",
            int(summary_df["horizon_mins"].min()),
            int(summary_df["horizon_mins"].max()),
            (
                int(summary_df["horizon_mins"].min()),
                int(summary_df["horizon_mins"].max()),
            ),
            step=30,
        )

        summary_table_df = make_summary_data(
            merged_df=merged_df,
            min_horizon=min_horizon,
            max_horizon=max_horizon,
            scale_factor=scale_factor,
            units=units,
        )

        st.dataframe(summary_table_df)

        ### 4. Daily metric plots. ###
        st.subheader("Daily Metrics Plots")
        st.write(
            "Plotted below are the daily MAE for each forecaster. "
            "This is for all forecast horizons.",
        )

        fig3 = plot_forecast_metric_per_day(
            merged_df=merged_df,
            forecaster_names=forecaster_names,
            scale_factor=scale_factor,
            units=units,
            selected_metric=selected_metric,
        )

        st.plotly_chart(fig3)

        st.header("Known Issues and TODOs")

        st.write("Bug: cache not releasing, the cache should stay for 5 minutes")
        st.write("Add more metrics")
        st.write("Group adjust and non-adjust")
        st.write("speed up read, use async and more caching")
        st.write("Get page working with no observations data")
        st.write("MAE vs horizon plot should start at 0")


def make_summary_data(
    merged_df: pd.DataFrame,
    min_horizon: int,
    max_horizon: int,
    scale_factor: float,
    units: str,
) -> pd.DataFrame:
    """Make summary data table for given min and max horizon mins."""
    # Reduce my horizon mins
    summary_table_df = merged_df[
        (merged_df["horizon_mins"] >= min_horizon) & (merged_df["horizon_mins"] <= max_horizon)
    ]

    summary_table_df = summary_table_df.rename(
        columns={
            "effective_capacity_watts_observation": "Capacity_watts",
            "value_watts": "Mean_Observed_Generation_watts",
        },
    )

    value_columns = [
        "error",
        "absolute_error",
        #  'absolute_error_normalized_by_generation',
        "Mean_Observed_Generation_watts",
        "Capacity_watts",
    ]

    summary_table_df = summary_table_df[["forecaster_name", *value_columns]]

    summary_table_df["Capacity_watts"] = summary_table_df["Capacity_watts"].astype(float)

    # group by forecaster full name a
    summary_table_df = summary_table_df.groupby("forecaster_name").mean()

    # rename
    summary_table_df = summary_table_df.rename(
        columns={
            "error": "ME",
            "absolute_error": "MAE",
            # 'absolute_error_normalized_by_generation': 'NMAE (by observed generation)',
            "Capacity_watts": "Mean Capacity",
            "Mean_Observed_Generation_watts": "Mean Observed Generation",
        },
    )

    # scale by units
    summary_table_df = summary_table_df / scale_factor
    summary_table_df = summary_table_df.rename(
        {col: f"{col} [{units}]" for col in summary_table_df.columns},
        axis=1,
    )

    # pivot table, so forecaster_name is columns
    summary_table_df = summary_table_df.pivot_table(
        columns=summary_table_df.index,
        values=summary_table_df.columns.tolist(),
    )

    return summary_table_df
