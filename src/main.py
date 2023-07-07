""" 
UK analysis dashboard for OCF 
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime, timedelta

from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.metric import MetricValue
from get_data import get_metric_value
from auth import check_password
from status import status_page
from forecast import forecast_page

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


def get_recent_daily_values(values):
    """
    Get the recent daily values from the metric values
    """
    if len(values) == 0:
        day_before_yesterday = None
        yesterday = None
        today = None
    elif len(values) == 1:
        day_before_yesterday = None
        yesterday = None
        today = values[len(values) - 1]
    elif len(values) == 2:
        day_before_yesterday = None
        yesterday = values[len(values) - 2]
        today = values[len(values) - 1]
    else:
        day_before_yesterday = values[len(values) - 3]
        yesterday = values[len(values) - 2]
        today = values[len(values) - 1]

    return day_before_yesterday, yesterday, today


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

        # transform SQL object into something readable
        x_mae_all_gsp, y_mae_all_gsp = get_x_y(metric_values=metric_values_mae_gsp_sum)
        x_mae, y_mae = get_x_y(metric_values=metric_values_mae)
        x_rmse, y_rmse = get_x_y(metric_values=metric_values_rmse)


        # getting recent statistics for the dashboard
        day_before_yesterday_mae, yesterday_mae, today_mae = get_recent_daily_values(values=y_mae)
        day_before_yesterday_rmse, yesterday_rmse, today_rmse = get_recent_daily_values(
            values=y_rmse
        )

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Metrics"}</h1>',
        unsafe_allow_html=True,
    )

    with st.expander("Recent MAE Values"):
        st.subheader("Recent MAE")
        t = datetime.today() - timedelta(days=1)
        t2 = datetime.today() - timedelta(days=2)
        t3 = datetime.today() - timedelta(days=3)
        col1, col2, col3 = st.columns([1, 1, 1])

        col1.metric(label=t3.strftime("%d/%m/%y"), value=day_before_yesterday_mae)
        col2.metric(label=t2.strftime("%d/%m/%y"), value=yesterday_mae)
        col3.metric(label=t.strftime("%d/%m/%y"), value=today_mae)

    with st.expander("Recent RMSE Values"):
        st.subheader("Recent RMSE")
        col1, col2, col3 = st.columns([1, 1, 1])
        col1.metric(label=t3.strftime("%d/%m/%y"), value=day_before_yesterday_rmse)
        col2.metric(label=t2.strftime("%d/%m/%y"), value=yesterday_rmse)
        col3.metric(label=t.strftime("%d/%m/%y"), value=today_rmse)

    st.sidebar.subheader("Select Forecast Horizon")
    forecast_horizon_selection = st.sidebar.multiselect(
        "Select", [0, 60, 120, 180, 240, 300, 360, 420], [60, 120, 240, 420]
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

    df_mae_all_gsp = pd.DataFrame(
        {
            "MAE All GSPs": y_mae_all_gsp,
            "datetime_utc": x_mae_all_gsp,
        })
 
    # set up title and subheader
    fig = px.bar(
        df_mae,
        x="datetime_utc",
        y="MAE",
        title="Quartz Solar MAE",
        hover_data=["MAE", "datetime_utc"],
        color_discrete_sequence=["#FFAC5F"],
    )

    fig.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT_HORIZON_0])
    st.plotly_chart(fig, theme="streamlit")

    line_color = [
        "#9EC8FA",
        "#9AA1F9",
        "#FFAC5F",
        "#9F973A",
        "#7BCDF3",
        "#086788",
        "#63BCAF",
        "#4C9A8E",
    ]

    # MAE by forecast horizon adding go.Figure
    fig2 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Quartz Solar MAE by Forecast Horizon (selected in sidebar)"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="MAE (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    fig2.add_trace(
        go.Scatter(
            x=df_mae["datetime_utc"],
            y=df_mae["MAE"],
            mode="lines",
            name="Daily Total MAE",
            line=dict(color="#FFD053"),
        )
    )

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

    for forecast_horizon in forecast_horizon_selection:
        metric_values = metric_values_by_forecast_horizon[forecast_horizon]
        x_mae_horizon, y_mae_horizon = get_x_y(metric_values=metric_values)

        df = pd.DataFrame(
            {
                "MAE": y_mae_horizon,
                "datetime_utc": x_mae_horizon,
            }
        )

        fig2.add_traces(
            [
                go.Scatter(
                    x=df["datetime_utc"],
                    y=df["MAE"],
                    name=f"{forecast_horizon}-minute horizon",
                    mode="lines",
                    line=dict(color=line_color[forecast_horizon_selection.index(forecast_horizon)]),
                )
            ]
        )

    fig2.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT])
    st.plotly_chart(fig2, theme="streamlit")
   
    fig4 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(
                text="Quartz Solar MAE by Forecast Horizon for Date Range(selected in sidebar)"
            ),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="MAE (MW)")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Forecast Horizon (minutes)")),
        )
    )

    for forecast_horizon in forecast_horizon_selection:
        metric_values = metric_values_by_forecast_horizon[forecast_horizon]
        x_mae_horizon = [value.datetime_interval.start_datetime_utc for value in metric_values]
        y_mae_horizon = [round(float(value.value), 2) for value in metric_values]

        df_mae_horizon = pd.DataFrame(
            {
                "MAE": y_mae_horizon,
                "datetime_utc": x_mae_horizon,
                "forecast_horizon": forecast_horizon,
            }
        )

        fig4.add_traces(
            [
                go.Scatter(
                    x=df_mae_horizon["MAE"],
                    y=df_mae_horizon["forecast_horizon"],
                    name=f"{forecast_horizon}-minute horizon",
                    mode="markers",
                    line=dict(color=line_color[forecast_horizon_selection.index(forecast_horizon)]),
                ),
            ]
        )
        fig4.update_layout(
            xaxis=dict(tickmode="linear", tick0=0, dtick=50),
            yaxis=dict(tickmode="linear", tick0=0, dtick=60),
        )

    fig4.update_layout(xaxis_range=[0, MAE_LIMIT_DEFAULT])
    st.plotly_chart(fig4, theme="streamlit")

    # add chart with forecast horizons on x-axis and line for each day in the date range
    fig5 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Quartz Solar MAE Forecast Horizon Values by Date"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Forecast Horizon (minutes)")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="MAE (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Date")),
        )
    )
    # make an empty array to capture data for each line
    traces = []
    # make an empty array to capture values for each forecast horizon in the date range
    dfs = []
    # get data for each forecast horizon
    # read database metric values
    for forecast_horizon in forecast_horizon_selection:
        metric_values = metric_values_by_forecast_horizon[forecast_horizon]
        dates = [value.datetime_interval.start_datetime_utc for value in metric_values]
        mae_value = [round(float(value.value), 2) for value in metric_values]
        forecast_horizons = [value.forecast_horizon_minutes for value in metric_values]

        # create dataframe for each date with a value for each forecast horizon
        data = pd.DataFrame(
            {
                "MAE": mae_value,
                "datetime_utc": dates,
                "forecast_horizon": forecast_horizons,
            }
        )

        dfs.append(data)

    # merge dataframes
    all_forecast_horizons_df = pd.concat(dfs, axis=0).sort_values(by=["datetime_utc"], ascending=True)
    # group by date
    result = {result_.index[0]: result_ for _, result_ in all_forecast_horizons_df.groupby("datetime_utc")}
    # loop through each date group in the dictionary and add to traces
    len_colours = len(line_color)
    # loop through each date group in the dictionary and add to traces
    for i in result:
        # sort results by day
        results_for_day = result[i]
        results_for_day = results_for_day.sort_values(by=["forecast_horizon"], ascending=True)
        traces.append(
            go.Scatter(
                x=results_for_day["forecast_horizon"].sort_values(ascending=True),
                y=results_for_day["MAE"],
                name=results_for_day["datetime_utc"].iloc[0].strftime("%Y-%m-%d"),
                mode="lines+markers",
                line=dict(color=line_color[i % len_colours]),
            )
        )

    fig5.add_traces(traces)

    fig5.update_layout(
        xaxis=dict(tickmode="linear", tick0=0, dtick=60),
        yaxis=dict(tickmode="linear", tick0=0, dtick=50),
    )
    fig5.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT])
    st.plotly_chart(fig5, theme="streamlit")

    # comparing MAE and RMSE
    fig6 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Quartz Solar MAE with RMSE for Comparison"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Error Value (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    fig6.add_traces(
        [
            go.Scatter(
                x=df_mae["datetime_utc"],
                y=df_mae["MAE"],
                name="MAE",
                mode="lines",
                line=dict(color="#FFD053"),
            ),
            go.Scatter(
                x=df_rmse["datetime_utc"],
                y=df_rmse["RMSE"],
                name="RMSE",
                mode="lines",
                line=dict(color=line_color[0]),
            ),
        ]
    )
    
    fig6.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT])
    st.plotly_chart(fig6, theme="streamlit")

    fig7 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Daily Latest MAE All GSPs"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Error Value (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    fig7.add_traces(
        go.Scatter(
                x=df_mae_all_gsp["datetime_utc"],
                y=df_mae_all_gsp["MAE All GSPs"],
                mode="lines",
                name="Daily Latest MAE All GSPs",
                line=dict(color=line_color[4]),
            ),
    )
    
    st.plotly_chart(fig7, theme="streamlit")

    st.subheader("Data - forecast horizon averaged")
    # get average MAE for each forecast horizon
    df_mae_horizon_mean = all_forecast_horizons_df.groupby(["forecast_horizon"]).mean().reset_index()
    df_mae_horizon_mean.rename(columns={"MAE": "mean"}, inplace=True)
    df_mae_horizon_std = all_forecast_horizons_df.groupby(["forecast_horizon"]).std().reset_index()
    df_mae_horizon_mean['std'] = df_mae_horizon_std['MAE']
    st.write(df_mae_horizon_mean)


    st.subheader("Raw Data")
    col1, col2 = st.columns([1, 1])
    col1.write(df_mae)
    col2.write(df_rmse)


if check_password():
    page_names_to_funcs = {
        "Metrics": metric_page,
        "Status": status_page,
        "Forecast": forecast_page,
    }

    demo_name = st.sidebar.selectbox("Choose a page", page_names_to_funcs.keys())
    page_names_to_funcs[demo_name]()
