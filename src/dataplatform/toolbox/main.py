"""Data Platform Toolbox Streamlit Page Main Code."""

import asyncio
import grpc.aio
import streamlit as st
from dataplatform.toolbox.location import locations_section
from ocf.dp.dp import common_pb2
from ocf.dp.dp_data import messages_pb2, service_pb2_grpc
import os

# Color scheme (matching existing toolbox)
# teal:  #63BCAF (Get operations)
# blue: #7bcdf3 (Create operations)
# yellow: #ffd053 (Update operations)
# red: #E63946 (Delete operations)
# orange: #FF9736 (Info sections)


def dataplatform_toolbox_page() -> None:
    """Wrapper function that is not async to call the main async function."""
    asyncio.run(async_dataplatform_toolbox_page())


async def async_dataplatform_toolbox_page():
    """Async Main function for the Data Platform Toolbox Streamlit page."""
    host = os.environ.get("DATA_PLATFORM_HOST", "localhost")
    port = os.environ.get("DATA_PLATFORM_PORT", "50051")
    channel = grpc.aio.insecure_channel(f"{host}:{int(port)}")
    try:
        data_client = service_pb2_grpc.DataPlatformDataServiceStub(channel)

        st.markdown(
            '<h1 style="color:#63BCAF;font-size:48px;">Data Platform Toolbox</h1>',
            unsafe_allow_html=True,
        )

        # Create tabs for different sections
        tab1, = st.tabs(
            [
                "Locations",
            ]
        )

        with tab1:
            await locations_section(data_client)
    finally:
        await channel.close()


# Required for the tests to run this as a script
if __name__ == "__main__":
    dataplatform_toolbox_page()
