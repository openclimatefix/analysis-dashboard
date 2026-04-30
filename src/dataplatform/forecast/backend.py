"""Backend logic for the Data Platform Forecasting Explorer app, including data fetching and processing."""

import asyncio
import datetime

import pandas as pd
import streamlit as st

from ocf import dp


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
    time_windows = []
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + datetime.timedelta(days=7), end_date)
        time_windows.append(
            dp.TimeWindow(
                start_timestamp_utc=current_start,
                end_timestamp_utc=current_end
            )
        )
        current_start = current_end

    times_to_fetch = init_times_utc if init_times_utc else [None]

    async def fetch_one(
        forecaster_obj: dp.Forecaster,
        window: dp.TimeWindow,
        init_time: datetime.datetime | None
    ):
        req = dp.GetForecastAsTimeseriesRequest(
            location_uuid=location_uuid,
            energy_source=dp.EnergySource.SOLAR,
            horizon_mins=horizon_mins,
            time_window=window,
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

    tasks = [fetch_one(f, w, t) for f in forecasters for t in times_to_fetch for w in time_windows]

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
    time_windows = []
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + datetime.timedelta(days=7), end_date)
        time_windows.append(
            dp.TimeWindow(
                start_timestamp_utc=current_start,
                end_timestamp_utc=current_end
            )
        )
        current_start = current_end


    # Run requests concurrently for all selected observers
    async def fetch_one(obs_name: str, window: dp.TimeWindow):
        req = dp.GetObservationsAsTimeseriesRequest(
            location_uuid=location_uuid,
            observer_name=obs_name,
            energy_source=energy_source,
            time_window=window,
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

    results = await asyncio.gather(*[fetch_one(obs, w) for obs in observers for w in time_windows])
    all_rows = [item for sublist in results for item in sublist]

    df = pd.DataFrame(all_rows)

    if not df.empty:
        df["target_timestamp_utc"] = pd.to_datetime(df["target_timestamp_utc"])
        df = df.sort_values(["observer_name", "target_timestamp_utc"]).reset_index(drop=True)

    return df

