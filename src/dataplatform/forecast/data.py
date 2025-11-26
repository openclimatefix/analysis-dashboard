"""Functions to get forecast and observation data from Data Platform."""

import time
from datetime import datetime, timedelta

import betterproto
import pandas as pd
from aiocache import Cache, cached
from dp_sdk.ocf import dp

from dataplatform.forecast.cache import key_builder_remove_client

# TODO make this dynamic
observer_names = ["pvlive_in_day", "pvlive_day_after"]


async def get_forecast_data(
    client: dp.DataPlatformDataServiceStub,
    location: dp.ListLocationsResponseLocationSummary,
    start_date: datetime,
    end_date: datetime,
    selected_forecasters: list[dp.Forecaster],
) -> pd.DataFrame:
    """Get forecast data for the given location and time window."""
    all_data_df = []

    for forecaster in selected_forecasters:
        forecaster_data_df = await get_forecast_data_one_forecaster(
            client,
            location,
            start_date,
            end_date,
            forecaster,
        )
        all_data_df.append(forecaster_data_df)

    all_data_df = pd.concat(all_data_df, ignore_index=True)

    # get watt value
    all_data_df["p50_watts"] = all_data_df["p50_fraction"].astype(float) * all_data_df[
        "effective_capacity_watts"
    ].astype(float)

    for col in ["p10", "p25", "p75", "p90"]:
        if col in all_data_df.columns:
            all_data_df[f"{col}_watts"] = all_data_df[col].astype(float) * all_data_df[
                "effective_capacity_watts"
            ].astype(float)

    return all_data_df


@cached(ttl=300, cache=Cache.MEMORY, key_builder=key_builder_remove_client)
async def get_forecast_data_one_forecaster(
    client: dp,
    location: dp.ListLocationsResponseLocationSummary,
    start_date: datetime,
    end_date: datetime,
    selected_forecaster: dp.Forecaster,
) -> pd.DataFrame:
    """Get forecast data for one forecaster for the given location and time window."""
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
                start_timestamp_utc=temp_start_date,
                end_timestamp_utc=temp_end_date,
            ),
            forecasters=[selected_forecaster],
        )
        forecasts = []
        async for chunk in client.stream_forecast_data(stream_forecast_data_request):
            forecasts.append(
                chunk.to_dict(include_default_values=True, casing=betterproto.Casing.SNAKE),
            )

        if len(forecasts) > 0:
            all_data_df.append(
                pd.DataFrame.from_dict(forecasts)
                .pipe(lambda df: df.join(pd.json_normalize(df["other_statistics_fractions"])))
                .drop("other_statistics_fractions", axis=1),
            )

        temp_start_date = temp_start_date + timedelta(days=30)

    all_data_df = pd.concat(all_data_df, ignore_index=True)

    # create column forecaster_name, its forecaster_fullname with version removed
    all_data_df["forecaster_name"] = all_data_df["forecaster_fullname"].apply(
        lambda x: x.rsplit(":", 1)[0],  # split from right, max 1 split
    )

    return all_data_df


@cached(ttl=300, cache=Cache.MEMORY, key_builder=key_builder_remove_client)
async def get_all_observations(
    client: dp.DataPlatformDataServiceStub,
    location: dp.ListLocationsResponseLocationSummary,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Get all observations for the given location and time window."""
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
                get_observations_request,
            )

            observations = []
            for chunk in get_observations_response.values:
                observations.append(
                    chunk.to_dict(include_default_values=True, casing=betterproto.Casing.SNAKE),
                )

            observation_one_df.append(pd.DataFrame.from_dict(observations))

            temp_start_date = temp_start_date + timedelta(days=7)

        observation_one_df = pd.concat(observation_one_df, ignore_index=True)
        observation_one_df = observation_one_df.sort_values(by="timestamp_utc")
        observation_one_df["observer_name"] = observer_name

        all_observations_df.append(observation_one_df)

    all_observations_df = pd.concat(all_observations_df, ignore_index=True)

    all_observations_df["value_watts"] = all_observations_df["value_fraction"].astype(
        float,
    ) * all_observations_df["effective_capacity_watts"].astype(float)
    all_observations_df["timestamp_utc"] = pd.to_datetime(all_observations_df["timestamp_utc"])

    return all_observations_df


async def get_all_data(
    client: dp.DataPlatformDataServiceStub,
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
    if "pvlive_day_after" in all_observations_df["observer_name"].values:
        one_observations_df = all_observations_df[
            all_observations_df["observer_name"] == "pvlive_day_after"
        ]

    # make target_timestamp_utc
    all_forecast_data_df["init_timestamp"] = pd.to_datetime(all_forecast_data_df["init_timestamp"])
    all_forecast_data_df["target_timestamp_utc"] = pd.to_datetime(
        all_forecast_data_df["init_timestamp"],
    ) + pd.to_timedelta(all_forecast_data_df["horizon_mins"], unit="m")

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
    merged_df["effective_capacity_watts_observation"] = merged_df[
        "effective_capacity_watts_observation"
    ].astype(float)

    # error and absolute error
    merged_df["error"] = merged_df["p50_watts"] - merged_df["value_watts"]
    merged_df["absolute_error"] = merged_df["error"].abs()

    return {
        "merged_df": merged_df,
        "all_forecast_data_df": all_forecast_data_df,
        "all_observations_df": all_observations_df,
        "forecast_seconds": forecast_seconds,
        "observation_seconds": observation_seconds,
    }


def align_t0(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Align t0 forecasts for different forecasters."""
    # get all forecaster names
    forecaster_names = merged_df["forecaster_name"].unique()

    # align t0 for each forecaster
    t0s_per_forecaster = {}
    for forecaster_name in forecaster_names:
        forecaster_df = merged_df[merged_df["forecaster_name"] == forecaster_name]

        t0s = forecaster_df["init_timestamp"].unique()
        t0s_per_forecaster[forecaster_name] = set(t0s)

    # find common t0s
    common_t0s = set.intersection(*t0s_per_forecaster.values())

    # align common t0s in merged_df
    merged_df = merged_df[merged_df["init_timestamp"].isin(common_t0s)]

    return merged_df
