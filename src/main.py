""" 
UK analysis dashboard for OCF 
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.metric import MetricValue

from auth import check_password
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
from plots.utils import get_x_y
from pvsite_forecast import pvsite_forecast_page
from sites_toolbox import sites_toolbox_page
from status import status_page
from tables.raw import make_raw_table
from tables.summary import make_recent_summary_stats, make_forecast_horizon_table
from users import user_page
from nwp_page import nwp_page

st.get_option("theme.primaryColor")
st.set_page_config(layout="wide", page_title="OCF Dashboard")

show_pvnet_gsp_sum = os.getenv("SHOW_PVNET_GSP_SUM", "False").lower() == "true"

def metric_page():
    # set up title and subheader
    # set up sidebar
    st.sidebar.subheader("Select date range for charts")
    # select start and end date
    starttime = st.sidebar.date_input(
        "Start Date", datetime.today() - timedelta(days=30)
    )
    endtime = st.sidebar.date_input("End Date", datetime.today())

    use_adjuster = st.sidebar.radio("Use adjuster", [True, False], index=1)

    st.sidebar.subheader("Select Forecast Model")
    models = ["cnn", "National_xg", "pvnet_v2"]
    if show_pvnet_gsp_sum:
        models.append("pvnet_gsp_sum")
    model_name = st.sidebar.selectbox("Select", models, 2)

    # set up database connection
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)

    # get metrics for comparing MAE and RMSE without forecast horizon

    with connection.get_session() as session:
        # read database metric values
        name_mae = "Daily Latest MAE"
        name_rmse = "Daily Latest RMSE"
        name_mae_gsp_sum = "Daily Latest MAE All GSPs"
        if use_adjuster:
            name_mae = "Daily Latest MAE with adjuster"
            name_rmse = "Daily Latest RMSE with adjuster"
            name_mae_gsp_sum = "Daily Latest MAE All GSPs"

        name_pvlive_mae = "PVLive MAE"
        name_pvlive_rmse = "PVLive RMSE"

        metric_values_mae = get_metric_value(
            session=session,
            name=name_mae,
            gsp_id=0,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
            model_name=model_name,
        )

        metric_values_rmse = get_metric_value(
            session=session,
            name=name_rmse,
            gsp_id=0,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
            model_name=model_name,
        )
        # get metric value for mae with pvlive gsp sum truths for comparison
        metric_values_mae_gsp_sum = get_metric_value(
            session=session,
            name=name_mae_gsp_sum,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
            model_name=model_name,
        )

        # pvlive
        metric_values_pvlive_mae = get_metric_value(
            session=session,
            name=name_pvlive_mae,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
            gsp_id=0,
        )
        metric_values_pvlive_rmse = get_metric_value(
            session=session,
            name=name_pvlive_rmse,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime,
            gsp_id=0,
        )

        # transform SQL object into something readable
        x_mae_all_gsp, y_mae_all_gsp = get_x_y(metric_values=metric_values_mae_gsp_sum)
        x_mae, y_mae = get_x_y(metric_values=metric_values_mae)
        x_rmse, y_rmse = get_x_y(metric_values=metric_values_rmse)
        x_plive_mae, y_plive_mae = get_x_y(metric_values=metric_values_pvlive_mae)
        x_plive_rmse, y_plive_rmse = get_x_y(metric_values=metric_values_pvlive_rmse)

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Metrics"}</h1>',
        unsafe_allow_html=True,
    )

    make_recent_summary_stats(values=y_mae)
    make_recent_summary_stats(values=y_rmse, title="Recent RMSE")

    st.sidebar.subheader("Select Forecast Horizon")
    forecast_horizon_selection = st.sidebar.multiselect(
        "Select",
        [
            0,
            60,
            90,
            120,
            150,
            180,
            240,
            300,
            360,
            420,
            8 * 60,
            12 * 60,
            15 * 60,
            18 * 60,
            21 * 60,
            24 * 60,
            30 * 60,
            35 * 60,
        ],
        [60, 120, 240, 420],
    )

    df_mae = pd.DataFrame(
        {
            "MAE": y_mae,
            "datetime_utc": x_mae,
        }
    )

    df_rmse = pd.DataFrame(
        {
            "RMSE": y_rmse,
            "datetime_utc": x_rmse,
        }
    )

    # Make MAE plot
    fig = make_mae_plot(df_mae)
    st.plotly_chart(fig, theme="streamlit")

    # get metrics per forecast horizon
    metric_values_by_forecast_horizon = {}
    with connection.get_session() as session:
        # read database metric values
        for forecast_horizon in forecast_horizon_selection:
            metric_values = get_metric_value(
                session=session,
                name=name_mae,
                gsp_id=0,
                forecast_horizon_minutes=forecast_horizon,
                start_datetime_utc=starttime,
                end_datetime_utc=endtime,
                model_name=model_name,
            )
            metric_values = [MetricValue.from_orm(value) for value in metric_values]
            metric_values_by_forecast_horizon[forecast_horizon] = metric_values

    fig2 = make_mae_by_forecast_horizon(
        df_mae, forecast_horizon_selection, metric_values_by_forecast_horizon
    )
    with st.expander("MAE by Forecast Horizon"):
        st.plotly_chart(fig2, theme="streamlit")

    fig3 = make_mae_forecast_horizon_group_by_forecast_horizon(
        forecast_horizon_selection, metric_values_by_forecast_horizon
    )

    with st.expander("MAE by Forecast Horizon by Date"):
        st.plotly_chart(fig3, theme="streamlit")

    all_forecast_horizons_df, fig4 = make_mae_vs_forecast_horizon_group_by_date(
        forecast_horizon_selection, metric_values_by_forecast_horizon
    )

    with st.expander("MAE Forecast Horizon Values by Date"):
        st.plotly_chart(fig4, theme="streamlit")

    # comparing MAE and RMSE
    fig5 = make_rmse_and_mae_plot(
        df_mae, df_rmse, x_plive_mae, x_plive_rmse, y_plive_mae, y_plive_rmse
    )

    with st.expander("Quartz Solar and PVlive MAE with RMSE"):
        st.plotly_chart(fig5, theme="streamlit")
        st.write(
            "PVLive is the difference between the intraday and day after PVLive values."
        )

    fig6 = make_all_gsps_plots(x_mae_all_gsp, y_mae_all_gsp)

    if model_name in ["pvnet_v2", "cnn"]:
        with st.expander("MAE All GSPs"):
            st.plotly_chart(fig6, theme="streamlit")

    fig7 = make_ramp_rate_plot(session=session, model_name=model_name, starttime=starttime, endtime=endtime)
    with st.expander("Ramp Rate"):
        st.plotly_chart(fig7, theme="streamlit")

    if model_name in ["pvnet_v2", "National_xg"]:
        with connection.get_session() as session:
            with st.expander("Pinball loss"):
                fig7 = make_pinball_or_exceedance_plot(
                    session=session,
                    model_name=model_name,
                    starttime=starttime,
                    endtime=endtime,
                    forecast_horizon_selection=forecast_horizon_selection,
                    metric_name="Pinball loss",
                )
                st.plotly_chart(fig7, theme="streamlit")
            with st.expander("Exceedance"):
                fig8 = make_pinball_or_exceedance_plot(
                    session=session,
                    model_name=model_name,
                    starttime=starttime,
                    endtime=endtime,
                    forecast_horizon_selection=forecast_horizon_selection,
                    metric_name="Exceedance",
                )
                st.plotly_chart(fig8, theme="streamlit")

    make_forecast_horizon_table(all_forecast_horizons_df, y_plive_mae)

    make_raw_table(df_mae, df_rmse)


if check_password():

    page_names_to_funcs = {
        "Metrics": metric_page,
        "Status": status_page,
        "Forecast": forecast_page,
        "PV Site Forecast": pvsite_forecast_page,
        "Sites Toolbox": sites_toolbox_page,
        "API Users": user_page,
        "NWP": nwp_page
    }

    demo_name = st.sidebar.selectbox("Choose a page", page_names_to_funcs.keys())
    page_names_to_funcs[demo_name]()
