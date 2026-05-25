"""Integration tests for the DP Adjuster page functions."""

from datetime import UTC, datetime

import pytest
from grpclib.exceptions import GRPCError
from grpclib.const import Status
from ocf import dp
from streamlit.testing.v1 import AppTest

from dataplatform.adjuster import get_observer_names, get_week_average_deltas
from dataplatform.forecast.constant import observer_names as default_observer_names
from tests.integration.conftest import (
    create_location_grpc,
    list_locations_grpc,
    random_location_name,
)

_ADJUSTER_TEST_FORECASTER_NAME = "test_adjuster"
_ADJUSTER_TEST_FORECASTER_VERSION = "1.3.0"
_ADJUSTER_TEST_FORECASTER_LABEL = (
    f"{_ADJUSTER_TEST_FORECASTER_NAME}:{_ADJUSTER_TEST_FORECASTER_VERSION}"
)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_observer_names_falls_back_to_defaults(data_client):
    """
    In a fresh DB with no observers, get_observer_names returns
    the fallback list from the observer_names constant.
    """
    result = await get_observer_names.__wrapped__(data_client)
    assert result == list(default_observer_names)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_observer_names_contains_all_defaults(data_client):
    """Result contains all default observer names and has no duplicates."""
    result = await get_observer_names.__wrapped__(data_client)
    assert isinstance(result, list)
    assert len(result) == len(set(result)), "no duplicates"
    for name in default_observer_names:
        assert name in result


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_week_average_deltas_not_found_without_location_source(data_client):
    """
    The data platform requires a "location source" record to serve deltas.
    CreateLocation alone doesn't create that record, so the API returns
    NOT_FOUND - which is what the adjuster page catches and shows as an error.
    """
    location_name = random_location_name()
    await create_location_grpc(data_client, location_name)
    list_response = await list_locations_grpc(data_client)
    location = next(
        loc for loc in list_response.locations if loc.location_name == location_name
    )

    forecaster = dp.Forecaster(forecaster_name="pvnet_v2", forecaster_version="1.0")
    pivot = datetime(2024, 1, 15, 9, 0, tzinfo=UTC)

    with pytest.raises(GRPCError) as exc_info:
        await get_week_average_deltas(
            client=data_client,
            location=location,
            forecaster=forecaster,
            observer_name="pvlive_day_after",
            pivot_timestamp_utc=pivot,
        )

    assert exc_info.value.status == Status.NOT_FOUND


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_get_week_average_deltas_not_found_for_all_default_observers(data_client):
    """
    NOT_FOUND is raised consistently for every default observer name
    when no location source exists — the error is not observer-specific.
    """
    location_name = random_location_name()
    await create_location_grpc(data_client, location_name)
    list_response = await list_locations_grpc(data_client)
    location = next(
        loc for loc in list_response.locations if loc.location_name == location_name
    )

    forecaster = dp.Forecaster(forecaster_name="pvnet_v2", forecaster_version="1.0")
    pivot = datetime(2024, 6, 1, 10, 30, tzinfo=UTC)

    for observer_name in default_observer_names:
        with pytest.raises(GRPCError) as exc_info:
            await get_week_average_deltas(
                client=data_client,
                location=location,
                forecaster=forecaster,
                observer_name=observer_name,
                pivot_timestamp_utc=pivot,
            )
        assert exc_info.value.status == Status.NOT_FOUND


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_async_dp_adjuster_page(data_client):
    """
    - create a NATION location via grpc
    - create a forecaster via grpc
    - run the adjuster Streamlit page
    - change location type sidebar selectbox to NATION
    - select the created location and forecaster in the UI
    - assert no exception
    - assert no "no locations found" warning (SITE location exists)
    - assert fetch error shown (no adjuster source data in the test DB)
    """
    location_name = random_location_name()
    await create_location_grpc(
        data_client,
        location_name,
        location_type=dp.LocationType.NATION,
    )
    await data_client.create_forecaster(
        dp.CreateForecasterRequest(
            name=_ADJUSTER_TEST_FORECASTER_NAME,
            version=_ADJUSTER_TEST_FORECASTER_VERSION,
        )
    )

    app = AppTest.from_file("src/dataplatform/adjuster.py")
    app.run()

    app.selectbox("adjuster_location_type").set_value(dp.LocationType.NATION)
    app.run()

    app.selectbox("adjuster_location").set_value(location_name)
    app.selectbox("adjuster_forecaster").set_value(_ADJUSTER_TEST_FORECASTER_LABEL)
    app.run()

    assert not app.exception
    assert not any("no locations found" in w.value.lower() for w in app.warning)
    assert any("failed to fetch" in e.value.lower() for e in app.error)
