from datetime import datetime, timedelta, time
import streamlit as st
import os
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.read.read import get_forecast_values_latest, get_forecast_values
from nowcasting_datamodel.read.read_gsp import get_gsp_yield
from nowcasting_datamodel.models import ForecastValue, GSPYield

import plotly.graph_objects as go


def forecast_page():
    """Main page for status"""
    st.markdown(
        f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>', unsafe_allow_html=True
    )
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Forecast"}</h1>', unsafe_allow_html=True
    )

    st.sidebar.subheader("Select Forecast Model")
    forecast_models = st.sidebar.multiselect(
        "Select a model", ["cnn", "National_xg", "pvnet_v2"], ["cnn"]
    )
    use_adjuster = st.sidebar.radio("Use adjuster", [True, False], index=1)


    use_most_recent = st.sidebar.radio("Most recent", [True, False], index=0)
    if not use_most_recent:
        now = datetime.utcnow() - timedelta(days=1)
        d = st.sidebar.date_input("Forecast creation date:", now.date())
        t = st.sidebar.time_input("Forecast creation time", time(12,00))
        forecast_time = datetime.combine(d, t)
        st.sidebar.write(f"Forecast creation time: {forecast_time}")
    else:
        forecast_time = datetime.utcnow()

    # get forecast results
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:

        forecast_per_model = {}
        if use_most_recent:
            now = datetime.utcnow()
            start_datetime = now.date() - timedelta(days=2)
            end_datetime = None
        else:
            start_datetime = forecast_time
            end_datetime = forecast_time + timedelta(days=2)

        for model in forecast_models:
            if use_most_recent:
                forecast_values = get_forecast_values_latest(
                    session=session,
                    gsp_id=0,
                    model_name=model,
                    start_datetime=start_datetime,
                )
            else:
                forecast_values = get_forecast_values(
                    session=session,
                    gsp_id=0,
                    model_name=model,
                    start_datetime=start_datetime,
                    created_utc_limit=start_datetime,
                    only_return_latest=True
                )

            forecast_per_model[model] = [ForecastValue.from_orm(f) for f in forecast_values]

            if use_adjuster:
                forecast_per_model[model] = [f.adjust(limit=1000) for f in forecast_per_model[model]]

        # get pvlive values
        pvlive_inday = get_gsp_yield(
            session=session,
            gsp_ids=[0],
            start_datetime_utc=start_datetime,
            end_datetime_utc=end_datetime,
            regime="in-day",
        )
        pvlive_dayafter = get_gsp_yield(
            session=session,
            gsp_ids=[0],
            start_datetime_utc=start_datetime,
            end_datetime_utc=end_datetime,
            regime="day-after",
        )

        pvlive_data = {}
        pvlive_data['PVLive Initial estimate'] = [GSPYield.from_orm(f) for f in pvlive_inday]
        pvlive_data['PVLive Updated estimate'] = [GSPYield.from_orm(f) for f in pvlive_dayafter]

    # make plot
    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Latest Forecast"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="MW")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )
    # forecasts on the chart
    for k, v in forecast_per_model.items():

        x = [i.target_time for i in v]
        y = [i.expected_power_generation_megawatts for i in v]

        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=k))

    # pvlive on the chart
    for k, v in pvlive_data.items():

        x = [i.datetime_utc for i in v]
        y = [i.solar_generation_kw/1000 for i in v]

        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=k))

    fig.add_trace(go.Scatter(x=[forecast_time,forecast_time], y=[0,10000], mode="lines", name='now', line=dict(color='red', width=4,dash='dash'), showlegend=False))

    st.plotly_chart(fig, theme="streamlit")
