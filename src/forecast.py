import os
from datetime import datetime, timedelta, time, timezone

import plotly.graph_objects as go
import streamlit as st
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models import ForecastValue, GSPYield, Location
from nowcasting_datamodel.read.read import (
    get_forecast_values_latest,
    get_forecast_values,
    get_all_locations,
)
from nowcasting_datamodel.read.read_gsp import get_gsp_yield, get_gsp_yield_sum
from nowcasting_datamodel.read.read_models import get_models

from plots.utils import get_colour_from_model_name

show_pvnet_gsp_sum = os.getenv("SHOW_PVNET_GSP_SUM", "False").lower() == "true"


def forecast_page():
    """Main page for status"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"National and GSP Forecasts"}</h1>',
        unsafe_allow_html=True,
    )
    # get locations
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:
        locations = get_all_locations(session=session)
        locations = [Location.from_orm(location) for location in locations if location.gsp_id < 318]

        gsps = [f"{location.gsp_id}: {location.region_name}" for location in locations]

        st.sidebar.subheader("Select Forecast Model")
        gsp_id = st.sidebar.selectbox("Select a region", gsps, index=0)
        # format gsp_id and get capacity
        gsp_id = int(gsp_id.split(":")[0])
        capacity_mw = [
            location.installed_capacity_mw for location in locations if location.gsp_id == gsp_id
        ][0]

        models = get_models(
            session=session,
            with_forecasts=True,
            forecast_created_utc=datetime.today() - timedelta(days=7),
        )
        models = [model.name for model in models]

        if show_pvnet_gsp_sum:
            models.append("pvnet_gsp_sum")
        forecast_models = st.sidebar.multiselect("Select a model", models, ["pvnet_v2"])

        probabilisitic_models = ["National_xg", "pvnet_v2", "blend"]
        probabilistic_forecasts = [
            model for model in forecast_models if model in probabilisitic_models
        ]

        if len(probabilistic_forecasts) > 0:
            show_prob = st.sidebar.checkbox("Show Probabilities Forecast", value=False)
        else:
            show_prob = False

        if gsp_id != 0:
            if "National_xg" in forecast_models:
                forecast_models.remove("National_xg")
                st.sidebar.warning("National_xg only available for National forecast.")

        use_adjuster = st.sidebar.radio("Use adjuster", [True, False], index=1)

        forecast_type = st.sidebar.radio(
            "Forecast Type", ["Now", "Creation Time", "Forecast Horizon"], index=0
        )
        if forecast_type == "Creation Time":
            now = datetime.now(tz=timezone.utc) - timedelta(days=1)

            d = st.sidebar.date_input("Forecast creation date:", now.date())
            dd = datetime.combine(d, time(0, 0))
            initial_times = [dd - timedelta(days=1) + timedelta(hours=3 * i) for i in range(8)]
            initial_times += [dd + timedelta(minutes=30 * i) for i in range(48)]

            select_init_times = st.sidebar.multiselect(
                "Forecast creation time",
                initial_times,
                [initial_times[x] for x in [2,6, 14, 20, 26, 32, 38]],
            )
            select_init_times = sorted(select_init_times)
            forecast_time = select_init_times[0]
            st.sidebar.write(f"Forecast creation time: {forecast_time}")

            start_datetimes = select_init_times
            end_datetimes = [t + timedelta(days=2) for t in select_init_times]

        elif forecast_type == "Forecast Horizon":
            now = datetime.now(tz=timezone.utc) - timedelta(days=1)
            start_d = st.sidebar.date_input("Forecast start date:", now.date())
            start_t = st.sidebar.time_input("Forecast start time", time(0, 0))

            start_datetimes = [datetime.combine(start_d, start_t)]
            end_datetimes = [
                start_datetime + timedelta(days=2) for start_datetime in start_datetimes
            ]

            # 0 8 hours in 30 mintue chunks, 8 to 36 hours in 3 hour chunks
            forecast_horizon = st.sidebar.selectbox(
                "Forecast Horizon",
                list(range(0, 480, 30)) + list(range(480, 36 * 60, 180)),
                8,
            )
            forecast_time = start_datetimes[0]

        else:
            forecast_time = datetime.now(tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            start_datetimes = [now.date() - timedelta(days=2)]
            end_datetimes = [None]

        forecast_per_model = {}
        for model in forecast_models:
            for i in range(len(start_datetimes)):

                start_datetime = start_datetimes[i]
                end_datetime = end_datetimes[i]

                if forecast_type == "Now":
                    forecast_values = get_forecast_values_latest(
                        session=session,
                        gsp_id=gsp_id,
                        model_name=model,
                        start_datetime=start_datetime,
                    )
                    save_model_name = model
                elif forecast_type == "Creation Time":
                    forecast_values = get_forecast_values(
                        session=session,
                        gsp_ids=[gsp_id],
                        model_name=model,
                        start_datetime=start_datetime,
                        created_utc_limit=start_datetime,
                        only_return_latest=True,
                    )
                    save_model_name = f"{model} {start_datetime}"
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
                    save_model_name = model

                # make ForecastValue objects with _properties
                forecast_per_model[save_model_name] = []
                for f in forecast_values:
                    forecast_value = ForecastValue.from_orm(f)
                    forecast_value._properties = f.properties
                    forecast_per_model[save_model_name].append(forecast_value)

                if use_adjuster:
                    forecast_per_model[save_model_name] = [
                        f.adjust(limit=1000) for f in forecast_per_model[save_model_name]
                    ]

        # get pvlive values
        pvlive_data, pvlive_gsp_sum_dayafter, pvlive_gsp_sum_inday = get_pvlive_data(
            end_datetimes[0], gsp_id, session, start_datetimes[0]
        )

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
    plot_pvlive(fig, gsp_id, pvlive_data, pvlive_gsp_sum_dayafter, pvlive_gsp_sum_inday)
    plot_forecasts(fig, forecast_per_model, probabilisitic_models, show_prob)

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


def plot_pvlive(fig, gsp_id, pvlive_data, pvlive_gsp_sum_dayafter, pvlive_gsp_sum_inday):
    # pvlive on the chart
    for k, v in pvlive_data.items():
        x = [i.datetime_utc for i in v]
        y = [i.solar_generation_kw / 1000 for i in v]

        if k == "PVLive Initial Estimate":
            line = dict(color=get_colour_from_model_name(k), dash="dash")
        elif k == "PVLive Updated Estimate":
            line = dict(color=get_colour_from_model_name(k))

        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=k, line=line))
    # pvlive gsp sum dictionary of values and chart for national forecast
    if gsp_id == 0:
        pvlive_gsp_sum_data = {}
        pvlive_gsp_sum_data["PVLive GSP Sum Estimate"] = [
            GSPYield.from_orm(f) for f in pvlive_gsp_sum_inday
        ]
        pvlive_gsp_sum_data["PVLive GSP Sum Updated"] = [
            GSPYield.from_orm(f) for f in pvlive_gsp_sum_dayafter
        ]

        for k, v in pvlive_gsp_sum_data.items():
            x = [i.datetime_utc for i in v]
            y = [i.solar_generation_kw / 1000 for i in v]

            if k == "PVLive GSP Sum Estimate":
                line = dict(color=get_colour_from_model_name(k), dash="dash")
            elif k == "PVLive GSP Sum Updated":
                line = dict(color=get_colour_from_model_name(k))

            fig.add_trace(
                go.Scatter(x=x, y=y, mode="lines", name=k, line=line, visible="legendonly")
            )


def plot_forecasts(fig, forecast_per_model, probabilisitic_models, show_prob):

    index_forecast_per_model = 0
    for model, forecast in forecast_per_model.items():
        x = [i.target_time for i in forecast]
        y = [i.expected_power_generation_megawatts for i in forecast]

        # count how many other models have the same name but different times
        count = sum(
            [
                1
                for key in list(forecast_per_model.keys())
                if key.split(" ")[0] == model.split(" ")[0]
            ]
        )

        # make opacity of lines depend on the number of models
        opacity = 0.3 + 0.7 * ((index_forecast_per_model + 1) / count)
        index_forecast_per_model += 1
        if index_forecast_per_model == count:
            index_forecast_per_model = 0

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                name=model,
                line=dict(color=get_colour_from_model_name(model, opacity=opacity)),
                hovertemplate="<br>%{x}<br>" + "<b>%{y:.2f}</b>MW",
            )
        )

        if len(forecast) > 0 and show_prob and (model in probabilisitic_models):
            try:
                properties_0 = forecast[0]._properties
                if isinstance(properties_0, dict) and (
                    "10" in properties_0.keys() and "90" in properties_0.keys()
                ):
                    plevel_10 = [i._properties["10"] for i in forecast]
                    plevel_90 = [i._properties["90"] for i in forecast]

                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=plevel_10,
                            mode="lines",
                            name="p10: " + model,
                            line=dict(color=get_colour_from_model_name(model), width=0),
                            showlegend=False,
                        )
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=plevel_90,
                            mode="lines",
                            name="p90: " + model,
                            line=dict(color=get_colour_from_model_name(model), width=0),
                            fill="tonexty",
                            showlegend=False,
                        )
                    )
            except Exception as e:
                print(e)
                print("Could not add plevel to chart")
                raise e


def get_pvlive_data(end_datetime, gsp_id, session, start_datetime):
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
    pvlive_data["PVLive Initial Estimate"] = [GSPYield.from_orm(f) for f in pvlive_inday]
    pvlive_data["PVLive Updated Estimate"] = [GSPYield.from_orm(f) for f in pvlive_dayafter]
    return pvlive_data, pvlive_gsp_sum_dayafter, pvlive_gsp_sum_inday
