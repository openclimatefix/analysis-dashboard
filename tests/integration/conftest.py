import time
from testcontainers.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
import pytest
import pytest_asyncio
from importlib.metadata import version
import os

from dp_sdk.ocf import dp
from grpclib.client import Channel

@pytest_asyncio.fixture(scope="session")
async def client():
    """
    Fixture to spin up a PostgreSQL container for the entire test session.
    This fixture uses `testcontainers` to start a fresh PostgreSQL container and provides
    the connection URL dynamically for use in other fixtures.
    """

    # we use a specific postgres image with postgis and pgpartman installed
    # TODO make a release of this, not using logging tag.
    with (
        PostgresContainer(
            "ghcr.io/openclimatefix/data-platform-pgdb:logging",
            username="postgres",
            password="postgres",
            dbname="postgres",
        ).with_env("POSTGRES_HOST", "db")
    ) as postgres:
        
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
            client =  dp.DataPlatformAdministrationServiceStub(channel)
            yield client
            channel.close()