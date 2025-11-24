import asyncio
import os

import streamlit as st
from dp_sdk.ocf import dp
from grpclib.client import Channel

from dataplatform.forecast.constanst import metrics
from dataplatform.forecast.data import get_all_data
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


def dp_forecast_page():
    asyncio.run(async_dp_forecast_page())


async def async_dp_forecast_page():
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
            f"Fetched `{len(all_forecast_data_df)}` rows of forecast data in `{forecast_seconds:.2f}` seconds. \
            Fetched `{len(all_observations_df)}` rows of observation data in `{observation_seconds:.2f}` seconds. \
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

        fig = plot_forecast_time_series(
            all_forecast_data_df=all_forecast_data_df,
            all_observations_df=all_observations_df,
            forecaster_names=forecaster_names,
            observer_names=observer_names,
            scale_factor=scale_factor,
            units=units,
            selected_forecast_type=selected_forecast_type,
            selected_forecast_horizon=selected_forecast_horizon,
        )
        st.plotly_chart(fig)

        ### 3. Summary Accuracy Graph. ###
        st.header("Summary Accuracy Graph")

        st.write(metrics)

        fig2, summary_df = plot_forecast_metric_vs_horizon_minutes(
            merged_df, forecaster_names, selected_metric, scale_factor, units
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
        st.header("Summary Accuracy Table")

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
        st.header("Daily Metrics Plots")
        st.write(
            "Plotted below are the daily MAE for each forecaster. This is for all forecast horizons.",
        )

        fig3 = plot_forecast_metric_per_day(
            merged_df=merged_df,
            selected_forecasters=selected_forecasters,
            scale_factor=scale_factor,
            units=units,
            selected_metric=selected_metric
        )

        st.plotly_chart(fig3)

        st.header("TODO")

        st.write("Bug: cache not releasing")
        st.write("Align forecasts on t0")
        st.write("Add more metrics")
        st.write("Add creation time / t0 forecast filter")
        st.write("speed up read, use async and more caching")
        st.write("Improve GSP labels")
        st.write("Get page working with no observations data")
        st.write("Change UK to use MW")
        st.write("Add GSP to name")
        st.write("Remove last MAE point")
        st.write("Reduce to last 7 days")
        st.write("Options to togle probablies in MAE ")
        st.write("Change y/x to actula and forecast")
        st.write("Remove duplicate names in legend of daily metrics plot")
        st.write("Look into shading areas disappering")


def make_summary_data(merged_df, min_horizon, max_horizon, scale_factor, units):
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

    summary_table_df = summary_table_df[["forecaster_name"] + value_columns]

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
