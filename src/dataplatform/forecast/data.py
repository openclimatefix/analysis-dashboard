"""Functions to get forecast and observation data from Data Platform."""

import time
from datetime import datetime, timedelta

import pandas as pd
from aiocache import Cache, cached
from ocf import dp
from google.protobuf.json_format import MessageToDict

from dataplatform.forecast.cache import key_builder_remove_client
from dataplatform.forecast.constant import cache_seconds, observer_names
from ocf.dp.dp import common_pb2
from ocf.dp.dp_data import messages_pb2, service_pb2_grpc


async def get_forecast_data(
    dpc: service_pb2_grpc.DataPlatformDataServiceStub,
    location: dp.ListLocationsResponseLocationSummary,
    start_date: datetime,
    end_date: datetime,
    selected_forecasters: list[dp.Forecaster],
) -> pd.DataFrame:
    """Get forecast data for the given location and time window."""
    all_data_df = []

    for forecaster in selected_forecasters:
        forecaster_data_df = await get_forecast_data_one_forecaster(
            dpc,
            location,
            start_date,
            end_date,
            forecaster,
        )
        if forecaster_data_df is not None:
            all_data_df.append(forecaster_data_df)

    if len(all_data_df) == 0:
        all_data_df = pd.DataFrame(columns=[
            "location_uuid",
            "forecaster_name",
            "effective_capacity_watts",
            "p50_fraction",
            "init_timestamp",
            "horizon_mins",
            "target_timestamp_utc",
        ])
    else:
        all_data_df = pd.concat(all_data_df, ignore_index=True)

    all_data_df["effective_capacity_watts"] = all_data_df["effective_capacity_watts"].astype(float)

    # get watt value
    all_data_df["p50_watts"] = all_data_df["p50_fraction"] * all_data_df["effective_capacity_watts"]

    for col in ["p10", "p25", "p75", "p90"]:
        col_fraction = f"{col}_fraction"
        if col_fraction in all_data_df.columns:
            all_data_df[f"{col}_watts"] = (
                all_data_df[col_fraction] * all_data_df["effective_capacity_watts"]
            )

    return all_data_df


@cached(ttl=cache_seconds, cache=Cache.MEMORY, key_builder=key_builder_remove_client)
async def get_forecast_data_one_forecaster(
    dpc: service_pb2_grpc.DataPlatformDataServiceStub,
    location: dp.ListLocationsResponseLocationSummary,
    start_date: datetime,
    end_date: datetime,
    selected_forecaster: dp.Forecaster,
) -> pd.DataFrame | None:
    """Get forecast data for one forecaster for the given location and time window."""
    all_data_list_dict = []

    # Grab all the data, in chunks of 30 days to avoid too large requests
    temp_start_date = start_date
    while temp_start_date <= end_date:
        temp_end_date = min(temp_start_date + timedelta(days=30), end_date)

        # fetch data
        stream_forecast_data_request = messages_pb2.StreamForecastDataRequest(
            location_uuid=location.location_uuid,
            energy_source=common_pb2.EnergySource.ENERGY_SOURCE_SOLAR,
            time_window=messages_pb2.StreamForecastDataRequest.TimeWindow(
                start_timestamp_utc=temp_start_date,
                end_timestamp_utc=temp_end_date,
            ),
            forecasters=[messages_pb2.Forecaster(forecaster_name=selected_forecaster.forecaster_name, 
                                                 forecaster_version=selected_forecaster.forecaster_version)],
        )

        forecasts = []
        async for chunk in dpc.StreamForecastData(stream_forecast_data_request):
            forecasts.append(chunk)
        
        if len(forecasts) > 0:
            all_data_list_dict.extend(MessageToDict(f, always_print_fields_with_no_presence=True) for f in forecasts)

        temp_start_date = temp_start_date + timedelta(days=30)

    all_data_df = pd.DataFrame.from_dict(all_data_list_dict)

    # change from camelCase to snake_case
    all_data_df = all_data_df.rename(
        columns={
            "locationUuid": "location_uuid",
            "forecasterFullname": "forecaster_fullname",
            "forecasterName": "forecaster_name",
            "effectiveCapacityWatts": "effective_capacity_watts",
            "p50Fraction": "p50_fraction",
            "initTimestamp": "init_timestamp",
            "horizonMins": "horizon_mins",
            "targetTimestampUtc": "target_timestamp_utc",
            "otherStatisticsFractions": "other_statistics_fractions",
        },
    )

    if len(all_data_df) == 0:
        return pd.DataFrame(columns=[
            "location_uuid",
            "forecaster_fullname",
            "forecaster_name",
            "effective_capacity_watts",
            "p50_fraction",
            "init_timestamp",
            "horizon_mins",
            "target_timestamp_utc",
        ])

    # get plevels into columns and rename them 'fraction
    columns_before_expand = set(all_data_df.columns)
    if "other_statistics_fractions" in all_data_df.columns:
        all_data_df = all_data_df.pipe(
            lambda df: df.join(pd.json_normalize(df["other_statistics_fractions"])),
        ).drop("other_statistics_fractions", axis=1)
    new_columns = set(all_data_df.columns) - columns_before_expand
    if len(new_columns) > 0:
        all_data_df = all_data_df.rename(columns={col: f"{col}_fraction" for col in new_columns})

    # create column forecaster_name, its forecaster_fullname with version removed
    all_data_df["forecaster_name"] = all_data_df["forecaster_fullname"].apply(
        lambda x: x.rsplit(":", 1)[0],  # split from right, max 1 split
    )

    return all_data_df


@cached(ttl=cache_seconds, cache=Cache.MEMORY, key_builder=key_builder_remove_client)
async def get_all_observations(
    client: service_pb2_grpc.DataPlatformDataServiceStub,
    location: dp.ListLocationsResponseLocationSummary,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Get all observations for the given location and time window."""
    all_observations_df = []

    for observer_name in observer_names:
        # Get all the observations for this observer_name, in chunks of 7 days
        observation_one_df = []
        temp_start_date = start_date
        while temp_start_date <= end_date:
            temp_end_date = min(temp_start_date + timedelta(days=7), end_date)

            get_observations_request = messages_pb2.GetObservationsAsTimeseriesRequest(
                observer_name=observer_name,
                location_uuid=location.location_uuid,
                energy_source=common_pb2.EnergySource.ENERGY_SOURCE_SOLAR,
                time_window=messages_pb2.TimeWindow(start_timestamp_utc=temp_start_date, 
                                                    end_timestamp_utc=temp_end_date),
            )
            get_observations_response = await client.GetObservationsAsTimeseries(
                get_observations_request,
            )

            observations = []
            for chunk in get_observations_response.values:
                observations.append(
                    MessageToDict(chunk, always_print_fields_with_no_presence=True),
                )

            observation_one_df.append(pd.DataFrame.from_dict(observations))

            temp_start_date = temp_start_date + timedelta(days=7)

        observation_one_df = pd.concat(observation_one_df, ignore_index=True)

        # rename varibales from Camel case to snake case
        observation_one_df = observation_one_df.rename(columns={
            "timestampUtc": "timestamp_utc",
            "effectiveCapacityWatts": "effective_capacity_watts",
            "valueFraction": "value_fraction",
        })

        # Handle case where no observation data is returned
        if (
            not observation_one_df.empty
            and "timestamp_utc" in observation_one_df.columns
        ):
            observation_one_df = observation_one_df.sort_values(by="timestamp_utc")
        else:
            observation_one_df = pd.DataFrame()

        if not observation_one_df.empty:
            observation_one_df["observer_name"] = observer_name

        all_observations_df.append(observation_one_df)

    all_observations_df = pd.concat(all_observations_df, ignore_index=True)
    # If no observations were returned at all, return empty dataframe
    if all_observations_df.empty:
        return pd.DataFrame()

    all_observations_df["effective_capacity_watts"] = all_observations_df[
        "effective_capacity_watts"
    ].astype(float)

    all_observations_df["value_watts"] = (
        all_observations_df["value_fraction"] * all_observations_df["effective_capacity_watts"]
    )
    all_observations_df["timestamp_utc"] = pd.to_datetime(all_observations_df["timestamp_utc"])

    return all_observations_df


async def get_all_data(
    client: service_pb2_grpc.DataPlatformDataServiceStub,
    selected_location: dp.ListLocationsResponseLocationSummary,
    start_date: datetime,
    end_date: datetime,
    selected_forecasters: list[dp.Forecaster],
) -> dict:
    """Get all forecast and observation data, and merge them."""
    # get generation data
    time_start = time.time()
    all_observations_df = await get_all_observations(
        client,
        selected_location,
        start_date,
        end_date,
    )
    observation_seconds = time.time() - time_start

    # get forcast all data
    time_start = time.time()
    all_forecast_data_df = await get_forecast_data(
        client,
        selected_location,
        start_date,
        end_date,
        selected_forecasters,
    )
    forecast_seconds = time.time() - time_start

    # If the observation data includes pvlive_day_after and pvlive_in_day,
    # then lets just take pvlive_day_after
    one_observations_df = all_observations_df.copy()
    if (
        not all_observations_df.empty
        and "observer_name" in all_observations_df.columns
        and "pvlive_day_after" in all_observations_df["observer_name"].values
    ):

        one_observations_df = all_observations_df[
            all_observations_df["observer_name"] == "pvlive_day_after"
        ]

    # make target_timestamp_utc
    all_forecast_data_df["init_timestamp"] = pd.to_datetime(all_forecast_data_df["init_timestamp"])
    all_forecast_data_df["target_timestamp_utc"] = all_forecast_data_df[
        "init_timestamp"
    ] + pd.to_timedelta(all_forecast_data_df["horizon_mins"], unit="m")

    # take the foecast data, and group by horizonMins, forecasterFullName
    # calculate mean absolute error between p50Fraction and observations valueFraction
    merged_df = pd.merge(
        all_forecast_data_df,
        one_observations_df,
        left_on=["target_timestamp_utc"],
        right_on=["timestamp_utc"],
        how="inner",
        suffixes=("_forecast", "_observation"),
    )

    # error and absolute error
    merged_df["error"] = merged_df["p50_watts"] - merged_df["value_watts"]
    merged_df["absolute_error"] = merged_df["error"].abs()

    # calculate forecast below for the different plevels
    for plevel in ["p10","p25","p50", "p75", "p90"]:
        if f"{plevel}_watts" in merged_df.columns:
            merged_df[f"{plevel}_below"] = merged_df[f"{plevel}_watts"] > merged_df["value_watts"]

    return {
        "merged_df": merged_df,
        "all_forecast_data_df": all_forecast_data_df,
        "all_observations_df": all_observations_df,
        "forecast_seconds": forecast_seconds,
        "observation_seconds": observation_seconds,
    }


def align_t0(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Align t0 forecasts for different forecasters."""
    # number of unique forecasters
    num_forecasters = merged_df["forecaster_name"].nunique()
    # Count number of forecasters that have each t0 time
    counts = merged_df.groupby("init_timestamp")["forecaster_name"].nunique()
    # Filter to just those t0s that all forecasters have
    common_t0s = counts[counts == num_forecasters].index
    return merged_df[merged_df["init_timestamp"].isin(common_t0s)]
