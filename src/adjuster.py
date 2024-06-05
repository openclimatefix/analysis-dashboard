""" This page shows the current adjuster values """
import os
import pandas as pd

import plotly.graph_objects as go

from nowcasting_datamodel.read.read_metric import read_latest_me_national
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models import MetricValueSQL, MetricSQL, MLModelSQL
import streamlit as st


def adjuster_page():
    """Main page for status"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Adjuster"}</h1>',
        unsafe_allow_html=True,
    )

    connection = DatabaseConnection(url=os.environ["DB_URL"], echo=True)
    with connection.get_session() as session:
        # get all the models with adjust values
        model_names = get_model_names_with_adjuster_values(session)

        # Add dropdown to select GSP region
        model_name = st.sidebar.selectbox("Select a models", model_names, index=0)

        # get adjust values
        metric_values = read_latest_me_national(
            session=session,
            model_name=model_name,
        )

        # format
        metric_values = [
            [metric_value.value, metric_value.time_of_day, metric_value.forecast_horizon_minutes]
            for metric_value in metric_values
        ]

    metric_values_df = pd.DataFrame(
        columns=["value", "time_of_day", "forecast_horizon_minutes"], data=metric_values
    )

    # pivot to make in 2d data ofr time_of_day vs forecast_horizon_minutes
    metric_values_df = metric_values_df.pivot(
        index="time_of_day", columns="forecast_horizon_minutes", values="value"
    )

    fig = go.Figure(
        data=go.Heatmap(
            z=metric_values_df.values, x=metric_values_df.columns, y=metric_values_df.index
        ),
        layout=go.Layout(
            title=go.layout.Title(text=f"Adjuster Value for {model_name}"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Forecast Horizon [minutes]")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Time of day")),
        ),
    )

    # add
    st.plotly_chart(fig, theme="streamlit")


def get_model_names_with_adjuster_values(session, metric_name: str = "Half Hourly ME"):
    """Get model name with adjuster values"""
    # start main query
    query = session.query(MetricValueSQL)
    query = query.join(MetricSQL)
    query = query.join(MLModelSQL)
    query = query.distinct(MLModelSQL.name)
    # filter on metric name
    query = query.filter(MetricSQL.name == metric_name)
    # get all results
    metric_values = query.all()
    model_names = [metric_value.model.name for metric_value in metric_values]
    return model_names
