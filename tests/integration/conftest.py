import time
import uuid
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
import pytest_asyncio
from importlib.metadata import version
import os
from streamlit.testing.v1 import AppTest
from dp_sdk.ocf import dp
from grpclib.client import Channel


@pytest_asyncio.fixture(scope="session")
async def dp_channel():
    """
    Fixture to spin up a PostgreSQL container for the entire test session.
    This fixture uses `testcontainers` to start a fresh PostgreSQL container and provides
    the connection URL dynamically for use in other fixtures.
    """

    # we use a specific postgres image with postgis and pgpartman installed
    # TODO make a release of this, not using logging tag.
    with PostgresContainer(
        "ghcr.io/openclimatefix/data-platform-pgdb:logging",
        username="postgres",
        password="postgres",
        dbname="postgres",
    ).with_env("POSTGRES_HOST", "db") as postgres:
        database_url = postgres.get_connection_url()
        # we need to get ride of psycopg2, so the go driver works
        database_url = database_url.replace("postgresql+psycopg2", "postgres")
        # we need to change to host.docker.internal so the data platform container can see it
        # https://stackoverflow.com/questions/46973456/docker-access-localhost-port-from-container
        database_url = database_url.replace("localhost", "host.docker.internal")
        dp_container = (
            DockerContainer(
                image=f"ghcr.io/openclimatefix/data-platform:{version('dp_sdk')}",
            )
            .with_env("DATABASE_URL", database_url)
            .with_exposed_ports(50051)
        )
        with dp_container:
            time.sleep(3)

            host = dp_container.get_container_host_ip()
            port = dp_container.get_exposed_port(50051)

            os.environ["DATA_PLATFORM_HOST"] = host
            os.environ["DATA_PLATFORM_PORT"] = str(port)

            channel = Channel(host=host, port=port)
            yield channel
            channel.close()


@pytest_asyncio.fixture(scope="session")
async def admin_client(dp_channel):
    return dp.DataPlatformAdministrationServiceStub(dp_channel)


@pytest_asyncio.fixture(scope="session")
async def data_client(dp_channel):
    return dp.DataPlatformDataServiceStub(dp_channel)


@pytest.fixture
def app():
    test_app = AppTest.from_file("src/dataplatform/toolbox/main.py")
    test_app.run()
    return test_app


def random_org_name():
    return "org-test-" + str(uuid.uuid4())


def random_org_name():
    return "org-test-" + str(uuid.uuid4())


def random_user_oauth():
    return "user-oauth-id-" + str(uuid.uuid4())


def random_location_name():
    return f"ui_location_{uuid.uuid4().hex}"


def random_policy_name():
    return f"policy-test-{uuid.uuid4()}"


async def create_org_grpc(admin_client, org_name: str):
    await admin_client.create_organisation(
        dp.CreateOrganisationRequest(org_name=org_name, metadata={})
    )


async def get_org_grpc(admin_client, org_name: str):
    return await admin_client.get_organisation(
        dp.GetOrganisationRequest(org_name=org_name)
    )


async def create_user_grpc(admin_client, user_oauth_id: str, org_name: str):
    await admin_client.create_user(
        dp.CreateUserRequest(oauth_id=user_oauth_id, organisation=org_name, metadata={})
    )


async def get_user_grpc(admin_client, user_oauth_id: str):
    return await admin_client.get_user(dp.GetUserRequest(oauth_id=user_oauth_id))


async def add_user_to_org_grpc(admin_client, user_oauth_id: str, org_name: str):
    return await admin_client.add_user_to_organisation(
        dp.AddUserToOrganisationRequest(org_name=org_name, user_oauth_id=user_oauth_id)
    )


async def create_location_grpc(
    data_client,
    location_name: str,
    energy_source=dp.EnergySource.SOLAR,
    location_type=dp.LocationType.SITE,
):
    return await data_client.create_location(
        dp.CreateLocationRequest(
            location_name=location_name,
            energy_source=energy_source,
            geometry_wkt="POINT(0 0)",
            location_type=location_type,
            effective_capacity_watts=100,
            metadata={},
        )
    )


async def list_locations_grpc(data_client):
    return await data_client.list_locations(dp.ListLocationsRequest())


async def create_policy_group_grpc(admin_client, policy_name: str):
    await admin_client.create_location_policy_group(
        dp.CreateLocationPolicyGroupRequest(name=policy_name)
    )


async def get_policy_group_grpc(admin_client, policy_name: str):
    return await admin_client.get_location_policy_group(
        dp.GetLocationPolicyGroupRequest(location_policy_group_name=policy_name)
    )


async def add_policy_to_group_grpc(
    admin_client,
    policy_name: str,
    location_uuid: str,
    energy_source=dp.EnergySource.WIND,
    permission=dp.Permission.WRITE,
):
    await admin_client.add_location_policies_to_group(
        dp.AddLocationPoliciesToGroupRequest(
            location_policy_group_name=policy_name,
            location_policies=[
                dp.LocationPolicy(
                    location_id=location_uuid,
                    energy_source=energy_source,
                    permission=permission,
                )
            ],
        )
    )


async def add_policy_to_org_grpc(admin_client, org_name, policy_name):
    await admin_client.add_location_policy_group_to_organisation(
        dp.AddLocationPolicyGroupToOrganisationRequest(
            org_name=org_name,
            location_policy_group_name=policy_name,
        )
    )
