import os
from datetime import datetime, timedelta, time
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

from plots.utils import (
    get_colour_from_model_name,
    model_is_probabilistic,
    get_recent_available_model_names,
)

from plots.elexon_plots import add_elexon_plot


class GSPLabeler:
    """A function class to add the GSP name to the GSP IDs"""

    def __init__(self, gsp_ids, gsp_names):
        """A function class to add the GSP name to the GSP IDs"""
        self.gsp_ids = gsp_ids
        self.gsp_names = gsp_names

    def __call__(self, gsp_id):
        """Get GSP label"""
        i = self.gsp_ids.index(gsp_id)
        return f"{gsp_id}: {self.gsp_names[i]}"


def forecast_page():
    """Main page for status"""
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"National and GSP Forecasts"}</h1>',
        unsafe_allow_html=True,
    )

    st.sidebar.subheader("Select Forecast Model")

    connection = DatabaseConnection(url=os.environ["DB_URL"], echo=True)
    with connection.get_session() as session:
        # Add dropdown to select GSP region
        locations = get_all_locations(session=session)
        locations = [Location.from_orm(loc) for loc in locations if loc.gsp_id < 342]
        gsp_ids = [loc.gsp_id for loc in locations]
        gsp_names = [loc.region_name for loc in locations]

        gsp_labeler = GSPLabeler(gsp_ids, gsp_names)

        gsp_id = st.sidebar.selectbox("Select a region", gsp_ids, index=0, format_func=gsp_labeler)

        # Get effective capacity of selected GSP
        capacity_mw = locations[gsp_ids.index(gsp_id)].installed_capacity_mw
        # Find recent available models
        available_models = get_recent_available_model_names(session)
        # Add selection for models
        selected_models = st.sidebar.multiselect("Select models", available_models, ["pvnet_v2"])
        # If any selected models are probabilistic add checkbox to show quantiles
        selected_prob_models = [model for model in selected_models if model_is_probabilistic(model)]

        if len(selected_prob_models) > 0:
            show_prob = st.sidebar.checkbox("Show Probabilities Forecast", value=False)
        else:
            show_prob = False

        if gsp_id != 0 and ("National_xg" in selected_models):
            selected_models.remove("National_xg")
            st.sidebar.warning("National_xg only available for National forecast.")
        # Add selection for adjuster
        use_adjuster = st.sidebar.radio("Use adjuster", [True, False], index=1)
        # Add selection for forecast type
        forecast_type = st.sidebar.radio(
            "Forecast Type", ["Now", "Creation Time", "Forecast Horizon"], index=0
        )

        now = datetime.now()
        today = now.date()
        yesterday = today - timedelta(days=1)

        if forecast_type == "Now":
            start_datetimes = [today - timedelta(days=2)]
            end_datetimes = [None]

        elif forecast_type == "Creation Time":
            # Add calendar to select start date - defaults to yesterday
            date_sel = st.sidebar.date_input("Forecast creation date:", yesterday)
            # Add dropdown selection of init-times
            dt_sel = datetime.combine(date_sel, time(0, 0))
            initial_times = [dt_sel - timedelta(days=1) + timedelta(hours=3 * i) for i in range(8)]
            initial_times += [dt_sel + timedelta(minutes=30 * i) for i in range(48)]

            select_init_times = st.sidebar.multiselect(
                "Forecast creation time",
                initial_times,
                [initial_times[x] for x in [14, 20, 26, 32, 38]],
            )

            select_init_times = sorted(select_init_times)

            start_datetimes = select_init_times
            end_datetimes = [t + timedelta(days=2) for t in select_init_times]

        elif forecast_type == "Forecast Horizon":
            # Add calendar and time selections for datetime
            date_sel = st.sidebar.date_input("Forecast start date:", yesterday)
            time_sel = st.sidebar.time_input("Forecast start time", time(0, 0))

            dt_sel = datetime.combine(date_sel, time_sel)
            start_datetimes = [dt_sel]
            end_datetimes = [dt_sel + timedelta(days=2)]

            # Add selection for horizon
            # 0-8 hours in 30 mintue chunks, 8-36 hours in 3 hour chunks
            forecast_horizon = st.sidebar.selectbox(
                "Forecast Horizon (mins)",
                list(range(0, 480, 30)) + list(range(480, 36 * 60, 180)),
                0,
            )
        # Get the data to plot
        forecast_per_model = {}
        for model in selected_models:
            for start_dt, end_dt in zip(start_datetimes, end_datetimes):
                if forecast_type == "Now":
                    forecast_values = get_forecast_values_latest(
                        session=session, gsp_id=gsp_id, model_name=model, start_datetime=start_dt
                    )
                    label = model

                elif forecast_type == "Creation Time":
                    forecast_values = get_forecast_values(
                        session=session,
                        gsp_ids=[gsp_id],
                        model_name=model,
                        start_datetime=start_dt,
                        created_utc_limit=start_dt,
                        only_return_latest=True,
                    )
                    label = f"{model} {start_dt}"

                elif forecast_type == "Forecast Horizon":
                    forecast_values = get_forecast_values(
                        session=session,
                        gsp_ids=[gsp_id],
                        model_name=model,
                        start_datetime=start_dt,
                        forecast_horizon_minutes=forecast_horizon,
                        end_datetime=end_dt,
                        only_return_latest=True,
                    )
                    label = model

                # Make ForecastValue objects with _properties attribute and maybe adjust
                forecast_per_model[label] = []
                for f in forecast_values:
                    forecast_value = ForecastValue.from_orm(f)
                    forecast_value._properties = f.properties
                    if use_adjuster:
                        forecast_value = forecast_value.adjust(limit=1000)
                    forecast_per_model[label].append(forecast_value)
        # Get pvlive values
        pvlive_data, pvlive_gsp_sum_dayafter, pvlive_gsp_sum_inday = get_pvlive_data(
            end_datetimes[0], gsp_id, session, start_datetimes[0]
        )
    # Make figure
    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Latest Forecast"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="MW")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )
    # Plot PVLive values and the forecasts
    plot_pvlive(fig, gsp_id, pvlive_data, pvlive_gsp_sum_dayafter, pvlive_gsp_sum_inday)
    plot_forecasts(fig, forecast_per_model, selected_prob_models, show_prob)

    if end_datetimes[0] is None or now <= max(end_datetimes):
        # Add vertical line to indicate now
        fig.add_trace(
            go.Scatter(
                x=[now, now],
                y=[0, capacity_mw],
                mode="lines",
                name="now",
                line=dict(color="red", width=4, dash="dash"),
                showlegend=False,
            )
        )

    # Only add Elexon plot if the National region is selected
    if gsp_id == 0:
        fig = add_elexon_plot(fig, start_datetimes, end_datetimes)

    st.plotly_chart(fig, theme="streamlit")

def plot_pvlive(fig, gsp_id, pvlive_data, pvlive_gsp_sum_dayafter, pvlive_gsp_sum_inday):
    # pvlive on the chart
    for k, v in pvlive_data.items():
        x = [i.datetime_utc for i in v]
        y = [i.solar_generation_kw / 1000 for i in v]

        line = {"color": get_colour_from_model_name(k)}
        if k == "PVLive Initial Estimate":
            line["dash"] = "dash"

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

            line = {"color": get_colour_from_model_name(k)}
            if k == "PVLive GSP Sum Estimate":
                line["dash"] = "dash"

            fig.add_trace(
                go.Scatter(x=x, y=y, mode="lines", name=k, line=line, visible="legendonly")
            )


def plot_forecasts(fig, forecast_per_model, selected_prob_models, show_prob):

    index_forecast_per_model = 0
    for model, forecast in forecast_per_model.items():
        x = [i.target_time for i in forecast]
        y = [i.expected_power_generation_megawatts for i in forecast]

        # Count how many other models have the same name but different times
        count = len([key for key in forecast_per_model if key.split(" ")[0] == model.split(" ")[0]])

        # Make opacity of lines depend on the number of models
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
                line=dict(color=get_colour_from_model_name(model)),
                opacity=opacity,
                hovertemplate="<br>%{x}<br>" + "<b>%{y:.2f}</b>MW",
                legendgroup=model,
            )
        )

        if len(forecast) > 0 and show_prob and (model in selected_prob_models):
            try:
                properties_0 = forecast[0]._properties
                if isinstance(properties_0, dict) and (
                    "10" in properties_0 and "90" in properties_0
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
                            legendgroup=model,
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
                            legendgroup=model,
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
        gsp_ids=list(range(1, 342)),
        start_datetime_utc=start_datetime,
        end_datetime_utc=end_datetime,
        regime="in-day",
    )
    pvlive_gsp_sum_dayafter = get_gsp_yield_sum(
        session=session,
        gsp_ids=list(range(1, 342)),
        start_datetime_utc=start_datetime,
        end_datetime_utc=end_datetime,
        regime="day-after",
    )
    pvlive_data = {}
    pvlive_data["PVLive Initial Estimate"] = [GSPYield.from_orm(f) for f in pvlive_inday]
    pvlive_data["PVLive Updated Estimate"] = [GSPYield.from_orm(f) for f in pvlive_dayafter]
    return pvlive_data, pvlive_gsp_sum_dayafter, pvlive_gsp_sum_inday
