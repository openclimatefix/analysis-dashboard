from datetime import datetime, timedelta, time, timezone
import streamlit as st
import os
from pvsite_datamodel.connection import DatabaseConnection
from pvsite_datamodel.read import (
    get_all_sites,
    get_pv_generation_by_sites,
    get_latest_forecast_values_by_site
)

import plotly.graph_objects as go


def pvsite_forecast_page():
    """Main page for pvsite forecast"""
    st.markdown(
        f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Analysis Dashboard"}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"PV Site Forecast"}</h1>',
        unsafe_allow_html=True,
    )
    # get site_uuids from database
    url = "postgresql://main:7o5geKryjWVnVVfu@localhost:5434/pvsitedevelopment"
    # url = os.environ["SITES_DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:
        site_uuids = get_all_sites(session=session)
        site_uuids = [
            sites.site_uuid for sites in site_uuids if sites.site_uuid is not None
        ]
      
    site_selection = st.sidebar.selectbox("Select sites by site_uuid", site_uuids,)
    starttime = st.sidebar.date_input("Start Date", datetime.today() - timedelta(days=3), max_value=datetime.today())
    st.write("Forecast for", site_selection, "starting on", starttime)

    # get forecast values for selected sites and plot
    with connection.get_session() as session:
        forecasts = get_latest_forecast_values_by_site(
            session=session,
            site_uuids=[site_selection],
            start_utc=starttime,
        )

        forecasts = forecasts.values()

        for forecast in forecasts:
            x = [i.start_utc for i in forecast]
            y = [i.forecast_power_kw for i in forecast]

    # get generation values for selected sites and plot
    with connection.get_session() as session:
        generations = get_pv_generation_by_sites(
            session=session,
            site_uuids=[site_selection],
            start_utc=starttime,
        )

        yy = [generation.generation_power_kw for generation in generations if generation is not None]
        xx = [generation.start_utc for generation in generations if generation is not None] 

    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Latest Forecast for Selected Site"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="KW")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="selected site forecast",
            line=dict(color="#4c9a8e"),
        )
        )
    fig.add_trace(
        go.Scatter(
            x=xx,
            y=yy,
            mode="lines",
            name="selected site generation",
            line=dict(color="#FF9736"),
        )
    )

    st.plotly_chart(fig, theme="streamlit")
