"""This module contains the data platform toolbox for the OCF dashboard"""
import streamlit as st
from dataplatform.toolbox.organisation import organisation_section
from dataplatform.toolbox.users import users_section
from dataplatform.toolbox.user_organisation import user_organisation_section
from dataplatform.toolbox.location import locations_section
from dataplatform.toolbox.policy import policies_section

# Color scheme (matching existing toolbox)
# teal:  #63BCAF (Get operations)
# blue: #7bcdf3 (Create operations)  
# yellow: #ffd053 (Update operations)
# red: #E63946 (Delete operations)
# orange: #FF9736 (Info sections)


def dataplatform_toolbox_page():
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
        organisation_section()
    
    with tab2:
        users_section()
    
    with tab3:
        user_organisation_section()
    
    with tab4:
        locations_section()
    
    with tab5:
        policies_section()

dataplatform_toolbox_page()
