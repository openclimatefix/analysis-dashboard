import streamlit as st
from datetime import datetime, timedelta, timezone
import os
import asyncio
from dp_sdk.ocf import dp
import pandas as pd
from grpclib.client import Channel
import plotly.graph_objects as go
import betterproto

data_platform_host = os.getenv("DATA_PLATFORM_HOST", "localhost")
data_platform_port = int(os.getenv("DATA_PLATFORM_PORT", "50051"))

# TODO make this dynamic
observer_names = ["pvlive_in_day", "pvlive_day_after"]



async def get_forecast_data(
    _client, location, start_date, end_date, selected_forecasters
) -> pd.DataFrame:
    all_data_df = []

    # loop over 30 days of data
    temp_start_date = start_date
    while temp_start_date <= end_date:
        temp_end_date = temp_start_date + timedelta(days=30)
        if temp_end_date > end_date:
            temp_end_date = end_date

        # fetch data
        stream_forecast_data_request = dp.StreamForecastDataRequest(
            location_uuid=location.location_uuid,
            energy_source=dp.EnergySource.SOLAR,
            time_window=dp.TimeWindow(
                start_timestamp_utc=temp_start_date, end_timestamp_utc=temp_end_date
            ),
            forecasters=selected_forecasters,
        )
        forecasts = []
        async for chunk in _client.stream_forecast_data(stream_forecast_data_request):
            forecasts.append(
                chunk.to_dict(
                    include_default_values=True, casing=betterproto.Casing.SNAKE
                )
            )

        if len(forecasts) > 0:
            all_data_df.append(
                pd.DataFrame.from_dict(forecasts)
                .pipe(
                    lambda df: df.join(
                        pd.json_normalize(df["other_statistics_fractions"])
                    )
                )
                .drop("other_statistics_fractions", axis=1)
            )

        temp_start_date = temp_start_date + timedelta(days=7)

    all_data_df = pd.concat(all_data_df, ignore_index=True)

    # get watt value
    all_data_df["p50_watts"] = all_data_df["p50_fraction"].astype(float) * all_data_df[
        "effective_capacity_watts"
    ].astype(float)

    return all_data_df


async def get_all_observations(client, location, start_date, end_date) -> pd.DataFrame:

    all_observations_df = []

    for observer_name in observer_names:
        # loop over 7 days of data
        observation_one_df = []
        temp_start_date = start_date
        while temp_start_date <= end_date:
            temp_end_date = temp_start_date + timedelta(days=7)
            if temp_end_date > end_date:
                temp_end_date = end_date

            get_observations_request = dp.GetObservationsAsTimeseriesRequest(
                observer_name=observer_name,
                location_uuid=location.location_uuid,
                energy_source=dp.EnergySource.SOLAR,
                time_window=dp.TimeWindow(temp_start_date, temp_end_date),
            )
            get_observations_response = await client.get_observations_as_timeseries(
                get_observations_request
            )

            observations = []
            for chunk in get_observations_response.values:
                observations.append(
                    chunk.to_dict(
                        include_default_values=True, casing=betterproto.Casing.SNAKE
                    )
                )

            observation_one_df.append(pd.DataFrame.from_dict(observations))

            temp_start_date = temp_start_date + timedelta(days=7)

        observation_one_df = pd.concat(observation_one_df, ignore_index=True)
        observation_one_df = observation_one_df.sort_values(by="timestamp_utc")
        observation_one_df["observer_name"] = observer_name

        all_observations_df.append(observation_one_df)

    all_observations_df = pd.concat(all_observations_df, ignore_index=True)

    all_observations_df["value_watts"] = all_observations_df["value_fraction"].astype(
        float
    ) * all_observations_df["effective_capacity_watts"].astype(float)

    return all_observations_df


def dp_forecast_page():
    asyncio.run(async_dp_forecast_page())


async def async_dp_forecast_page():
    st.title("Data Platform Forecast Page")
    st.write(
        "This is the forecast page from the Data Platform module. This is very much a WIP"
    )

    async with Channel(host=data_platform_host, port=data_platform_port) as channel:
        client = dp.DataPlatformDataServiceStub(channel)

        # Select Country
        country = st.sidebar.selectbox("TODO Select a Country", ["UK", "NL"], index=0)

        # Select Location Type
        location_types = [
            dp.LocationType.NATION,
            dp.LocationType.GSP,
            dp.LocationType.SITE,
        ]
        location_type = st.sidebar.selectbox(
            "Select a Location Type", location_types, index=0
        )

        # List Location
        list_locations_request = dp.ListLocationsRequest(
            location_type_filter=location_type
        )
        list_locations_response = await client.list_locations(list_locations_request)
        locations = list_locations_response.locations
        location_names = [loc.location_name for loc in locations]

        # slect locations
        selected_location_name = st.sidebar.selectbox(
            "Select a Location", location_names, index=0
        )
        selected_location = next(
            loc for loc in locations if loc.location_name == selected_location_name
        )

        # get models
        get_forecasters_request = dp.ListForecastersRequest(latest_versions_only=True)
        get_forecasters_response = await client.list_forecasters(
            get_forecasters_request
        )
        forecasters = get_forecasters_response.forecasters
        forecaster_names = [forecaster.forecaster_name for forecaster in forecasters]
        selected_forecaster_name = st.sidebar.multiselect(
            "Select a Forecaster", forecaster_names, default=forecaster_names[0]
        )
        selected_forecasters = [
            forecaster
            for forecaster in forecasters
            if forecaster.forecaster_name in selected_forecaster_name
        ]

        # select start and end date
        start_date = st.sidebar.date_input(
            "Start date:", datetime.now().date() - timedelta(days=30)
        )
        end_date = st.sidebar.date_input(
            "End date:", datetime.now().date() + timedelta(days=3)
        )
        start_date = datetime.combine(start_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        end_date = datetime.combine(end_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )

        # select forecast type
        st.sidebar.write("TODO Select Forecast Type:")

        # setup page
        st.header("Time Series Plot")

        # get generation data
        all_observations_df = await get_all_observations(
            client, selected_location, start_date, end_date
        )

        # get forcast all data
        all_forecast_data_df = await get_forecast_data(
            client, selected_location, start_date, end_date, selected_forecasters
        )
        st.write(
            f"Selected Location uuid: {selected_location.location_uuid}. \
                 Fetched {len(all_forecast_data_df)} rows of forecast data"
        )

        # add download button
        csv = all_forecast_data_df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️",
            data=csv,
            file_name=f"site_forecast_{selected_location.location_uuid}_{start_date}_{end_date}.csv",
            mime="text/csv",
        )

        all_forecast_data_df["target_timestamp_utc"] = pd.to_datetime(
            all_forecast_data_df["init_timestamp"]
        ) + pd.to_timedelta(all_forecast_data_df["horizon_mins"], unit="m")

        # Choose current forecast
        # this is done by selecting the unique target_timestamp_utc with the the lowest horizonMins
        # it should also be unique for each forecasterFullName
        current_forecast_df = all_forecast_data_df.loc[
            all_forecast_data_df.groupby(
                ["target_timestamp_utc", "forecaster_fullname"]
            )["horizon_mins"].idxmin()
        ]

        # plot the results
        fig = go.Figure()
        for forecaster in selected_forecasters:
            name_and_version = (
                f"{forecaster.forecaster_name}:{forecaster.forecaster_version}"
            )
            forecaster_df = current_forecast_df[
                current_forecast_df["forecaster_fullname"] == name_and_version
            ]
            fig.add_trace(
                go.Scatter(
                    x=forecaster_df["target_timestamp_utc"],
                    y=forecaster_df["p50_watts"],
                    mode="lines",
                    name=forecaster.forecaster_name,
                )
            )

        for observer_name in observer_names:
            obs_df = all_observations_df[
                all_observations_df["observer_name"] == observer_name
            ]
            fig.add_trace(
                go.Scatter(
                    x=obs_df["timestamp_utc"],
                    y=obs_df["value_watts"],
                    mode="lines",
                    name=observer_name,
                )
            )

        fig.update_layout(
            title="Current Forecast",
            xaxis_title="Time",
            yaxis_title="Generation [Watts]",
            legend_title="Forecaster",
        )

        st.plotly_chart(fig)

        st.header("Summary Accuracy Graph")
        metrics = {
            "MAE": "MAE is absolute mean error, average(abs(y-x))",
            "ME": "ME is mean (bias) error, average((y-x))",
            "NMAE (by capacity)": " NMAE (by capacity), average(abs(y-x)) / mean(capacity)",
            "NMAE (by mean observed generation)": " NMAE (by mean observed generation), average(abs(y-x)) / mean(y)",
            #    "NMAE (by observed generation)":" NAME (by observed generation)"
        }
        selected_metric = st.sidebar.selectbox(
            "Select a Metrics", metrics.keys(), index=0
        )

        st.write(metrics)

        # take the foecast data, and group by horizonMins, forecasterFullName
        # calculate mean absolute error between p50Fraction and observations valueFraction
        all_observations_df["timestamp_utc"] = pd.to_datetime(
            all_observations_df["timestamp_utc"]
        )
        merged_df = pd.merge(
            all_forecast_data_df,
            all_observations_df,
            left_on=["target_timestamp_utc"],
            right_on=["timestamp_utc"],
            how="inner",
            suffixes=("_forecast", "_observation"),
        )
        merged_df["effective_capacity_watts_observation"] = merged_df[
            "effective_capacity_watts_observation"
        ].astype(float)

        # error
        merged_df["error"] = merged_df["p50_watts"] - merged_df["value_watts"]

        # absolute error
        merged_df["absolute_error"] = (merged_df["error"]).abs()

        # absolute error, normalized by mean observed generation
        mean_observed_generation = merged_df["value_watts"].mean()
        # merged_df['absolute_error_normalized_by_generation'] = merged_df['absolute_error'] / merged_df['value_watts']

        summary_df = (
            merged_df.groupby(["horizon_mins", "forecaster_fullname"])
            .agg({"absolute_error": "mean"})
            .reset_index()
        )
        summary_df["std"] = (
            merged_df.groupby(["horizon_mins", "forecaster_fullname"])
            .agg({"absolute_error": "std"})
            .reset_index()["absolute_error"]
        )
        summary_df["count"] = (
            merged_df.groupby(["horizon_mins", "forecaster_fullname"])
            .agg({"absolute_error": "count"})
            .reset_index()["absolute_error"]
        )
        summary_df["sem"] = summary_df["std"] / (summary_df["count"] ** 0.5)

        # ME
        summary_df["ME"] = (
            merged_df.groupby(["horizon_mins", "forecaster_fullname"])
            .agg({"error": "mean"})
            .reset_index()["error"]
        )

        # summary_df["absolute_error_divided_by_observed"] = (
        #     merged_df.groupby(["horizon_mins", "forecaster_fullname"])
        #     .agg({"absolute_error_normalized_by_generation": "mean"})
        #     .reset_index()["absolute_error_normalized_by_generation"]
        # )

        summary_df["effective_capacity_watts_observation"] = (
            merged_df.groupby(["horizon_mins", "forecaster_fullname"])
            .agg({"effective_capacity_watts_observation": "mean"})
            .reset_index()["effective_capacity_watts_observation"]
        )

        # rename absolute_error to MAE
        summary_df = summary_df.rename(columns={"absolute_error": "MAE"})
        summary_df["NMAE (by capacity)"] = (
            summary_df["MAE"] / summary_df["effective_capacity_watts_observation"]
        )
        summary_df["NMAE (by mean observed generation)"] = (
            summary_df["MAE"] / mean_observed_generation
        )
        # summary_df["NMAE (by observed generation)"] = summary_df["absolute_error_divided_by_observed"]

        fig2 = go.Figure()

        for forecaster in selected_forecasters:
            name_and_version = (
                f"{forecaster.forecaster_name}:{forecaster.forecaster_version}"
            )
            forecaster_df = summary_df[
                summary_df["forecaster_fullname"] == name_and_version
            ]
            fig2.add_trace(
                go.Scatter(
                    x=forecaster_df["horizon_mins"],
                    y=forecaster_df[selected_metric],
                    mode="lines+markers",
                    name=forecaster.forecaster_name,
                )
            )

            fig2.add_trace(
                go.Scatter(
                    x=forecaster_df["horizon_mins"],
                    y=forecaster_df[selected_metric] - 1.96 * forecaster_df["sem"],
                    mode="lines",
                    # name="p10: " + model,
                    # line=dict(color=get_colour_from_model_name(model), width=0),
                    legendgroup=forecaster.forecaster_name,
                    showlegend=False,
                )
            )

            fig2.add_trace(
                go.Scatter(
                    x=forecaster_df["horizon_mins"],
                    y=forecaster_df[selected_metric] + 1.96 * forecaster_df["sem"],
                    mode="lines",
                    # name="p10: " + model,
                    # line=dict(color=get_colour_from_model_name(model), width=0),
                    legendgroup=forecaster.forecaster_name,
                    showlegend=False,
                    fill="tonexty",
                )
            )

        fig2.update_layout(
            title=f"{selected_metric} by Horizon",
            xaxis_title="Horizon (Minutes)",
            yaxis_title=selected_metric,
            legend_title="Forecaster",
        )

        st.plotly_chart(fig2)

        csv = summary_df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️",
            data=csv,
            file_name=f"summary_accuracy_{selected_location.location_uuid}_{start_date}_{end_date}.csv",
            mime="text/csv",
        )

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

        # Reduce my horizon mins
        summary_table_df = merged_df[
            (merged_df["horizon_mins"] >= min_horizon)
            & (merged_df["horizon_mins"] <= max_horizon)
        ]

        summary_table_df = summary_table_df.rename(
            columns={
                "effective_capacity_watts_observation": "Capacity_watts",
                "value_watts": "Mean_Observed_Generation_watts",
            }
        )

        value_columns = [
            "error",
            "absolute_error",
            #  'absolute_error_normalized_by_generation',
            "Mean_Observed_Generation_watts",
            "Capacity_watts",
        ]

        summary_table_df = summary_table_df[["forecaster_fullname"] + value_columns]

        summary_table_df["Capacity_watts"] = summary_table_df["Capacity_watts"].astype(
            float
        )

        # group by forecaster full name a
        summary_table_df = summary_table_df.groupby("forecaster_fullname").mean()

        # rename
        summary_table_df = summary_table_df.rename(
            columns={
                "error": "ME",
                "absolute_error": "MAE",
                # 'absolute_error_normalized_by_generation': 'NMAE (by observed generation)',
                "Capacity_watts": "Mean Capacity",
                "Mean_Observed_Generation_watts": "Mean Observed Generation",
            }
        )

        # pivot table, so forecaster_fullname is columns
        summary_table_df = summary_table_df.pivot_table(
            columns=summary_table_df.index,
            values=summary_table_df.columns.tolist(),
        )

        st.dataframe(summary_table_df)

        st.header("TODO")

        st.write("Add caching on data")
        st.write("Add probabilistic")
        st.write("Scale to KW/MW/GW as needed")
        st.write("Align forecasts on t0")
        st.write("Add more metrics")
        st.write("Add forecast horizon options")
        st.write("Add creation time forecast filter")
        st.write("Daily Metrics graphs")
        st.write("colours")
        st.write("speed up read, use async and more caching")
