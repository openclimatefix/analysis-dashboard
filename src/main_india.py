""" 
India Analysis dashboard for OCF
"""

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
from batch_page import batch_page

import tomllib

try:
    with open("pyproject.toml", "rb") as f:
        pyproject_data = tomllib.load(f)
    __version__ = pyproject_data["project"]["version"]
except (FileNotFoundError, KeyError):
    __version__ = "v?"

st.get_option("theme.primaryColor")
st.set_page_config(layout="wide", page_title="OCF Dashboard")

def main_page():
    st.text(f'This is the Analysis Dashboard India v{__version__}. Please select the page you want on the left hand side')


if check_password():
    pg = st.navigation([
        st.Page(main_page, title="🏠 Home", default=True),
        st.Page(status_page, title="🚦 Status"),
        st.Page(pvsite_forecast_page, title="📉 Site Forecast"),
        st.Page(mlmodel_page, title="🤖 ML Models"),
        st.Page(sites_toolbox_page, title="🛠️ Sites Toolbox"),
        st.Page(user_page, title="👥 API Users"),
        st.Page(nwp_page, title="🌤️ NWP"),
        st.Page(satellite_page, title="🛰️ Satellite"),
        st.Page(weather_forecast_page, title="🌦️ Weather Forecast"),
        st.Page(weather_graph_page, title="🌨️ Weather Data"),
        st.Page(batch_page, title="👀 Batch Visualisation Page"),
    ], position="top")
    pg.run()

