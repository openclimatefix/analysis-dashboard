from datetime import datetime, timedelta, time, timezone
import streamlit as st
import os
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.read.read import (
    get_forecast_values_latest,
    get_forecast_values,
    get_all_locations,
)
from nowcasting_datamodel.read.read_gsp import get_gsp_yield
from nowcasting_datamodel.models import ForecastValue, GSPYield, Location
from get_data import get_gsp_yield_sum
import plotly.graph_objects as go


colour_per_model = {
    "cnn": "#FFD053",
    "National_xg": "#7BCDF3",
    "pvnet_v2": "#4c9a8e",
    "PVLive Initial Estimate": "#e4e4e4",
    "PVLive Updated Estimate": "#e4e4e4",
    "PVLive GSP Sum Estimate": "#FF9736",
    "PVLive GSP Sum Updated": "#FF9736",
}


def forecast_page():
    """Main page for status"""
    st.markdown(
        f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Forecast"}</h1>',
        unsafe_allow_html=True,
    )
    # get locations
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:
        locations = get_all_locations(session=session)
        locations = [
            Location.from_orm(location)
            for location in locations
            if location.gsp_id < 318
        ]

    gsps = [f"{location.gsp_id}: {location.region_name}" for location in locations]

    st.sidebar.subheader("Select Forecast Model")
    gsp_id = st.sidebar.selectbox("Select a region", gsps, index=0)
    # format gsp_id and get capacity
    gsp_id = int(gsp_id.split(":")[0])
    capacity_mw = [
        location.installed_capacity_mw
        for location in locations
        if location.gsp_id == gsp_id
    ][0]

    forecast_models = st.sidebar.multiselect(
        "Select a model", ["cnn", "National_xg", "pvnet_v2"], ["cnn"]
    )
    use_adjuster = st.sidebar.radio("Use adjuster", [True, False], index=1)

    forecast_type = st.sidebar.radio(
        "Forecast Type", ["Now", "Creation Time", "Forecast Horizon"], index=0
    )
    if forecast_type == "Creation Time":
        now = datetime.now(tz=timezone.utc) - timedelta(days=1)
        d = st.sidebar.date_input("Forecast creation date:", now.date())
        t = st.sidebar.time_input("Forecast creation time", time(12, 00))
        forecast_time = datetime.combine(d, t)
        st.sidebar.write(f"Forecast creation time: {forecast_time}")
    elif forecast_type == "Forecast Horizon":
        now = datetime.now(tz=timezone.utc) - timedelta(days=1)
        start_d = st.sidebar.date_input("Forecast start date:", now.date())
        start_t = st.sidebar.time_input("Forecast start time", time(12, 00))

        start_datetime = datetime.combine(start_d, start_t)
        end_datetime = start_datetime + timedelta(days=2)

        forecast_horizon = st.sidebar.selectbox(
            "Forecast Horizon", list(range(0, 480, 30)), 8
        )
    else:
        forecast_time = datetime.now(tz=timezone.utc)

    with connection.get_session() as session:

        forecast_per_model = {}
        if forecast_type == "Now":
            now = datetime.now(tz=timezone.utc)
            start_datetime = now.date() - timedelta(days=2)
            end_datetime = None
        elif forecast_type == "Creation Time":
            start_datetime = forecast_time
            end_datetime = forecast_time + timedelta(days=2)
        else:
            forecast_time = start_datetime

        for model in forecast_models:
            if forecast_type == "Now":
                forecast_values = get_forecast_values_latest(
                    session=session,
                    gsp_id=gsp_id,
                    model_name=model,
                    start_datetime=start_datetime,
                )
            elif forecast_type == "Creation Time":
                forecast_values = get_forecast_values(
                    session=session,
                    gsp_ids=[gsp_id],
                    model_name=model,
                    start_datetime=start_datetime,
                    created_utc_limit=start_datetime,
                    only_return_latest=True,
                )
            else:
                forecast_values = get_forecast_values(
                    session=session,
                    gsp_id=gsp_id,
                    model_name=model,
                    start_datetime=start_datetime,
                    forecast_horizon_minutes=forecast_horizon,
                    end_datetime=end_datetime,
                    only_return_latest=True,
                )

            forecast_per_model[model] = [
                ForecastValue.from_orm(f) for f in forecast_values
            ]

            if use_adjuster:
                forecast_per_model[model] = [
                    f.adjust(limit=1000) for f in forecast_per_model[model]
                ]

        # get pvlive values
        pvlive_inday = get_gsp_yield(
            session=session,
            gsp_ids=[gsp_id],
            start_datetime_utc=start_datetime,
            end_datetime_utc=end_datetime,
            regime="in-day",
        )
        pvlive_dayafter = get_gsp_yield(
            session=session,
            gsp_ids=[gsp_id],
            start_datetime_utc=start_datetime,
            end_datetime_utc=end_datetime,
            regime="day-after",
        )

        pvlive_gsp_sum_inday = get_gsp_yield_sum(
            session=session,
            gsp_ids=list(range(1, 318)),
            start_datetime_utc=start_datetime,
            end_datetime_utc=end_datetime,
            regime="in-day",
        )

        pvlive_gsp_sum_dayafter = get_gsp_yield_sum(
            session=session,
            gsp_ids=list(range(1, 318)),
            start_datetime_utc=start_datetime,
            end_datetime_utc=end_datetime,
            regime="day-after",
        )

        pvlive_data = {}
        pvlive_data["PVLive Initial Estimate"] = [
            GSPYield.from_orm(f) for f in pvlive_inday
        ]
        pvlive_data["PVLive Updated Estimate"] = [
            GSPYield.from_orm(f) for f in pvlive_dayafter
        ]

        pvlive_gsp_sum_data = {}
        pvlive_gsp_sum_data["PVLive GSP Sum Estimate"] = [
            GSPYield.from_orm(f) for f in pvlive_gsp_sum_inday
        ]
        pvlive_gsp_sum_data["PVLive GSP Sum Updated"] = [
            GSPYield.from_orm(f) for f in pvlive_gsp_sum_dayafter
        ]

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

        fig.add_trace(
            go.Scatter(
                x=x, y=y, mode="lines", name=k, line=dict(color=colour_per_model[k])
            )
        )

    # pvlive on the chart
    for k, v in pvlive_data.items():

        x = [i.datetime_utc for i in v]
        y = [i.solar_generation_kw / 1000 for i in v]

        if k == "PVLive Initial Estimate":
            line = dict(color=colour_per_model[k], dash="dash")
        elif k == "PVLive Updated Estimate":
            line = dict(color=colour_per_model[k])

        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=k, line=line))

    # pvlive gsp sum on the chart for national forecast
    if gsp_id == 0:
        for k, v in pvlive_gsp_sum_data.items():

            x = [i.datetime_utc for i in v]
            y = [i.solar_generation_kw / 1000 for i in v]

            if k == "PVLive GSP Sum Estimate":
                line = dict(color=colour_per_model[k], dash="dash")
            elif k == "PVLive GSP Sum Updated":
                line = dict(color=colour_per_model[k])

            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=k, line=line))

    fig.add_trace(
        go.Scatter(
            x=[forecast_time, forecast_time],
            y=[0, capacity_mw],
            mode="lines",
            name="now",
            line=dict(color="red", width=4, dash="dash"),
            showlegend=False,
        )
    )

    st.plotly_chart(fig, theme="streamlit")
