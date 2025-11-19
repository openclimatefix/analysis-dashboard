from datetime import timedelta
import os
from dp_sdk.ocf import dp
import pandas as pd
import betterproto
from aiocache import Cache, cached

data_platform_host = os.getenv("DATA_PLATFORM_HOST", "localhost")
data_platform_port = int(os.getenv("DATA_PLATFORM_PORT", "50051"))

# TODO make this dynamic
observer_names = ["pvlive_in_day", "pvlive_day_after"]


def key_builder_remove_client(func, *args, **kwargs):
    """Custom key builder that ignores the client argument for caching purposes."""

    key = f"{func.__name__}:"
    for arg in args:
        if isinstance(arg, dp.DataPlatformDataServiceStub):
            continue
        key += f"{arg}-"

    for k, v in kwargs.items():
        key += f"{k}={v}-"

    return key


async def get_forecast_data(
    _client, location, start_date, end_date, selected_forecasters
) -> pd.DataFrame:
    all_data_df = []

    for forecaster in selected_forecasters:
        forecaster_data_df = await get_forecast_data_one_forecaster(
            _client, location, start_date, end_date, forecaster
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
    client, location, start_date, end_date, selected_forecaster
) -> pd.DataFrame:
    all_data_df = []

    # loop over 30 days of data
    temp_start_date = start_date
    while temp_start_date <= end_date:
        temp_end_date = temp_start_date + timedelta(days=7)
        if temp_end_date > end_date:
            temp_end_date = end_date

        # fetch data
        stream_forecast_data_request = dp.StreamForecastDataRequest(
            location_uuid=location.location_uuid,
            energy_source=dp.EnergySource.SOLAR,
            time_window=dp.TimeWindow(
                start_timestamp_utc=temp_start_date, end_timestamp_utc=temp_end_date
            ),
            forecasters=[selected_forecaster],
        )
        forecasts = []
        async for chunk in client.stream_forecast_data(stream_forecast_data_request):
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

    # create column forecaster_name, its forecaster_fullname with version removed
    all_data_df["forecaster_name"] = all_data_df["forecaster_fullname"].apply(
        lambda x: x.rsplit(":", 1)[0]  # split from right, max 1 split
    )

    return all_data_df


@cached(ttl=300, cache=Cache.MEMORY, key_builder=key_builder_remove_client)
async def get_all_observations(_client, location, start_date, end_date) -> pd.DataFrame:
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
            get_observations_response = await _client.get_observations_as_timeseries(
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