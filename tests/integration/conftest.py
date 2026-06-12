import time
import uuid
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import PortWaitStrategy
from testcontainers.postgres import PostgresContainer
import pytest_asyncio
from importlib.metadata import version
import os
from streamlit.testing.v1 import AppTest
from ocf.dp.dp import common_pb2
from ocf.dp.dp_data import messages_pb2, service_pb2_grpc
import grpc.aio

DATA_PLATFORM_GRPC_PORT = 50051
DATA_PLATFORM_STARTUP_TIMEOUT_SECONDS = 60

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
        f"ghcr.io/openclimatefix/data-platform-pgdb:{version('dp_sdk')}",
        username="postgres",
        password="postgres",
        dbname="postgres",
    ).with_env("POSTGRES_HOST", "db") as postgres:
        
        postgres_container = postgres.get_wrapped_container()
        assert postgres_container is not None
        docker_client = postgres.get_docker_client()
        postgres_network = docker_client.network_name(postgres_container.id)
        postgres_ip = docker_client.bridge_ip(postgres_container.id)
        database_url = (
            f"postgres://{postgres.username}:{postgres.password}@"
            f"{postgres_ip}:{postgres.port}/{postgres.dbname}"
        )

        dp_container = (
            DockerContainer(
                image=f"ghcr.io/openclimatefix/data-platform:{version('dp_sdk')}",
                env={"DATABASE_URL": database_url},
                ports=[DATA_PLATFORM_GRPC_PORT],
            )
            .with_kwargs(network=postgres_network)
            .waiting_for(
                PortWaitStrategy(DATA_PLATFORM_GRPC_PORT).with_startup_timeout(
                    DATA_PLATFORM_STARTUP_TIMEOUT_SECONDS,
                ),
            )
        )
        with dp_container:
            time.sleep(3)

            host = dp_container.get_container_host_ip()
            port = dp_container.get_exposed_port(DATA_PLATFORM_GRPC_PORT)

            os.environ["DATA_PLATFORM_HOST"] = host
            os.environ["DATA_PLATFORM_PORT"] = str(port)

            channel = grpc.aio.insecure_channel(f"{host}:{port}")
            yield channel
            await channel.close()


@pytest_asyncio.fixture(scope="session")
async def data_client(dp_channel):
    return service_pb2_grpc.DataPlatformDataServiceStub(dp_channel)


@pytest.fixture
def app():
    test_app = AppTest.from_file("src/dataplatform/toolbox/main.py")
    test_app.run()
    return test_app

def random_location_name():
    return f"ui_location_{uuid.uuid4().hex}"

async def create_location_grpc(
    data_client,
    location_name: str,
    energy_source=common_pb2.EnergySource.ENERGY_SOURCE_SOLAR,
    location_type=common_pb2.LocationType.LOCATION_TYPE_SITE,
):
    return await data_client.CreateLocation(
        messages_pb2.CreateLocationRequest(
            location_name=location_name,
            energy_source=energy_source,
            geometry_wkt="POINT(0 0)",
            location_type=location_type,
            effective_capacity_watts=100,
            metadata={},
        )
    )


async def list_locations_grpc(data_client):
    return await data_client.ListLocations(messages_pb2.ListLocationsRequest())

