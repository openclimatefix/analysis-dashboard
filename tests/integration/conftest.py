import subprocess
import time
import os
import pytest


@pytest.fixture(scope="session")
def data_platform():
    """
    Starts the data-platform using `make run` before tests.
    Kills it after all integration tests finish.
    """
    env = os.environ.copy()
    env["DATA_PLATFORM_HOST"] = "localhost"
    env["DATA_PLATFORM_PORT"] = "50051"

    proc = subprocess.Popen(
        ["make", "run"],
        # this currently expects data-platform to be available at ../data-platform.
        # will change later
        cwd="../data-platform",  
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # give gRPC server time to boot
    time.sleep(5)

    yield

    proc.terminate()
    proc.wait()
