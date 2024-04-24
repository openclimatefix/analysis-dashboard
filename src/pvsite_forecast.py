import os
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, time, timezone
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
        f'<h1 style="color:#63BCAF;font-size:48px;">{"PV Site Forecast"}</h1>',
        unsafe_allow_html=True,
    )
    # get site_uuids from database
    url = os.environ["SITES_DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:
        site_uuids = get_all_sites(session=session)
        site_uuids = [
            sites.site_uuid for sites in site_uuids if sites.site_uuid is not None
        ]
      
    site_selection = st.sidebar.selectbox("Select sites by site_uuid", site_uuids,)
    starttime = st.sidebar.date_input("Start Date", min_value=datetime.today() - timedelta(days=365), max_value=datetime.today())

    forecast_type = st.sidebar.selectbox("Select Forecast Type", ["Latest", "Forecast_horizon", "DA"], 0)

    if forecast_type == "Latest":
        created = st.sidebar.text_input("Created Before", pd.Timestamp.now().ceil('15min'))

        if created == "":
            created = datetime.now()
        else:
            created = datetime.fromisoformat(created)
        st.write("Forecast for", site_selection, "starting on", starttime, "created by", created)
    else:
        created = None

    if forecast_type == "Forecast_horizon":
        forecast_horizon = st.sidebar.selectbox("Select Forecast Horizon", range(0,2880,15), 6)
    else:
        forecast_horizon = None

    if forecast_type == "DA":
        # TODO make these more flexible
        day_ahead_hours = 9
        day_ahead_timezone_delta_hours = 5.5
        st.write(f"Forecast for {day_ahead_hours} oclock the day before "
                 f"with {day_ahead_timezone_delta_hours} hour timezone delta")
    else:
        day_ahead_hours = None
        day_ahead_timezone_delta_hours = None

    # an option to resample to the data
    resample = st.sidebar.selectbox("Resample data", [None, "15T", "30T"], None)

    # get forecast values for selected sites and plot
    with connection.get_session() as session:
        forecasts = get_latest_forecast_values_by_site(
            session=session,
            site_uuids=[site_selection],
            start_utc=starttime,
            created_by=created,
            forecast_horizon_minutes=forecast_horizon,
            day_ahead_hours=day_ahead_hours,
            day_ahead_timezone_delta_hours=day_ahead_timezone_delta_hours
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

    df_forecast = pd.DataFrame({'forecast_datetime': x, 'forecast_power_kw': y})
    df_generation = pd.DataFrame({'generation_datetime': xx, 'generation_power_kw': yy})

    if resample is not None:
        df_forecast.set_index('forecast_datetime', inplace=True)
        df_generation.set_index('generation_datetime', inplace=True)
        df_forecast = df_forecast.resample(resample).mean()
        df_generation = df_generation.resample(resample).mean()

        # merge together
        df_all = df_forecast.merge(df_generation, left_index=True, right_index=True, how='outer')

        # select variables
        xx = df_all.index
        x = df_all.index
        yy = df_all['generation_power_kw']
        y = df_all['forecast_power_kw']

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

    # download data,
    @st.cache_data
    def convert_df(df: pd.DataFrame):
        # IMPORTANT: Cache the conversion to prevent computation on every rerun
        return df.to_csv().encode('utf-8')

    # join data together
    if resample is not None:
        df = df_all
    else:
        df = pd.concat([df_forecast, df_generation], axis=1)
    csv = convert_df(df)
    now = datetime.now().isoformat()

    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f'site_forecast_{site_selection}_{now}.csv',
        mime='text/csv',
    )