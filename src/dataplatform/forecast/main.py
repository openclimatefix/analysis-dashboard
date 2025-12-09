"""Data Platform Forecast Streamlit Page Main Code."""

import asyncio
import os

import pandas as pd
import streamlit as st
from dp_sdk.ocf import dp
from grpclib.client import Channel

from dataplatform.forecast.constant import metrics, observer_names
from dataplatform.forecast.data import align_t0, get_all_data
from dataplatform.forecast.plot import (
    plot_forecast_metric_per_day,
    plot_forecast_metric_vs_horizon_minutes,
    plot_forecast_time_series,
)
from dataplatform.forecast.setup import setup_page

data_platform_host = os.getenv("DATA_PLATFORM_HOST", "localhost")
data_platform_port = int(os.getenv("DATA_PLATFORM_PORT", "50051"))


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
        strict_horizon_filtering = setup_page_dict["strict_horizon_filtering"]

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
        We cache data for 5 minutes to speed up repeated requests.",
    )

    # add download button
    csv = merged_df.to_csv().encode("utf-8")
    st.download_button(
        label="⬇️ Download data",
        data=csv,
        file_name=f"site_forecast_{selected_location.location_uuid}_{start_date}_{end_date}.csv",
        mime="text/csv",
        help="Download the forecast and generation data as a CSV file.",
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
        strict_horizon_filtering=strict_horizon_filtering,
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

    if selected_metric == "MAE":
        show_sem = st.checkbox(
            "Show Uncertainty",
            value=True,
            help="On the plot below show the uncertainty bands associated with the MAE. "
            "This is done by looking at the "
            "Standard Error of the Mean (SEM) of the absolute errors. "
            "We plot the 5 to 95 percentile range around the MAE.",
        )
    else:
        show_sem = False

    summary_df = make_summary_data_metric_vs_horizon_minutes(merged_df)

    fig2 = plot_forecast_metric_vs_horizon_minutes(
        summary_df,
        forecaster_names,
        selected_metric,
        scale_factor,
        units,
        show_sem,
    )

    st.plotly_chart(fig2)

    csv = summary_df.to_csv().encode("utf-8")
    st.download_button(
        label="⬇️ Download summary",
        data=csv,
        file_name=f"summary_accuracy_{selected_location.location_uuid}_{start_date}_{end_date}.csv",
        mime="text/csv",
        help="Download the summary accuracy data as a CSV file.",
    )

    ### 4. Summary Accuracy Table, with slider to select min and max horizon mins. ###
    st.subheader("Summary Accuracy Table")

    # add slider to select min and max horizon mins
    default_min_horizon = int(summary_df["horizon_mins"].min())
    default_max_horizon = int(summary_df["horizon_mins"].max())
    min_horizon, max_horizon = st.slider(
        "Select Horizon Mins Range",
        default_min_horizon,
        default_max_horizon,
        (
            default_min_horizon,
            default_max_horizon,
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

    st.write("Add more metrics")
    st.write("Group adjust and non-adjust")
    st.write("speed up read, use async and more caching")
    st.write("Get page working with no observations data")


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

    capacity_watts_col = "effective_capacity_watts_observation"

    value_columns = [
        "error",
        "absolute_error",
        "value_watts",
        capacity_watts_col,
    ]
    summary_table_df = summary_table_df[["forecaster_name", *value_columns]]

    # group by forecaster full name a
    summary_table_df = summary_table_df.groupby("forecaster_name").mean()

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

    # rename
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

    # mean absolute error by horizonMins and forecasterFullName
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
    summary_df.columns = [col[:-1] if col.endswith("_") else col for col in summary_df.columns]

    # calculate sem of MAE
    summary_df["sem"] = summary_df["absolute_error_std"] / (
        summary_df["absolute_error_count"] ** 0.5
    )

    # TODO more metrics

    summary_df["effective_capacity_watts_observation"] = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg({"effective_capacity_watts_observation": "mean"})
        .reset_index()["effective_capacity_watts_observation"]
    )

    # rename absolute_error to MAE
    summary_df = summary_df.rename(columns={"absolute_error_mean": "MAE", "error_mean": "ME"})
    summary_df["NMAE (by capacity)"] = (
        summary_df["MAE"] / summary_df["effective_capacity_watts_observation"]
    )
    summary_df["NMAE (by mean observed generation)"] = summary_df["MAE"] / mean_observed_generation

    return summary_df
