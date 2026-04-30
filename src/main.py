""" 
UK analysis dashboard for OCF 
"""

import streamlit as st

from auth import check_password
from dataplatform.forecast.main import dp_forecast_page
from pvsite_forecast import pvsite_forecast_page
from sites_toolbox import sites_toolbox_page
from status import status_page
from users import user_page
from nwp_page import nwp_page
from satellite_page import satellite_page
from cloudcasting_page import cloudcasting_page
from batch_page import batch_page
from dataplatform.toolbox.main import dataplatform_toolbox_page

st.get_option("theme.primaryColor")
st.set_page_config(layout="wide", page_title="OCF Dashboard")


def main_page():
    st.text('This is the Analysis Dashboard UK. Please select the page you want from the menu at the top of this page')


if check_password():
    pg = st.navigation({
        "Home": [
            st.Page(main_page, title="🏠 Home", default=True),
            st.Page(status_page, title="Status"),
            st.Page(user_page, title="API Users"),
        ],
        "Data Platform": [
            st.Page(dp_forecast_page, title="Data Platform Forecast"),
            st.Page(dataplatform_toolbox_page, title="Data Platform Toolbox"),
        ],
        "Sites": [
            st.Page(pvsite_forecast_page, title="Site Forecast"),
            st.Page(sites_toolbox_page, title="Sites Toolbox"),
        ],
        "Input Data": [
            st.Page(nwp_page, title="NWP"),
            st.Page(satellite_page, title="Satellite"),
            st.Page(batch_page, title="Batch Visualisation Page"),
        ],
        "Cloudcasting": [
            st.Page(cloudcasting_page, title="Cloudcasting"),
        ],
        "Legacy": [
            st.Page(metric_page, title="Legacy Metrics"),
            st.Page(forecast_page, title="Legacy Forecast"),
            st.Page(adjuster_page, title="Legacy Adjuster"),
        ]},
        position="top",
    )
    pg.run()
