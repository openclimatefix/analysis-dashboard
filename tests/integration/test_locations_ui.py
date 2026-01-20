import uuid
import pytest
from dp_sdk.ocf import dp
import pandas as pd

from tests.integration.conftest import (
    create_location_grpc, list_locations_grpc, random_location_name
)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_list_locations_ui(app, data_client: dp.DataPlatformDataServiceStub):
    # -----------------
    # LIST LOCATIONS (UI)
    # -----------------

    # Create some locations via gRPC
    location_names = []

    for _ in range(3):
        name = random_location_name()
        location_names.append(name)
        await create_location_grpc(data_client, name)

    app.run()
    # Expand filter options and click list button
    app.selectbox("list_loc_energy").set_value("All")
    app.selectbox("list_loc_type").set_value("All")
    app.text_input("list_loc_user").set_value("")
    app.button("list_locations_button").click()
    app.run()

    dfs = [df.value for df in app.dataframe]
    # Combine all rendered dataframes
    all_tables = pd.concat(dfs)
    for location_name in location_names:
        assert location_name in all_tables["Name"].values


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_location_ui(app, data_client: dp.DataPlatformDataServiceStub):
    # -----------------
    # GET LOCATION (UI)
    # -----------------
    location_name = random_location_name()
    response = await create_location_grpc(data_client, location_name)
    location_uuid = response.location_uuid

    # Get location via UI
    app.text_input("get_loc_uuid").set_value(location_uuid)
    app.selectbox("get_loc_energy").set_value("SOLAR")
    app.checkbox("get_loc_geom").set_value(True)
    app.button("get_location_button").click()
    app.run()

    # Assert location details are displayed
    assert any(location_uuid in s.value for s in app.success)

@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_create_location_ui(app, data_client: dp.DataPlatformDataServiceStub):
    # -----------------
    # CREATE LOCATION (UI)
    # -----------------
    location_name = random_location_name()

    # Fill in form and create location via UI
    app.text_input("create_loc_name").set_value(location_name)
    app.selectbox("create_loc_energy").set_value("WIND")
    app.selectbox("create_loc_type").set_value("REGION")
    app.text_input("create_loc_geom").set_value("POINT(0 0)")
    app.number_input("create_loc_cap").set_value(100)
    app.text_area("create_loc_metadata").set_value("{}")
    app.button("create_location_button").click()
    app.run()

    # Assert success message in UI
    assert any("created" in s.value.lower() for s in app.success)

    # Verify creation via gRPC
    response = await list_locations_grpc(data_client)
    assert any(loc.location_name == location_name for loc in response.locations)
    