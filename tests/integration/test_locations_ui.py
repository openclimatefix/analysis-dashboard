import uuid
import pytest
import pytest
from streamlit.testing.v1 import AppTest
from dp_sdk.ocf import dp
import pandas as pd


@pytest.fixture
def app():
    test_app = AppTest.from_file("src/dataplatform/toolbox/main.py")
    test_app.run()
    return test_app


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_list_locations_ui(app, data_client: dp.DataPlatformDataServiceStub):
    # -----------------
    # LIST LOCATIONS (UI)
    # -----------------

    # Create some locations via gRPC
    location_names = []
    for i in range(3):
        location_name = "ui_location_" + str(uuid.uuid4()).replace("-", "_")
        location_names.append(location_name)
        await data_client.create_location(
            dp.CreateLocationRequest(
                location_name=location_name,
                energy_source=1,
                geometry_wkt="Point(0 0)",
                location_type=1,
                effective_capacity_watts=100,
                metadata={}
            )
        )
    app.run()
    # Expand filter options and click list button
    app.selectbox("list_loc_energy").set_value("All")
    app.selectbox("list_loc_type").set_value("All")
    app.text_input("list_loc_user").set_value("")
    app.run()
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
    location_name = "ui_location_" + str(uuid.uuid4()).replace("-", "_")

    # Create location via gRPC
    response = await data_client.create_location(
            dp.CreateLocationRequest(
                location_name=location_name,
                energy_source=1,
                geometry_wkt="Point(0 0)",
                location_type=1,
                effective_capacity_watts=100,
                metadata={}
            )
        )
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
    location_name = "ui_location_" + str(uuid.uuid4()).replace("-", "_")

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

    # Verify location was actually created via gRPC
    response = await data_client.list_locations(
        dp.ListLocationsRequest()
    )
    assert any(loc.location_name == location_name for loc in response.locations)
    