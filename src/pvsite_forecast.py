import os
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta, time, timezone
from pvsite_datamodel.read import get_site_by_uuid
from pvsite_datamodel.read.model import get_models
from sqlalchemy.orm import Session
from pvsite_datamodel.connection import DatabaseConnection
from pvsite_datamodel.read import (
    get_all_sites,
    get_pv_generation_by_sites,
    get_forecast_values_fast,
    get_forecast_values_day_ahead_fast,
)

import plotly.graph_objects as go
import pytz

# Penalty Calculator
def calculate_penalty(df, region, asset_type, capacity_kw):
    """
    Calculate penalties dynamically based on region, asset type, and capacity.
    """
    penalty_bands = {
        ("Rajasthan", "solar"): [(10, 15, 0.1), (15, None, 1.0)],
        ("Madhya Pradesh", "wind"): [(10, 20, 0.25), (20, 30, 0.5), (30, None, 0.75)],
        ("Gujarat", "solar"): [(7, 15, 0.25), (15, 23, 0.5), (23, None, 0.75)],
        ("Gujarat", "wind"): [(12, 20, 0.25), (20, 28, 0.5), (28, None, 0.75)],
        ("Karnataka", "solar"): [(10, 20, 0.25), (20, 30, 0.5), (30, None, 0.75)],
    }
    default_bands = [(10, 20, 0.25), (20, 30, 0.5), (30, None, 0.75)]
    bands = penalty_bands.get((region, asset_type.lower()), default_bands)

    deviation = df["forecast_power_kw"] - df["generation_power_kw"]
    deviation_percentage = (deviation / capacity_kw) * 100

    penalty = pd.Series(0, index=df.index)
    for lower, upper, rate in bands:
        mask = abs(deviation_percentage) >= lower
        penalty_band = (abs(deviation_percentage[mask]).clip(upper=upper) - lower) / 100 \
                       * rate * capacity_kw
        penalty[mask] += penalty_band

    total_penalty = penalty.sum()
    return penalty, total_penalty


# Internal Dashboard
def pvsite_forecast_page():
    """Main page for pvsite forecast"""

    st.markdown(
        '<h1 style="color:#63BCAF;font-size:48px;">PV Site Forecast</h1>',
        unsafe_allow_html=True,
    )

    # Database connection & site list
    url = os.environ["SITES_DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:
        sites = get_all_sites(session=session)
        site_uuids = [s.location_uuid for s in sites if s.location_uuid]

        # Toggle between selecting by UUID or client name
        query_method = st.sidebar.radio("Select site by", ("site_uuid", "client_site_name"))

        if query_method == "site_uuid":
            site_selection_uuid = st.sidebar.selectbox(
                "Select sites by site_uuid", site_uuids
            )
        else:
            client_site_name = st.sidebar.selectbox(
                "Select sites by client_site_name",
                sorted([s.client_location_name for s in sites]),
            )
            site_selection_uuid = next(
                s.location_uuid
                for s in sites
                if s.client_location_name == client_site_name
            )

        # Now offer resample options at the correct level
        resample = st.sidebar.selectbox("Resample data", [None, "15min", "30min"], None)

        timezone_selected = st.sidebar.selectbox("Select timezone", ["UTC", "Asia/Calcutta"])
        tz = pytz.timezone(timezone_selected)

        # Date inputs
        day_after_tomorrow = datetime.today() + timedelta(days=3)
        start_date = st.sidebar.date_input(
            "Start Date",
            min_value=datetime.today() - timedelta(days=365),
            max_value=datetime.today(),
        )
        end_date = st.sidebar.date_input("End Date", day_after_tomorrow)

        forecast_type = st.sidebar.selectbox(
            "Select Forecast Type", ["Latest", "Forecast_horizon", "DA"], 0
        )

        # Fetch site metadata
        site = get_site_by_uuid(session, site_selection_uuid)
        capacity = site.capacity_kw
        region = site.region
        asset_type = site.asset_type
        country = site.country

        # Handle "Latest" created timestamp input
        if forecast_type == "Latest":
            default_created = pd.Timestamp.utcnow().ceil("15min")
            default_created = default_created.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)
            created_str = st.sidebar.text_input("Created Before", default_created)
            created = datetime.fromisoformat(created_str) if created_str else default_created
        else:
            created = None

        # Forecast horizon options
        if forecast_type == "Forecast_horizon":
            forecast_horizon = st.sidebar.selectbox("Select Forecast Horizon", range(0, 2880, 15), 6)
        else:
            forecast_horizon = None

        # Day‐ahead settings
        if forecast_type == "DA":
            day_ahead_hours = 9
            now = datetime.now()
            delta = tz.localize(now) - now.replace(tzinfo=timezone.utc)
            day_ahead_timezone_delta = (24 - delta.seconds / 3600) % 24
            if site.country.lower() == "india":
                day_ahead_timezone_delta = 5.5
            st.write(
                f"Forecast for {day_ahead_hours} o'clock the day before "
                f"with {day_ahead_timezone_delta}h timezone delta"
            )
        else:
            day_ahead_hours = day_ahead_timezone_delta = None

        # Display selection summary
        st.write(
            "Forecast for",
            site_selection_uuid,
            "-", site.client_location_name,
            "from", start_date,
            "to", end_date,
            "(created before", created, ")"
        )

        # Convert dates to UTC datetimes
        start_dt = tz.localize(datetime.combine(start_date, time.min)).astimezone(pytz.utc)
        end_dt   = tz.localize(datetime.combine(end_date,   time.min)).astimezone(pytz.utc)
        if created:
            created = tz.localize(created).astimezone(pytz.utc)

        # Retrieve ML models
        ml_models = get_models(
            session=session,
            start_datetime=start_dt,
            end_datetime=end_dt,
            site_uuid=site_selection_uuid,
            forecast_horizon=15,
        )
        if not ml_models:
            class Dummy: name = None
            ml_models = [Dummy()]

        # Fetch forecast & generation series
        xs, ys = {}, {}
        for m in ml_models:
            if day_ahead_hours is not None:
                fv = get_forecast_values_day_ahead_fast(
                    session=session,
                    site_uuid=site_selection_uuid,
                    start_utc=start_dt,
                    end_utc=end_dt,
                    day_ahead_hours=day_ahead_hours,
                    day_ahead_timezone_delta_hours=day_ahead_timezone_delta,
                    model_name=m.name,
                )
            else:
                fv = get_forecast_values_fast(
                    session=session,
                    site_uuid=site_selection_uuid,
                    start_utc=start_dt,
                    created_by=created,
                    created_after=start_dt - timedelta(days=2),
                    forecast_horizon_minutes=forecast_horizon,
                    end_utc=end_dt,
                    model_name=m.name,
                )

            # convert times to selected TZ
            times = [t.start_utc.replace(tzinfo=pytz.utc).astimezone(tz) for t in fv]
            powers = [t.forecast_power_kw for t in fv]
            xs[m.name], ys[m.name] = times, powers

        gens = get_pv_generation_by_sites(
            session=session,
            site_uuids=[site_selection_uuid],
            start_utc=start_dt,
            end_utc=end_dt,
        )
        xx = [g.start_utc.replace(tzinfo=pytz.utc).astimezone(tz) for g in gens if g]
        yy = [g.generation_power_kw for g in gens if g]

    # Build DataFrames
    df_forecast = []
    for name in xs:
        df_temp = pd.DataFrame({
            "forecast_datetime": xs[name],
            f"forecast_power_kw_{name}": ys[name]
        })
        df_forecast = df_temp if not df_forecast else df_forecast.merge(df_temp, on="forecast_datetime", how="outer")
    if not df_forecast:
        df_forecast = pd.DataFrame(columns=["forecast_datetime"])
    df_generation = pd.DataFrame({"generation_datetime": xx, "generation_power_kw": yy})

    df_forecast.set_index("forecast_datetime", inplace=True)
    df_generation.set_index("generation_datetime", inplace=True)

    # Only prompt when no resample; otherwise resample & merge
    if resample is None:
        st.caption("Please resample to '15min' to get MAE")
    else:
        df_forecast = df_forecast.resample(resample).mean()
        df_generation = df_generation.resample(resample).mean()
        df_all = df_forecast.merge(df_generation, left_index=True, right_index=True, how="outer")
        xx = df_all.index
        yy = df_all["generation_power_kw"]

    # Plotting
    fig = go.Figure(layout=go.Layout(
        title="Latest Forecast for Selected Site",
        xaxis_title=f"Time [{timezone_selected}]",
        yaxis_title="kW",
        legend_title="Legend",
    ))
    for name in ys:
        fig.add_trace(go.Scatter(
            x=df_forecast.index,
            y=df_forecast[f"forecast_power_kw_{name}"],
            mode="lines", name=f"forecast_{name}"
        ))
    fig.add_trace(go.Scatter(x=xx, y=yy, mode="lines", name="generation", line=dict(color="#FF9736")))
    st.plotly_chart(fig, theme="streamlit")

    # Download merged data as CSV
    @st.cache_data
    def convert_df(df: pd.DataFrame):
        return df.to_csv().encode("utf-8")

    df_out = df_all if resample else pd.concat([df_forecast, df_generation], axis=1)
    csv = convert_df(df_out)
    now = datetime.now().isoformat()
    st.download_button(
        "Download data as CSV",
        data=csv,
        file_name=f"site_forecast_{site_selection_uuid}_{now}.csv",
        mime="text/csv",
    )

    # … rest of your error‐metric visuals unchanged …
