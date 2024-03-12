""" 
India Analysis dashboard for OCF
"""

import os

import streamlit as st

from auth import check_password
from nwp_page import nwp_page
from pvsite_forecast import pvsite_forecast_page
from sites_toolbox import sites_toolbox_page
from status import status_page

st.get_option("theme.primaryColor")
st.set_page_config(layout="centered", page_title="OCF Dashboard")

if check_password():

    page_names_to_funcs = {
        "Status": status_page,
        "Location Forecast": pvsite_forecast_page,
        "Sites Toolbox": sites_toolbox_page,
        "NWP": nwp_page,
    }

    demo_name = st.sidebar.selectbox("Choose a page", page_names_to_funcs.keys(), 1)
    page_names_to_funcs[demo_name]()
