"""Backend logic for the Data Platform Forecasting Explorer app, including data fetching and processing."""

import numpy as np
import asyncio
import datetime

import pandas as pd
import streamlit as st

from ocf.dp.dp_data import messages_pb2, service_pb2_grpc
from ocf.dp.dp import common_pb2
from google.protobuf.json_format import MessageToDict


async def fetch_timeseries(
    client: service_pb2_grpc.DataPlatformDataServiceStub,
    location_uuid: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    horizon_mins: int,
    forecasters: list[messages_pb2.Forecaster],
    init_times_utc: list[datetime.datetime] | None = None,
) -> pd.DataFrame:
    """Directly calls GetForecastAsTimeseries for selected models and init times."""

    time_window = messages_pb2.TimeWindow(
        start_timestamp_utc=start_date, end_timestamp_utc=end_date
    )
    time_windows = []
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + datetime.timedelta(days=7), end_date)
        time_windows.append(
            messages_pb2.TimeWindow(
                start_timestamp_utc=current_start, end_timestamp_utc=current_end
            )
        )
        current_start = current_end

    times_to_fetch = init_times_utc if init_times_utc else [None]

    async def fetch_one(
        forecaster_obj: messages_pb2.Forecaster,
        window: messages_pb2.TimeWindow,
        init_time: datetime.datetime | None,
    ):
        req = messages_pb2.GetForecastAsTimeseriesRequest(
            location_uuid=location_uuid,
            energy_source=common_pb2.EnergySource.ENERGY_SOURCE_SOLAR,
            horizon_mins=horizon_mins,
            time_window=window,
            forecaster=forecaster_obj,
            initialization_timestamp_utc=init_time,
        )

        try:
            resp = await client.GetForecastAsTimeseries(req)
            rows = []
            for val in resp.values:
                row = {
                    "target_timestamp_utc": val.target_timestamp_utc.ToDatetime(
                        tzinfo=datetime.UTC
                    ),
                    "initialization_timestamp_utc": val.initialization_timestamp_utc.ToDatetime(
                        tzinfo=datetime.UTC
                    ),
                    "created_timestamp_utc": val.created_timestamp_utc.ToDatetime(
                        tzinfo=datetime.UTC
                    ),
                    "effective_capacity_watts": val.effective_capacity_watts,
                    "forecaster_name": forecaster_obj.forecaster_name,
                    "location_uuid": resp.location_uuid,
                    "horizon_mins": (
                        val.target_timestamp_utc.ToDatetime(tzinfo=datetime.UTC)
                        - val.initialization_timestamp_utc.ToDatetime(
                            tzinfo=datetime.UTC
                        )
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

    tasks = [
        fetch_one(f, w, t)
        for f in forecasters
        for t in times_to_fetch
        for w in time_windows
    ]

    results = await asyncio.gather(*tasks)
    all_rows = [item for sublist in results for item in sublist]

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df["target_timestamp_utc"] = pd.to_datetime(df["target_timestamp_utc"])
        if "initialization_timestamp_utc" in df.columns:
            df["initialization_timestamp_utc"] = pd.to_datetime(
                df["initialization_timestamp_utc"]
            )
        df = df.sort_values(
            ["forecaster_name", "initialization_timestamp_utc", "target_timestamp_utc"]
        ).reset_index(drop=True)

    return df


async def fetch_observations(
    client: service_pb2_grpc.DataPlatformDataServiceStub,
    location_uuid: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    observers: list[str],
    energy_source: common_pb2.EnergySource = common_pb2.EnergySource.ENERGY_SOURCE_SOLAR,
) -> pd.DataFrame:
    """Directly calls GetObservationsAsTimeseries for selected observers."""

    time_window = messages_pb2.TimeWindow(
        start_timestamp_utc=start_date, end_timestamp_utc=end_date
    )
    time_windows = []
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + datetime.timedelta(days=7), end_date)
        time_windows.append(
            messages_pb2.TimeWindow(
                start_timestamp_utc=current_start, end_timestamp_utc=current_end
            )
        )
        current_start = current_end

    # Run requests concurrently for all selected observers
    async def fetch_one(obs_name: str, window: messages_pb2.TimeWindow):
        req = messages_pb2.GetObservationsAsTimeseriesRequest(
            location_uuid=location_uuid,
            observer_name=obs_name,
            energy_source=energy_source,
            time_window=window,
        )

        try:
            resp = await client.GetObservationsAsTimeseries(req)
            rows = []
            for val in resp.values:
                rows.append(
                    {
                        "target_timestamp_utc": val.timestamp_utc.ToDatetime(
                            tzinfo=datetime.UTC
                        ),
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

    results = await asyncio.gather(
        *[fetch_one(obs, w) for obs in observers for w in time_windows]
    )
    all_rows = [item for sublist in results for item in sublist]

    obs_columns = [
        "target_timestamp_utc",
        "value_fraction",
        "effective_capacity_watts",
        "observer_name",
        "location_uuid",
        "value_watts",
    ]
    df = (
        pd.DataFrame(all_rows, columns=obs_columns)
        if all_rows
        else pd.DataFrame(columns=obs_columns)
    )

    if not df.empty:
        df["target_timestamp_utc"] = pd.to_datetime(df["target_timestamp_utc"])
        df = df.sort_values(["observer_name", "target_timestamp_utc"]).reset_index(
            drop=True
        )

    return df


async def fetch_all_forecasts(
    client: service_pb2_grpc.DataPlatformDataServiceStub,
    location_uuid: str,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    forecasters: list[messages_pb2.Forecaster],
) -> pd.DataFrame:
    """Fetches all forecasts for all t0s within a time window using stream_forecast_data."""

    req = messages_pb2.StreamForecastDataRequest(
        location_uuids=[location_uuid],
        energy_source=common_pb2.EnergySource.ENERGY_SOURCE_SOLAR,
        time_window=messages_pb2.StreamForecastDataRequest.TimeWindow(
            start_timestamp_utc=start_date, end_timestamp_utc=end_date
        ),
        forecasters=forecasters,
    )

    forecast_values = []
    async for chunk in client.StreamForecastData(req):
        forecast_values.extend(chunk.values)

    df = (
        pd.DataFrame.from_dict(
            [
                MessageToDict(
                    f,
                    always_print_fields_with_no_presence=True,
                    preserving_proto_field_name=True,
                )
                for f in forecast_values
            ]
        )
        .pipe(lambda df: df.join(
            pd.json_normalize(df["other_statistics_fractions"].tolist()).set_index(df.index)
        ))
        .drop(
            "other_statistics_fractions",
            axis=1,
        )
        .assign(
            **{
                f"{k}_watts": lambda df, k=k: (
                    pd.to_numeric(df[k], errors="coerce") *
                    pd.to_numeric(df["effective_capacity_watts"], errors="coerce")
                )
                .round()
                .astype("Int64")
                for k in chunk.values[0].other_statistics_fractions.keys()
            },
        )
        .drop(
            columns=[k for k in chunk.values[0].other_statistics_fractions.keys()],
        )
        .assign(
            **{
                "p50_watts": lambda df: (
                    pd.to_numeric(df["p50_fraction"], errors="coerce") *
                    pd.to_numeric(df["effective_capacity_watts"], errors="coerce")
                )
                .round()
                .astype("Int64"),

                "target_timestamp_utc": lambda df: (
                    pd.to_datetime(df["init_timestamp"], utc=True, errors="coerce")
                    + pd.to_timedelta(pd.to_numeric(df["horizon_mins"], errors="coerce"), unit="m")
                ),
                "initialization_timestamp_utc": lambda df: pd.to_datetime(
                    df["init_timestamp"],
                    utc=True,
                    errors="coerce"
                ),
                "created_timestamp_utc": lambda df: pd.to_datetime(
                    df["created_timestamp_utc"],
                    utc=True,
                    errors="coerce"
                ),
                "forecaster_name": lambda df: df["forecaster_fullname"].apply(
                    lambda x: x.split(":")[0] if isinstance(x, str) and ":" in x else x
                ),
            },
        )
        .drop(
            columns=[
                "p50_fraction",
                "init_timestamp",
                "forecaster_fullname",
            ],
        )
        .sort_values(
            by=[
                "location_uuid",
                "forecaster_name",
                "initialization_timestamp_utc",
                "created_timestamp_utc",
                "target_timestamp_utc",
            ]
        )
    )

    return df
