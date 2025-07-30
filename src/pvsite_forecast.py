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
    get_latest_forecast_values_by_site,
)

import plotly.graph_objects as go
import pytz

# Penalty Calculator
def calculate_penalty(df, region, asset_type, capacity_kw):
    """
    Calculate penalties dynamically based on region, asset type, and capacity.
    """
    # Define penalty bands for combinations of region and asset type
    penalty_bands = {
        ("Rajasthan", "solar"): [
            (
                10,
                15,
                0.1,
            ),  # Band (lowest bound of the band range, highest bound of the band range, penalty that particular band carries)
            (
                15,
                None,
                1.0,
            ),  # Band (lowest bound of the band range, no highest bound of the band range, penalty that particular band carries)
        ],
        ("Madhya Pradesh", "wind"): [
            (10, 20, 0.25),
            (20, 30, 0.5),
            (30, None, 0.75),
        ],
        ("Gujarat", "solar"): [
            (7, 15, 0.25),
            (15, 23, 0.5),
            (23, None, 0.75),
        ],
        ("Gujarat", "wind"): [
            (12, 20, 0.25),
            (20, 28, 0.5),
            (28, None, 0.75),
        ],
        ("Karnataka", "solar"): [
            (10, 20, 0.25),
            (20, 30, 0.5),
            (30, None, 0.75),
        ],
    }

    # Fallback bands if region and asset type combination is missing
    default_bands = [
        (10, 20, 0.25),
        (20, 30, 0.5),
        (30, None, 0.75),
    ]

    # Fetch penalty bands based on region and asset type
    bands = penalty_bands.get((region, asset_type.lower()), default_bands)

    # Calculate deviation and deviation percentage
    deviation = df["forecast_power_kw"] - df["generation_power_kw"]
    deviation_percentage = (deviation / capacity_kw) * 100

    # Initialize penalty column
    penalty = pd.Series(0, index=df.index)

    # Apply penalty calculation for each band
    for lower, upper, rate in bands:

        mask = (abs(deviation_percentage) >= lower)
        penalty_band = (abs(deviation_percentage[mask]).clip(upper=upper) - lower)/100 * rate * capacity_kw
        penalty[mask] += penalty_band

    # Calculate total penalty
    total_penalty = penalty.sum()

    return penalty, total_penalty


# Internal Dashboard
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
        sites = get_all_sites(session=session)
        site_uuids = [sites.location_uuid for sites in sites if sites.location_uuid is not None]

        # streamlit toggle between site_uuid and client_site_name
        query_method = st.sidebar.radio(
            "Select site by", ("site_uuid", "client_site_name")
        )

        if query_method == "site_uuid":
            site_selection_uuid = st.sidebar.selectbox(
                "Select sites by site_uuid",
                site_uuids,
            )

        else:
            client_site_name = st.sidebar.selectbox(
                "Select sites by client_site_name",
                sorted([sites.client_location_name for sites in sites]),
            )
            site_selection_uuid = [
                sites.location_uuid
                for sites in sites
                if sites.client_location_name == client_site_name
            ][0]

        timezone_selected = st.sidebar.selectbox(
            "Select timezone", ["UTC", "Asia/Calcutta"]
        )
        timezone_selected = pytz.timezone(timezone_selected)

        day_after_tomorrow = datetime.today() + timedelta(days=3)
        starttime = st.sidebar.date_input(
            "Start Date",
            min_value=datetime.today() - timedelta(days=365),
            max_value=datetime.today(),
        )
        endtime = st.sidebar.date_input("End Date", day_after_tomorrow)

        forecast_type = st.sidebar.selectbox(
            "Select Forecast Type", ["Latest", "Forecast_horizon", "DA"], 0
        )

        # get site from database
        site = get_site_by_uuid(session, site_selection_uuid)
        capacity = site.capacity_kw
        site_client_site_name = site.client_location_name
        country = site.country

        # Extract region, asset type, and capacity dynamically
        region = site.region  # Assume site object has a 'region' attribute
        asset_type = site.asset_type  # Assume site object has an 'asset_type' attribute
        capacity_kw = site.capacity_kw  # Extract capacity dynamically

        if forecast_type == "Latest":
            created = pd.Timestamp.utcnow().ceil("15min")
            created = created.astimezone(timezone.utc)
            created = created.astimezone(timezone_selected)
            created = created.replace(tzinfo=None)
            created = st.sidebar.text_input("Created Before", created)

            if created == "":
                created = pd.Timestamp.utcnow().ceil("15min")
                created = created.astimezone(timezone.utc)
                created = created.astimezone(timezone_selected)
                created = created.replace(tzinfo=None)
            else:
                created = datetime.fromisoformat(created)
        else:
            created = None

        if forecast_type == "Forecast_horizon":
            forecast_horizon = st.sidebar.selectbox(
                "Select Forecast Horizon", range(0, 2880, 15), 6
            )
        else:
            forecast_horizon = None

        if forecast_type == "DA":
            # TODO make these more flexible
            day_ahead_hours = 9

            # find the difference in hours for the timezone
            now = datetime.now()
            d = timezone_selected.localize(now) - now.replace(tzinfo=timezone.utc)
            day_ahead_timezone_delta_hours = (24 - d.seconds / 3600) % 24

            # get site from database, if india set day_ahead_timezone_delta_hours to 5.5 hours
            site = get_site_by_uuid(session, site_selection_uuid)
            if site.country == "india":
                day_ahead_timezone_delta_hours = 5.5

            st.write(
                f"Forecast for {day_ahead_hours} oclock the day before "
                f"with {day_ahead_timezone_delta_hours} hour timezone delta"
            )
        else:
            day_ahead_hours = None
            day_ahead_timezone_delta_hours = None

        # an option to resample to the data
        resample = st.sidebar.selectbox("Resample data", [None, "15T", "30T"], None)

        st.write(
            "Forecast for",
            site_selection_uuid,
            " - `",
            site_client_site_name,
            "`, starting on",
            starttime,
            "created by",
            created,
            "ended on",
            endtime,
        )

        # change date to datetime
        starttime = datetime.combine(starttime, time.min)
        endtime = datetime.combine(endtime, time.min)

        # change to the correct timezone
        # starttime = starttime.replace(tzinfo=timezone_selected)
        # endtime = endtime.replace(tzinfo=timezone_selected)
        starttime = timezone_selected.localize(starttime)
        endtime = timezone_selected.localize(endtime)

        # change to utc
        starttime = starttime.astimezone(pytz.utc)
        endtime = endtime.astimezone(pytz.utc)

        if created is not None:
            created = timezone_selected.localize(created)
            created = created.astimezone(pytz.utc)

        # great ml model names for this site

        # get forecast values for selected sites and plot
        # great ml model names for this site
        ml_models = get_models(
            session=session,
            start_datetime=starttime,
            end_datetime=endtime,
            site_uuid=site_selection_uuid,
            forecast_horizon=0,
        )

        if len(ml_models) == 0:

            class Models:
                name = None

            ml_models = [Models()]

        ys = {}
        xs = {}
        for model in ml_models:

            forecasts = get_latest_forecast_values_by_site(
                session=session,
                site_uuids=[site_selection_uuid],
                start_utc=starttime,
                created_by=created,
                created_after=starttime - timedelta(days=2),
                forecast_horizon_minutes=forecast_horizon,
                day_ahead_hours=day_ahead_hours,
                day_ahead_timezone_delta_hours=day_ahead_timezone_delta_hours,
                end_utc=endtime,
                model_name=model.name,
            )
            forecasts = forecasts.values()

            for forecast in forecasts:
                x = [i.start_utc for i in forecast]
                y = [i.forecast_power_kw for i in forecast]

                # convert to timezone
                x = [i.replace(tzinfo=pytz.utc) for i in x]
                x = [i.astimezone(timezone_selected) for i in x]

            ys[model.name] = y
            xs[model.name] = x

        # get generation values for selected sites and plot
        generations = get_pv_generation_by_sites(
            session=session,
            site_uuids=[site_selection_uuid],
            start_utc=starttime,
            end_utc=endtime,
        )

        yy = [
            generation.generation_power_kw
            for generation in generations
            if generation is not None
        ]
        xx = [
            generation.start_utc for generation in generations if generation is not None
        ]

        # convert to timezone
        xx = [i.replace(tzinfo=pytz.utc) for i in xx]
        xx = [i.astimezone(timezone_selected) for i in xx]

    df_forecast = []
    for model in ml_models:
        name = model.name
        if len(df_forecast) == 0:
            df_forecast = pd.DataFrame(
                {"forecast_datetime": xs[name], f"forecast_power_kw_{name}": ys[name]}
            )
        else:
            temp = pd.DataFrame(
                {"forecast_datetime": xs[name], f"forecast_power_kw_{name}": ys[name]}
            )
            df_forecast = df_forecast.merge(temp, on="forecast_datetime", how="outer")
    if len(ml_models) == 0:
        df_forecast = pd.DataFrame(columns=["forecast_datetime"])
    df_generation = pd.DataFrame({"generation_datetime": xx, "generation_power_kw": yy})
    df_forecast.set_index("forecast_datetime", inplace=True)
    df_generation.set_index("generation_datetime", inplace=True)

    if resample is not None:
        df_forecast = df_forecast.resample(resample).mean()
        df_generation = df_generation.resample(resample).mean()

        # merge together
        df_all = df_forecast.merge(
            df_generation, left_index=True, right_index=True, how="outer"
        )

        # select variables
        xx = df_all.index
        yy = df_all["generation_power_kw"]

    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Latest Forecast for Selected Site"),
            xaxis=go.layout.XAxis(
                title=go.layout.xaxis.Title(text=f"Time [{timezone_selected}]")
            ),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="KW")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    for model in ml_models:
        name = model.name
        fig.add_trace(
            go.Scatter(
                x=df_forecast.index,
                y=df_forecast[f"forecast_power_kw_{name}"],
                mode="lines",
                name=f"forecast_{name}",
                # line=dict(color="#4c9a8e"),
            )
        )
    fig.add_trace(
        go.Scatter(
            x=xx,
            y=yy,
            mode="lines",
            name="generation",
            line=dict(color="#FF9736"),
        )
    )

    st.plotly_chart(fig, theme="streamlit")

    # download data,
    @st.cache_data
    def convert_df(df: pd.DataFrame):
        # IMPORTANT: Cache the conversion to prevent computation on every rerun
        return df.to_csv().encode("utf-8")

    # join data together
    if resample is not None:
        df = df_all
    else:
        df = pd.concat([df_forecast, df_generation], axis=1)
    csv = convert_df(df)
    now = datetime.now().isoformat()

    if resample is None:
        st.caption("Please resample to '15T' to get MAE")
    else:
        metrics = []
        for model in ml_models:
            name = model.name
            forecast_column = f"forecast_power_kw_{name}"

            # MAE and NMAE Calculator
            mae_kw = (df["generation_power_kw"] - df[forecast_column]).abs().mean()
            mae_mw = (
                df["generation_power_kw"] - df[forecast_column]
            ).abs().mean() / 1000
            me_kw = (df["generation_power_kw"] - df[forecast_column]).mean()
            mean_generation = df["generation_power_kw"].mean()
            nmae = mae_kw / mean_generation * 100
            nma2 = (df["generation_power_kw"] - df[forecast_column]).abs()
            gen = df["generation_power_kw"].clip(0)
            nmae2 = nma2 / gen * 100
            nmae2_mean = nmae2[nmae2 != np.inf].mean()
            nmae_capacity = mae_kw / capacity * 100
            pearson_corr = df["generation_power_kw"].corr(df[forecast_column])

            one_metric_data = {
                "model_name": name,
                "mae_mw": mae_mw,
                "mae_kw": mae_kw,
                "me_kw": me_kw,
                "nmae_mean [%]": nmae,
                "nmae_live_gen [%]": nmae2_mean,
                "nmae_capacity [%]": nmae_capacity,
                "mean_generation": mean_generation,
                "capacity": capacity,
                "pearson_corr": pearson_corr,
            }

            if country == "india":
                df["forecast_power_kw"] = df[forecast_column]
                penalties, total_penalty = calculate_penalty(
                    df, str(region), str(asset_type), capacity_kw
                )
                one_metric_data["total_penalty [INR]"] = int(total_penalty)

            metrics.append(one_metric_data)

        metrics = pd.DataFrame(metrics)

        # round all columns to 3 decimal places
        metrics = metrics.round(3)

        # model name is None change to "None"
        metrics["model_name"] = metrics["model_name"].fillna("None")

        # make mode_name the columns by pivoting, and make the index the other columns
        value_columns = one_metric_data.keys()
        value_columns = [i for i in value_columns if i != "model_name"]
        metrics = metrics.pivot_table(
            values=value_columns,
            columns="model_name",
        )

        # show metrics in a table
        st.write(metrics)

        st.caption(f"NMAE_mean is calculated by MAE / (mean generation)")
        st.caption(f"NMAE_live_gen is calculated by current generation (kw)")
        st.caption(f"NMAE_capacity is calculated by generation capacity (mw)")

    # CSV download button
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f"site_forecast_{site_selection_uuid}_{now}.csv",
        mime="text/csv",
    )

    # Add error metrics visualization - daily averages for selected time frame
    st.subheader("Daily Average Error Metrics")

    # Check if resampling is applied - if not, show a clear message
    if resample is None:
        st.warning("Please select a resample option (e.g., '15T') in the sidebar to view error metrics. Without resampling, error metrics cannot be calculated properly.")
    else:
        # Create time series of error metrics for each model
        error_dfs = {}
        for model in ml_models:
            name = model.name
            forecast_column = f"forecast_power_kw_{name}"
            
            # Skip if forecast column doesn't exist or name is None
            if forecast_column not in df.columns or name is None:
                continue
            
            # Calculate model-specific metrics - these are used within this loop iteration
            model_mean_generation = df["generation_power_kw"].mean()
            
            # Create time series of errors
            error_df = pd.DataFrame(index=df.index)
            # Create date column for daily aggregation
            error_df["date"] = error_df.index.date
            
            # Error = generation - forecast
            error_df["error_kw"] = df["generation_power_kw"] - df[forecast_column]
            # Absolute error = |error|
            error_df["abs_error_kw"] = error_df["error_kw"].abs()
            
            # NMAE (% of mean generation) - use model_mean_generation calculated above
            if model_mean_generation > 0:
                error_df["nmae_mean"] = error_df["abs_error_kw"] / model_mean_generation * 100
            else:
                error_df["nmae_mean"] = np.nan
            
            # NMAE (% of capacity)
            if capacity > 0:
                error_df["nmae_capacity"] = error_df["abs_error_kw"] / capacity * 100
            else:
                error_df["nmae_capacity"] = np.nan
            
            # NMAE (% of live generation)
            gen = df["generation_power_kw"].clip(0.1)  # Avoid division by zero
            error_df["nmae_live_gen"] = error_df["abs_error_kw"] / gen * 100
            
            # If in India, add penalties
            if country == "india":
                # Calculate penalty for this specific model
                df_copy = df.copy()
                df_copy["forecast_power_kw"] = df_copy[forecast_column]
                penalties, _ = calculate_penalty(df_copy, str(region), str(asset_type), capacity_kw)
                error_df["penalty"] = penalties
            
            # Group by date and calculate daily averages
            daily_error = error_df.groupby("date").mean()
            
            # Store the daily errors for this model
            error_dfs[name] = daily_error

        # Create visualizations - only if we have valid data
        if error_dfs:
            # 1. Daily MAE Plot (corresponds to mae_kw in metrics table)
            fig_mae = go.Figure()
            for model_name, error_df in error_dfs.items():
                # Check if the model name and data are valid
                if model_name is not None and not error_df.empty:
                    fig_mae.add_trace(
                        go.Scatter(
                            x=error_df.index,
                            y=error_df["abs_error_kw"],
                            mode="lines+markers",
                            name=f"{model_name}",
                            marker=dict(size=8)
                        )
                    )
            
            # Only show chart if we added traces
            if len(fig_mae.data) > 0:
                fig_mae.update_layout(
                    title="Daily Average MAE",
                    xaxis_title="Date",
                    yaxis_title="MAE (kW)"
                )
                st.plotly_chart(fig_mae, theme="streamlit")
            
            # 2. Daily ME Plot (corresponds to me_kw in metrics table)
            fig_me = go.Figure()
            for model_name, error_df in error_dfs.items():
                if model_name is not None and not error_df.empty:
                    fig_me.add_trace(
                        go.Scatter(
                            x=error_df.index,
                            y=error_df["error_kw"],
                            mode="lines+markers",
                            name=f"{model_name}",
                            marker=dict(size=8)
                        )
                    )
            
            if len(fig_me.data) > 0:
                fig_me.update_layout(
                    title="Daily Average ME (+ means overforecast, - means underforecast)",
                    xaxis_title="Date",
                    yaxis_title="ME (kW)"
                )
                st.plotly_chart(fig_me, theme="streamlit")
            
            # 3. Daily NMAE Mean Plot (corresponds to nmae_mean [%] in metrics table)
            fig_nmae_mean = go.Figure()
            for model_name, error_df in error_dfs.items():
                if model_name is not None and not error_df.empty and "nmae_mean" in error_df.columns:
                    fig_nmae_mean.add_trace(
                        go.Scatter(
                            x=error_df.index,
                            y=error_df["nmae_mean"],
                            mode="lines+markers",
                            name=f"{model_name}",
                            marker=dict(size=8)
                        )
                    )
            
            if len(fig_nmae_mean.data) > 0:
                fig_nmae_mean.update_layout(
                    title="Daily Average NMAE (% of Mean Generation)",
                    xaxis_title="Date",
                    yaxis_title="NMAE Mean (%)"
                )
                st.plotly_chart(fig_nmae_mean, theme="streamlit")
            
            # 4. Daily NMAE Capacity Plot (corresponds to nmae_capacity [%] in metrics table)
            fig_nmae_cap = go.Figure()
            for model_name, error_df in error_dfs.items():
                if model_name is not None and not error_df.empty and "nmae_capacity" in error_df.columns:
                    fig_nmae_cap.add_trace(
                        go.Scatter(
                            x=error_df.index,
                            y=error_df["nmae_capacity"],
                            mode="lines+markers",
                            name=f"{model_name}",
                            marker=dict(size=8)
                        )
                    )
            
            if len(fig_nmae_cap.data) > 0:
                fig_nmae_cap.update_layout(
                    title="Daily Average NMAE (% of Capacity)",
                    xaxis_title="Date",
                    yaxis_title="NMAE Capacity (%)"
                )
                st.plotly_chart(fig_nmae_cap, theme="streamlit")
            
            # 5. Daily NMAE Live Gen Plot (corresponds to nmae_live_gen [%] in metrics table)
            fig_nmae_live = go.Figure()
            for model_name, error_df in error_dfs.items():
                if model_name is not None and not error_df.empty and "nmae_live_gen" in error_df.columns:
                    fig_nmae_live.add_trace(
                        go.Scatter(
                            x=error_df.index,
                            y=error_df["nmae_live_gen"],
                            mode="lines+markers",
                            name=f"{model_name}",
                            marker=dict(size=8)
                        )
                    )
            
            if len(fig_nmae_live.data) > 0:
                fig_nmae_live.update_layout(
                    title="Daily Average NMAE (% of Live Generation)",
                    xaxis_title="Date",
                    yaxis_title="NMAE Live Gen (%)"
                )
                st.plotly_chart(fig_nmae_live, theme="streamlit")
            
            # 6. Daily Penalty Plot (for India only)
            if country == "india":
                fig_penalty = go.Figure()
                has_penalty_data = False
                
                for model_name, error_df in error_dfs.items():
                    if model_name is not None and not error_df.empty and "penalty" in error_df.columns:
                        has_penalty_data = True
                        fig_penalty.add_trace(
                            go.Scatter(
                                x=error_df.index,
                                y=error_df["penalty"],
                                mode="lines+markers",
                                name=f"{model_name}",
                                marker=dict(size=8)
                            )
                        )
                
                if has_penalty_data:
                    fig_penalty.update_layout(
                        title="Daily Average Penalty",
                        xaxis_title="Date",
                        yaxis_title="Penalty (INR)"
                    )
                    st.plotly_chart(fig_penalty, theme="streamlit")
            
            # Option to download daily error metrics
            daily_metrics_combined = pd.DataFrame()
            
            for model_name, error_df in error_dfs.items():
                if model_name is not None and not error_df.empty:
                    model_daily = error_df.copy()
                    # Rename columns to include model name
                    renamed_cols = {col: f"{col}_{model_name}" for col in model_daily.columns 
                                if col != 'date'}
                    model_daily = model_daily.rename(columns=renamed_cols)
                    
                    if daily_metrics_combined.empty:
                        daily_metrics_combined = model_daily
                    else:
                        daily_metrics_combined = daily_metrics_combined.join(model_daily, how='outer')
            
            if not daily_metrics_combined.empty:
                daily_csv = convert_df(daily_metrics_combined.reset_index())
                
                st.download_button(
                    label="Download daily error metrics as CSV",
                    data=daily_csv,
                    file_name=f"daily_error_metrics_{site_selection_uuid}_{now}.csv",
                    mime="text/csv",
                )
        else:
            st.info("No valid data available for error metrics visualization. Please check if your selected time range contains both forecast and generation data.")