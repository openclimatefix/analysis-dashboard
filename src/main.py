""" 
UK analysis dashboard for OCF 
"""

import os
import streamlit as st
import pandas as pd
import numpy as np

from datetime import datetime, timedelta

from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.metric import MetricValue
from get_data import get_metric_value
from auth import check_password
from plots.all_gsps import make_all_gsps_plots
from plots.forecast_horizon import make_mae_by_forecast_horizon, make_mae_forecast_horizon_group_by_forecast_horizon, \
    make_mae_vs_froecast_horizon_group_by_date
from plots.mae_and_rmse import make_rmse_and_mae_plot, make_mae_plot
from status import status_page
from forecast import forecast_page
from pvsite_forecast import pvsite_forecast_page
from sites_toolbox import sites_toolbox_page

from plots.pinball_and_exceedance_plots import make_pinball_or_exceedance_plot
from tables.raw import make_raw_table
from tables.summary import make_recent_summary_stats

st.get_option("theme.primaryColor")

MAE_LIMIT_DEFAULT = 800
MAE_LIMIT_DEFAULT_HORIZON_0 = 300


def get_x_y(metric_values):
    """
    Extra x and y values from the metric values

    x is the time
    y is the metric value
    """
    metric_values = [MetricValue.from_orm(value) for value in metric_values]
    # select data to show in the chart MAE and RMSE and date from the above date range
    x = [value.datetime_interval.start_datetime_utc for value in metric_values]
    y = [round(float(value.value), 2) for value in metric_values]

    return x, y


def metric_page():

    # set up title and subheader
    st.markdown(
        f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>', unsafe_allow_html=True
    )
    # set up sidebar
    st.sidebar.subheader("Select date range for charts")
    # select start and end date
    starttime = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=30))
    endtime = st.sidebar.date_input("End Date", datetime.today())

    use_adjuster = st.sidebar.radio("Use adjuster", [True, False], index=1)

    st.sidebar.subheader("Select Forecast Model")
    model_name = st.sidebar.selectbox("Select", ["cnn", "National_xg", "pvnet_v2"])

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
    make_recent_summary_stats(values=y_rmse)

    st.sidebar.subheader("Select Forecast Horizon")
    forecast_horizon_selection = st.sidebar.multiselect(
        "Select",
        [0, 60, 120, 180, 240, 300, 360, 420, 8*60, 12*60, 15*60, 18*60, 21*60, 24*60, 30*60, 35*60],
        [60, 120, 240, 420]
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
 
    # set up title and subheader
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

    fig2 = make_mae_by_forecast_horizon(df_mae, forecast_horizon_selection, metric_values_by_forecast_horizon)
    with st.expander("MAE by Forecast Horizon"):
        st.plotly_chart(fig2, theme="streamlit")

    fig4 = make_mae_forecast_horizon_group_by_forecast_horizon(forecast_horizon_selection,
                                                               metric_values_by_forecast_horizon)

    with st.expander("MAE by Forecast Horizon by Date"):
        fig4.update_layout(xaxis_range=[0, MAE_LIMIT_DEFAULT])
        st.plotly_chart(fig4, theme="streamlit")

    all_forecast_horizons_df, fig5 = make_mae_vs_froecast_horizon_group_by_date(forecast_horizon_selection,
                                                                                metric_values_by_forecast_horizon)

    with st.expander("MAE Forecast Horizon Values by Date"):
        st.plotly_chart(fig5, theme="streamlit")

    # comparing MAE and RMSE
    fig6 = make_rmse_and_mae_plot(df_mae, df_rmse, x_plive_mae, x_plive_rmse, y_plive_mae, y_plive_rmse)

    fig6.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT])
    with st.expander("Quartz Solar and PVlive MAE with RMSE"):
        st.plotly_chart(fig6, theme="streamlit")
        st.write("PVLive is the difference between the intraday and day after PVLive values.")

    fig7 = make_all_gsps_plots(x_mae_all_gsp, y_mae_all_gsp)

    if model_name in ["pvnet_v2", "cnn"]:
        with st.expander("MAE All GSPs"):
            st.plotly_chart(fig7, theme="streamlit")

    if model_name in ["pvnet_v2", "National_xg"]:
        with connection.get_session() as session:
            with st.expander("Pinball loss"):
                fig8 = make_pinball_or_exceedance_plot(
                    session=session,
                    model_name=model_name,
                    starttime=starttime,
                    endtime=endtime,
                    forecast_horizon_selection=forecast_horizon_selection,
                    metric_name="Pinball loss",
                )
                st.plotly_chart(fig8, theme="streamlit")
            with st.expander("Exccedance"):
                fig9 = make_pinball_or_exceedance_plot(
                    session=session,
                    model_name=model_name,
                    starttime=starttime,
                    endtime=endtime,
                    forecast_horizon_selection=forecast_horizon_selection,
                    metric_name="Exceedance",
                )
                st.plotly_chart(fig9, theme="streamlit")

    st.subheader("Data - forecast horizon averaged")
    # get average MAE for each forecast horizon
    df_mae_horizon_mean = all_forecast_horizons_df.groupby(["forecast_horizon"]).mean().reset_index()
    df_mae_horizon_mean.rename(columns={"MAE": "mean"}, inplace=True)
    df_mae_horizon_std = all_forecast_horizons_df.groupby(["forecast_horizon"]).std().reset_index()
    df_mae_horizon_mean['std'] = df_mae_horizon_std['MAE']
    pv_live_mae = np.round(np.mean(y_plive_mae),2)
    st.write(f"PV LIVE Mae {pv_live_mae} MW (intraday - day after)")
    st.write(df_mae_horizon_mean)

    make_raw_table(df_mae, df_rmse)


if check_password():
    page_names_to_funcs = {
        "Metrics": metric_page,
        "Status": status_page,
        "Forecast": forecast_page,
        "PV Site Forecast": pvsite_forecast_page,
        "Sites Toolbox": sites_toolbox_page,
    }

    demo_name = st.sidebar.selectbox("Choose a page", page_names_to_funcs.keys())
    page_names_to_funcs[demo_name]()
