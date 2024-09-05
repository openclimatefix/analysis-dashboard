import streamlit as st
import pandas as pd
import plotly.express as px
from herbie import FastHerbie
from datetime import datetime, timedelta, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor

@st.cache_data(show_spinner=False)
def fetch_data_for_init_time(init_time, forecast_date, lat, lon, parameter, model="ifs"):
    # Adjust the initialization datetime based on the init_time offset in hours
    init_datetime = forecast_date - timedelta(hours=init_time)  # This will be a datetime object

    FH = FastHerbie([init_datetime], model=model, fxx=range(0, 24, 1), fast=True)

    try:
        FH.download()  # Ensure the file is downloaded
    except Exception as e:
        st.error(f"Failed to download data for initialization time {init_datetime}. Error: {e}")
        return None, None

    variable_subset = ":10[u|v]" if parameter == "u10:v10" else ":100[u|v]" if parameter == "u100:v100" else "2t"

    try:
        ds = FH.xarray(variable_subset, remove_grib=False)
        if isinstance(ds, list):
            ds = ds[0]
    except EOFError as e:
        st.error(f"Failed to read data file for {init_datetime}. Error: {e}")
        return None, None
    except Exception as e:
        st.error(f"An unexpected error occurred while reading data: {e}")
        return None, None

    return ds, init_datetime

def process_initialization(init_time, forecast_date, lat, lon, parameter, model="ifs"):
    ds, init_datetime = fetch_data_for_init_time(init_time, forecast_date, lat, lon, parameter, model)
    if ds is None:
        return []

    interpolated_data = []

    time_dim = ds['step'] if 'step' in ds.dims else ds['time'] if 'time' in ds.dims else None
    if time_dim is None:
        st.error("Neither 'step' nor 'time' dimension is present in the dataset. Unable to proceed with forecast.")
        return []

    for time_val in time_dim:
        actual_forecast_time = init_datetime + pd.to_timedelta(time_val.values)
        if actual_forecast_time.date() == forecast_date.date():
            if parameter == "u10:v10":
                u = ds['u10'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val)
                v = ds['v10'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val)
                value = np.sqrt(u**2 + v**2)
            elif parameter == "u100:v100":
                u = ds['u100'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val)
                v = ds['v100'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val)
                value = np.sqrt(u**2 + v**2)
            else:  # temp
                value = ds['t2m'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val) - 273.15

            interpolated_data.append({
                'date_time': actual_forecast_time,
                'latitude': lat,
                'longitude': lon,
                'value': value.compute().item(),
                'init_time': f"{init_time} hours before"
            })

    return interpolated_data

def get_forecast(forecast_date, lat, lon, parameter, init_times, model="ifs"):
    all_data = []
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda init_time: process_initialization(init_time, forecast_date, lat, lon, parameter, model), init_times))
    for result in results:
        all_data.extend(result)
    return pd.DataFrame(all_data)

def weather_forecast_page():
    # Streamlit app
    st.title("Weather Forecasts from Different Initialization Times")

    parameter_mapping = {
        "Wind Speed (10m)": "u10:v10",
        "Wind Speed (100m)": "u100:v100",
        "Temperature": "2t"
    }

    parameter_option = st.sidebar.selectbox("Select Parameter", options=list(parameter_mapping.keys()))
    parameter_value = parameter_mapping[parameter_option]
    lat = st.sidebar.number_input("Enter Latitude", value=27.035, format="%.6f")
    lon = st.sidebar.number_input("Enter Longitude", value=70.515, format="%.6f")

    # Use datetime.combine to set the forecast_date to midnight
    forecast_date = st.sidebar.date_input("Select Forecast Date", datetime.today().date())
    forecast_date = datetime.combine(forecast_date, time(hour=0))

    # Multiselect for initialization times in hours
    init_time_options = st.sidebar.multiselect(
        "Select Initialization Times (in hours before forecast date)",
        options=[24, 18, 12, 6, 0],
        default=[24, 12, 0]  # Default selections: 24 hours before, 12 hours before, and current day
    )

    if st.button("Fetch Data"):
        if not init_time_options:
            st.warning("Please select at least one initialization time.")
        else:
            st.write("Note: Data loading may take up to 30 seconds. Please be patient...")
            data = get_forecast(forecast_date, lat, lon, parameter_value, init_times=init_time_options )

            if not data.empty:
                fig = px.line(
                    data,
                    x='date_time',
                    y='value',
                    color='init_time',
                    labels={
                        'date_time': 'Date and Time',
                        'value': f'{parameter_option} ({"m/s" if "Wind Speed" in parameter_option else "°C"})',
                        'init_time': 'Initialization Time'
                    },
                    title=f"Forecast of {parameter_option} at ({lat}, {lon}) for {forecast_date.strftime('%Y-%m-%d')}"
                )
                st.plotly_chart(fig)

                csv = data.to_csv(index=False)
                file_name = f"{forecast_date.strftime('%Y-%m-%d')}_{parameter_option}_comparison_data.csv"
                st.download_button(label="Download data as CSV", data=csv, file_name=file_name, mime='text/csv')
            else:
                st.warning("No data was collected.")
