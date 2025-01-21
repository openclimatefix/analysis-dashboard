""" 
India Analysis dashboard for OCF
"""

import os

import streamlit as st

from auth import check_password
from nwp_page import nwp_page
from pvsite_forecast import pvsite_forecast_page
from sites_toolbox import sites_toolbox_page
from satellite_page import satellite_page
from status import status_page
from users import user_page
from weather_forecast import weather_forecast_page
from mlmodel import mlmodel_page
from weather_graph import weather_graph_page

st.get_option("theme.primaryColor")
st.set_page_config(layout="wide", page_title="OCF Dashboard")

if check_password():

    page_names_to_funcs = {
        "Status": status_page,
        "Location Forecast": pvsite_forecast_page,
        "ML Models": mlmodel_page,
        "Sites Toolbox": sites_toolbox_page,
        "API Users": user_page,
        "NWP": nwp_page,
        "Satellite": satellite_page,
        "Weather Forecast": weather_forecast_page, 
        "Weather Data" : weather_graph_page,
    }

    demo_name = st.sidebar.selectbox("Choose a page", page_names_to_funcs.keys(), 1)
    page_names_to_funcs[demo_name]()
