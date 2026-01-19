"""
UK analysis dashboard for OCF
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from importlib.metadata import version, PackageNotFoundError
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.metric import MetricValue

from auth import check_password
from dataplatform.forecast.main import dp_forecast_page
from forecast import forecast_page
from get_data import get_metric_value
from plots.all_gsps import make_all_gsps_plots
from plots.forecast_horizon import (
    make_mae_by_forecast_horizon,
    make_mae_forecast_horizon_group_by_forecast_horizon,
    make_mae_vs_forecast_horizon_group_by_date,
)
from plots.mae_and_rmse import make_rmse_and_mae_plot, make_mae_plot
from plots.pinball_and_exceedance_plots import make_pinball_or_exceedance_plot
from plots.ramp_rate import make_ramp_rate_plot
from plots.utils import (
    get_x_y,
    get_recent_available_model_names,
    model_is_probabilistic,
    model_is_gsp_regional,
)
from pvsite_forecast import pvsite_forecast_page
from sites_toolbox import sites_toolbox_page
from status import status_page
from tables.raw import make_raw_table
from tables.summary import make_recent_summary_stats, make_forecast_horizon_table
from users import user_page
from nwp_page import nwp_page
from satellite_page import satellite_page
from cloudcasting_page import cloudcasting_page
from adjuster import adjuster_page
from batch_page import batch_page

# Restore original Streamlit config (as requested by reviewer)
st.get_option("theme.primaryColor")
st.set_page_config(layout="wide", page_title="OCF Dashboard")


def metric_page():
    # Sidebar controls
    st.sidebar.subheader("Select date range for charts")
    starttime = st.sidebar.date_input(
        "Start Date", datetime.today() - timedelta(days=30)
    )
    endtime = st.sidebar.date_input("End Date", datetime.today())

    use_adjuster = st.sidebar.radio("Use adjuster", [True, False], index=1)

    st.sidebar.subheader("Select Forecast Model")

    connection = DatabaseConnection(url=os.environ["DB_URL"], echo=True)
    with connection.get_session() as session:
        models = get_recent_available_model_names(session)

    model_name = st.sidebar.selectbox(
        "Select model", models, index=models.index("pvnet_v2")
    )

    with connection.get_session() as session:
        name_mae = "Daily Latest MAE"
        name_rmse = "Daily Latest RMSE"
        name_mae_gsp_sum = "Daily Latest MAE All GSPs"

        if use_adjuster:
            name_mae = "Daily Latest MAE with adjuster"
            name_rmse = "Daily Latest RMSE with adjuster"

        metric_values_mae = get_metric_value(
            session,
            name=name_mae,
            gsp_id=0,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
            model_name=model_name,
        )
        metric_values_rmse = get_metric_value(
            session,
            name=name_rmse,
            gsp_id=0,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
            model_name=model_name,
        )
        metric_values_mae_gsp_sum = get_metric_value(
            session,
            name=name_mae_gsp_sum,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
            model_name=model_name,
        )

        x_mae, y_mae = get_x_y(metric_values_mae)
        x_rmse, y_rmse = get_x_y(metric_values_rmse)
        x_mae_all_gsp, y_mae_all_gsp = get_x_y(metric_values_mae_gsp_sum)

    st.markdown(
        '<h1 style="color:#63BCAF;font-size:48px;">Metrics</h1>',
        unsafe_allow_html=True,
    )

    make_recent_summary_stats(values=y_mae)
    make_recent_summary_stats(values=y_rmse, title="Recent RMSE")

    fig = make_mae_plot(
        pd.DataFrame({"MAE": y_mae, "datetime_utc": x_mae})
    )
    st.plotly_chart(fig, theme="streamlit")

    fig2 = make_all_gsps_plots(x_mae_all_gsp, y_mae_all_gsp)
    if model_is_gsp_regional(model_name):
        with st.expander("MAE All GSPs"):
            st.plotly_chart(fig2, theme="streamlit")


def main_page():
    try:
        app_version = version("analysis-dashboard")
    except PackageNotFoundError:
        app_version = "unknown"

    st.markdown("## OCF Dashboard")
    st.text(
        f"This is the Analysis Dashboard UK v{app_version}. "
        "Please select the page you want from the menu at the top of this page"
    )


if check_password():
    pg = st.navigation(
        [
            st.Page(main_page, title="🏠 Home", default=True),
            st.Page(metric_page, title="🔢 Metrics"),
            st.Page(status_page, title="🚦 Status"),
            st.Page(forecast_page, title="📈 Forecast"),
            st.Page(pvsite_forecast_page, title="📉 Site Forecast"),
            st.Page(dp_forecast_page, title="📉 DP Forecast"),
            st.Page(sites_toolbox_page, title="🛠️ Sites Toolbox"),
            st.Page(user_page, title="👥 API Users"),
            st.Page(nwp_page, title="🌤️ NWP"),
            st.Page(satellite_page, title="🛰️ Satellite"),
            st.Page(cloudcasting_page, title="☁️ Cloudcasting"),
            st.Page(adjuster_page, title="🔧 Adjuster"),
            st.Page(batch_page, title="👀 Batch Visualisation Page"),
        ],
        position="top",
    )
    pg.run()
