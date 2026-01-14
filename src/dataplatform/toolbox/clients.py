"""gRPC clients for the Data Platform Toolbox."""

import os
import streamlit as st

from grpc_requests import Client

def get_data_platform_url():
    """
    Get the gRPC endpoint for the Data Platform server from
    environment variables DATA_PLATFORM_HOST and DATA_PLATFORM_PORT.
    """
    host = os.environ.get("DATA_PLATFORM_HOST", "localhost")
    port = os.environ.get("DATA_PLATFORM_PORT", "50051")
    return f"{host}:{port}"


def get_admin_client():
    """Get or create the gRPC admin client."""
    dp_url = get_data_platform_url()
    try:
        client = Client.get_by_endpoint(dp_url)
        return client.service("ocf.dp.DataPlatformAdministrationService")
    except Exception as e:
        st.error(f"Failed to connect to Data Platform at {dp_url}: {e}")
        return None


def get_data_client():
    """Get or create the gRPC data client."""
    dp_url = get_data_platform_url()
    try:
        client = Client.get_by_endpoint(dp_url)
        return client.service("ocf.dp.DataPlatformDataService")
    except Exception as e:
        st.error(f"Failed to connect to Data Platform at {dp_url}: {e}")
        return None

