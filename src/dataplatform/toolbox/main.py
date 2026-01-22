"""Data Platform Toolbox Streamlit Page Main Code."""
import asyncio
from grpclib.client import Channel
import streamlit as st
from dataplatform.toolbox.organisation import organisation_section
from dataplatform.toolbox.users import users_section
from dataplatform.toolbox.user_organisation import user_organisation_section
from dataplatform.toolbox.location import locations_section
from dataplatform.toolbox.policy import policies_section
from dp_sdk.ocf import dp
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
    async with Channel(host=host, port=int(port)) as channel:
        admin_client = dp.DataPlatformAdministrationServiceStub(channel)
        data_client = dp.DataPlatformDataServiceStub(channel)

        st.markdown(
            '<h1 style="color:#63BCAF;font-size:48px;">Data Platform Toolbox</h1>',
            unsafe_allow_html=True,
        )

        # Create tabs for different sections
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏢 Organisations", 
            "👤 Users", 
            "🔗 User + Organisation",
            "📍 Locations",
            "📋 Policies"
        ])

        with tab1:
            await organisation_section(admin_client)

        with tab2:
            await users_section(admin_client)
        
        with tab3:
            await user_organisation_section(admin_client)
        
        with tab4:
            await locations_section(data_client)
        
        with tab5:
            await policies_section(admin_client, data_client)

# Required for the tests to run this as a script
if __name__ == "__main__":
    dataplatform_toolbox_page()
