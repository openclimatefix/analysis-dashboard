"""Setup Forecast Streamlit Page."""

import datetime as dt
import dataclasses

import pandas as pd
import streamlit as st
from aiocache import Cache, cached
from ocf import dp

from dataplatform.forecast.cache import key_builder_remove_client
from dataplatform.forecast.constant import cache_seconds, metrics


@cached(ttl=cache_seconds, cache=Cache.MEMORY, key_builder=key_builder_remove_client)
async def get_location_names(
    client: dp.DataPlatformDataServiceStub,
) -> dict:
    """Get location names."""
    list_locations_request = dp.ListLocationsRequest()
    list_locations_response = await client.list_locations(list_locations_request)
    all_locations = list_locations_response.locations

    location_names = {loc.location_name: loc for loc in all_locations}
    location_names = dict(
        sorted(
            location_names.items(),
            key=lambda item: (
                item[1].metadata.fields["gsp_id"].number_value
                if "gsp_id" in item[1].metadata.fields
                else float("inf")
            ),
        )
    )

    return location_names


@cached(ttl=cache_seconds, cache=Cache.MEMORY, key_builder=key_builder_remove_client)
async def get_forecasters(
    client: dp.DataPlatformDataServiceStub,
) -> list[dp.Forecaster]:
    """Get all forecasters."""
    get_forecasters_request = dp.ListForecastersRequest()
    get_forecasters_response = await client.list_forecasters(get_forecasters_request)
    forecasters = get_forecasters_response.forecasters
    return forecasters


@dataclasses.dataclass
class PageConfig:
    location: dp.ListLocationsResponseLocationSummary
    forecasters: list[dp.Forecaster]
    start_date: dt.datetime
    end_date: dt.datetime
    forecast_type: str
    scale_factor: float
    metric: str
    forecast_horizon: int
    t0s: list[dt.datetime] | None
    units: str
    strict_horizon_filtering: bool


async def setup_page(client: dp.DataPlatformDataServiceStub) -> PageConfig:
    """Setup the Streamlit page with sidebar options."""
    location_names = await get_location_names(client)
    selected_location_name = st.sidebar.selectbox(
        "Location",
        location_names.keys(),
        index=0,
    )
    selected_location = location_names[selected_location_name]

    forecasters = await get_forecasters(client)
    forecaster_names = sorted(
        {forecaster.forecaster_name for forecaster in forecasters}
    )
    default_index = (
        forecaster_names.index("pvnet_v2") if "pvnet_v2" in forecaster_names else 0
    )
    selected_forecaster_name = st.sidebar.multiselect(
        "Forecaster",
        forecaster_names,
        default=forecaster_names[default_index],
    )

    selected_forecasters = [
        forecaster
        for forecaster in forecasters
        if forecaster.forecaster_name in selected_forecaster_name
    ]

    now = dt.datetime.now(tz=dt.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    window = st.sidebar.date_input(
        "Time window",
        (
            (now - dt.timedelta(days=1)).date(),
            (now + dt.timedelta(days=2)).date(),
        ),
        (now - dt.timedelta(days=365)).date(),
        (now + dt.timedelta(days=365)).date(),
    )
    start_date = dt.datetime.combine(window[0], now.time()).replace(tzinfo=dt.UTC)
    end_date = (start_date + dt.timedelta(days=2)).replace(tzinfo=dt.UTC) - dt.timedelta(seconds=1)
    if len(window) == 2:
        end_date = dt.datetime.combine(window[1], now.time()).replace(tzinfo=dt.UTC) - dt.timedelta(seconds=1)

    selected_forecast_type = st.sidebar.selectbox(
        "Forecast Type",
        ["Current", "Horizon", "t0"],
        index=0,
    )

    selected_forecast_horizon = 0
    strict_horizon_filtering = False
    selected_t0s = None

    if selected_forecast_type == "Horizon":
        selected_forecast_horizon = st.sidebar.selectbox(
            "Minimum Forecast Horizon (minutes)",
            list(range(0, 36 * 60, 30)),
            index=3,
        )
        strict_horizon_filtering = st.sidebar.checkbox(
            "Exact horizons only",
            value=False,
            help="Only show forecasts that exactly match the selected horizon, "
            "if not, we use any forecast horizon greater or equal than",
        )

    if selected_forecast_type == "t0":
        # Make datetimes every 30 minutes from start_date to end_date
        all_t0s = (
            pd.date_range(start=start_date, end=end_date, freq="30min")
            .to_pydatetime()
            .tolist()
        )
        t0_dict = {t.strftime("%Y-%m-%d %H:%M"): t for t in all_t0s}

        selected_t0_strs = st.sidebar.multiselect(
            "Desired t0s",
            options=list(t0_dict.keys()),
            default=list(t0_dict.keys())[:5],
        )
        selected_t0s = [t0_dict[t_str] for t_str in selected_t0_strs]

    default_unit_index = 2  # MW
    units = st.sidebar.selectbox(
        "Units", ["W", "kW", "MW", "GW"], index=default_unit_index
    )
    scale_factors = {"W": 1, "kW": 1e3, "MW": 1e6, "GW": 1e9}
    scale_factor = scale_factors[units]

    selected_metric = st.sidebar.selectbox("Desired Metric", metrics.keys(), index=0)

    return PageConfig(
        location=selected_location,
        forecasters=selected_forecasters,
        start_date=start_date,
        end_date=end_date,
        forecast_type=selected_forecast_type,
        scale_factor=scale_factor,
        metric=selected_metric,
        forecast_horizon=selected_forecast_horizon,
        t0s=selected_t0s,
        units=units,
        strict_horizon_filtering=strict_horizon_filtering,
    )
