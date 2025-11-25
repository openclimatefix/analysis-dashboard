from datetime import UTC, datetime, timedelta

import pandas as pd
import streamlit as st
from dp_sdk.ocf import dp

from dataplatform.forecast.constanst import metrics


async def setup_page(client) -> dict:
    # Select Country
    country = st.sidebar.selectbox("TODO Select a Country", ["UK", "NL"], index=0)

    # Select Location Type
    location_types = [
        dp.LocationType.NATION,
        dp.LocationType.GSP,
        dp.LocationType.SITE,
    ]
    location_type = st.sidebar.selectbox("Select a Location Type", location_types, index=0)

    # List Location
    list_locations_request = dp.ListLocationsRequest(location_type_filter=location_type)
    list_locations_response = await client.list_locations(list_locations_request)
    all_locations = list_locations_response.locations
    
    location_names = {loc.location_name:loc for loc in all_locations}
    if location_type == dp.LocationType.GSP:
        location_names = {f'{int(loc.metadata.fields['gsp_id'].number_value)}:{loc.location_name}': loc for loc in all_locations}
        # sort by gsp id
        location_names = dict(sorted(location_names.items(), key=lambda item: int(item[0].split(":")[0])))

    # slect locations
    selected_location_name = st.sidebar.selectbox("Select a Location", location_names.keys(), index=0)
    selected_location = location_names[selected_location_name]

    # get models
    get_forecasters_request = dp.ListForecastersRequest()
    get_forecasters_response = await client.list_forecasters(get_forecasters_request)
    forecasters = get_forecasters_response.forecasters
    forecaster_names = sorted(list(set([forecaster.forecaster_name for forecaster in forecasters])))
    if "pvnet_v2" in forecaster_names:
        default_index = forecaster_names.index("pvnet_v2")
    else:
        default_index = 0
    selected_forecaster_name = st.sidebar.multiselect(
        "Select a Forecaster",
        forecaster_names,
        default=forecaster_names[default_index],
    )
    selected_forecasters = [
        forecaster
        for forecaster in forecasters
        if forecaster.forecaster_name in selected_forecaster_name
    ]

    # select start and end date
    start_date = st.sidebar.date_input("Start date:", datetime.now().date() - timedelta(days=7))
    end_date = st.sidebar.date_input("End date:", datetime.now().date() + timedelta(days=3))
    start_date = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=UTC)
    end_date = datetime.combine(end_date, datetime.min.time()).replace(tzinfo=UTC) - timedelta(seconds=1)

    # select forecast type
    selected_forecast_type = st.sidebar.selectbox(
        "Select a Forecast Type",
        ["Current", "Horizon", "t0"],
        index=0,
    )

    selected_forecast_horizon = None
    selected_t0s = None
    if selected_forecast_type == "Horizon":
        selected_forecast_horizon = st.sidebar.selectbox(
            "Select a Forecast Horizon",
            list(range(0, 24*60, 30)),
            index=3,
        )
    if selected_forecast_type == "t0":

        # make datetimes every 30 minutes from start_date to end_date
        all_t0s = pd.date_range(start=start_date, end=end_date, freq='30T').to_pydatetime().tolist()

        
        selected_t0s = st.sidebar.multiselect(
            "Select t0s",
            all_t0s,
            default=all_t0s[:5],
        )

    # select units
    default_unit_index = 2  # MW
    units = st.sidebar.selectbox("Select Units", ["W", "kW", "MW", "GW"], index=default_unit_index)
    scale_factors = {"W": 1, "kW": 1e3, "MW": 1e6, "GW": 1e9}
    scale_factor = scale_factors[units]

    selected_metric = st.sidebar.selectbox("Select a Metrics", metrics.keys(), index=0)

    return {
        "selected_location": selected_location,
        "selected_forecasters": selected_forecasters,
        "start_date": start_date,
        "end_date": end_date,
        "selected_forecast_type": selected_forecast_type,
        "scale_factor": scale_factor,
        "selected_metric": selected_metric,
        "forecaster_names": forecaster_names,
        "selected_forecast_horizon": selected_forecast_horizon,
        "selected_t0s": selected_t0s,
        "units": units,
    }
