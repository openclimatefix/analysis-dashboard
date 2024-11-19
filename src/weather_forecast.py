import os
import shutil
import streamlit as st
import pandas as pd
import plotly.express as px
from herbie import FastHerbie
from datetime import datetime, timedelta, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

# Define the Herbie cache directory path
HERBIE_CACHE_DIR = "herbie_cache_directory"

# Function to clear Herbie cache before each run
def clear_herbie_cache(cache_dir: str):
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)  # Remove all contents
    os.makedirs(cache_dir, exist_ok=True)  # Re-create the directory

# Function to compute forecast hours
def compute_forecast_hours(init_time: datetime, forecast_date: datetime) -> range:
    """
    Computes the range of forecast hours based on the delta between the initialization time
    and the forecast date, fetching up to 24 hours from the calculated difference.

    Parameters:
    - init_time (datetime): The initialization time.
    - forecast_date (datetime): The target forecast date.

    Returns:
    - forecast_hours (range): Range of forecast hours to fetch.
    """
    delta_hours = int((forecast_date - init_time).total_seconds() // 3600) # Convert difference to hours
    forecast_hours = range(delta_hours, delta_hours + 24 + 1)  # Fetch up to 24 hours
    #print(delta_hours, init_time, forecast_date )
    return forecast_hours
    

@st.cache_data(show_spinner=False)
def fetch_data_for_init_time(
    init_time: datetime, 
    forecast_date: datetime, 
    lat: float, 
    lon: float, 
    parameter: str, 
    model: str = "ifs"
) -> Tuple[Optional['xarray.Dataset'], Optional[datetime]]:
    # Clear the cache for every new fetch
    clear_herbie_cache(HERBIE_CACHE_DIR)
    
    # Calculate forecast hours
    forecast_hours = compute_forecast_hours(init_time, forecast_date)
    FH = FastHerbie([init_time], model=model, fxx=forecast_hours, cache_dir=HERBIE_CACHE_DIR, fast=True)
    
    try:
        FH.download()  # Ensure the file is downloaded
    except Exception as e:
        st.error(f"Failed to download data for initialization time {init_time}. Error: {e}")
        return None, None

    # Determine the variable subset based on the selected parameter
    variable_subset = ":10[u|v]" if parameter == "u10:v10" else ":100[u|v]" if parameter == "u100:v100" else "2t"

    try:
        ds = FH.xarray(variable_subset, remove_grib=False)
        if isinstance(ds, list):
            ds = ds[0]
    except EOFError as e:
        st.error(f"Failed to read data file for {init_time}. Error: {e}")
        return None, None
    except Exception as e:
        st.error(f"An unexpected error occurred while reading data: {e}")
        return None, None

    return ds, init_time

def process_initialization(
    init_time: datetime, 
    forecast_date: datetime, 
    lat: float, 
    lon: float, 
    parameter: str, 
    model: str = "ifs"
) -> List[dict]:
    """
    Process the weather forecast for a specific initialization time, 
    interpolate data for the given latitude and longitude.

    Parameters:
    - init_time (datetime): The initialization time for the forecast.
    - forecast_date (datetime): The forecast date for which the data is requested.
    - lat (float): Latitude of the location for the forecast.
    - lon (float): Longitude of the location for the forecast.
    - parameter (str): The weather parameter to retrieve (e.g., "u10:v10", "u100:v100", or "2t").
    - model (str): The weather model to use for fetching data (default: "ifs").

    Returns:
    - interpolated_data (list): A list of dictionaries containing forecast values and metadata.
    """
    ds, init_time = fetch_data_for_init_time(init_time, forecast_date, lat, lon, parameter, model)
    if ds is None:
        return []

    interpolated_data = []

    # Determine the time dimension
    time_dim = ds['step'] if 'step' in ds.dims else ds['time'] if 'time' in ds.dims else None
    if time_dim is None:
        st.error("No 'step' or 'time' dimension in dataset.")
        return []

    # Iterate over the forecast steps and interpolate the data
    for time_val in time_dim:
        actual_forecast_time = init_time + pd.to_timedelta(time_val.values)

        # Debugging: Show the actual forecast time to check if the full day is captured
        st.write(f"Forecast time: {actual_forecast_time}")

        if actual_forecast_time.date() == forecast_date.date():
            if parameter == "u10:v10":
                u = ds['u10'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val)
                v = ds['v10'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val)
                value = np.sqrt(u**2 + v**2)
            elif parameter == "u100:v100":
                u = ds['u100'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val)
                v = ds['u100'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val)
                value = np.sqrt(u**2 + v**2)
            else:
                value = ds['t2m'].interp(latitude=lat, longitude=lon, method="nearest", step=time_val) - 273.15

            interpolated_data.append({
                'date_time': actual_forecast_time,
                'latitude': lat,
                'longitude': lon,
                'value': value.compute().item(),
                'init_time': init_time.strftime('%Y-%m-%d %H:%M')
            })

    return interpolated_data

def get_forecast(
    forecast_date: datetime, 
    lat: float, 
    lon: float, 
    parameter: str, 
    init_times: List[datetime], 
    model: str = "ifs"
) -> pd.DataFrame:
    """
    Get the weather forecast data for multiple initialization times.

    Parameters:
    - forecast_date (datetime): The date for which the forecast is requested.
    - lat (float): Latitude of the location for the forecast.
    - lon (float): Longitude of the location for the forecast.
    - parameter (str): The weather parameter to retrieve (e.g., "u10:v10", "u100:v100", or "2t").
    - init_times (list): A list of datetime objects representing initialization times.
    - model (str): The weather model to use for fetching data (default: "ifs").

    Returns:
    - pd.DataFrame: A Pandas DataFrame containing the forecast data for the selected parameters and times.
    """
    all_data = []
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda init_time: process_initialization(init_time, forecast_date, lat, lon, parameter, model), init_times))
    for result in results:
        all_data.extend(result)
    return pd.DataFrame(all_data)

def weather_forecast_page() -> None:
    """
    The main page for displaying weather forecasts with user inputs.

    - Allows users to input latitude and longitude.
    - Select the forecast date.
    - Choose initialization times based on yesterday's forecast generation times.
    - Fetch and display forecast data for the chosen initialization times and location.
    """
    # Streamlit app
    st.title("Weather Forecasts from Different Initialization Times")

    # Parameter selection
    parameter_mapping = {
        "Wind Speed (10m)": "u10:v10",
        "Wind Speed (100m)": "u100:v100",
        "Temperature": "2t"
    }
    parameter_option = st.sidebar.selectbox("Select Parameter", options=list(parameter_mapping.keys()))
    parameter_value = parameter_mapping[parameter_option]

    # Latitude and longitude inputs
    lat = st.sidebar.number_input("Enter Latitude", value=27.035, format="%.6f")
    lon = st.sidebar.number_input("Enter Longitude", value=70.515, format="%.6f")

    # Forecast date selection
    forecast_date = st.sidebar.date_input("Select Forecast Date", datetime.today().date())
    forecast_date = datetime.combine(forecast_date, time(hour=0))

    # Create initialization times for yesterday at 00:00, 06:00, 12:00, and 18:00
    yesterday = forecast_date - timedelta(days=1)
    init_times = [
        yesterday.replace(hour=0)-timedelta(hours=12),
        yesterday.replace(hour=0),
        yesterday.replace(hour=12),
        yesterday.replace(hour=0)+timedelta(hours=24)
    ]

    # Multi-selection for initialization times
    init_time_options = st.sidebar.multiselect(
        "Select Initialization Times",
        options=[time.strftime('%Y-%m-%d %H:%M') for time in init_times],
        default=[time.strftime('%Y-%m-%d %H:%M') for time in init_times]
    )
    selected_init_times = [datetime.strptime(time, '%Y-%m-%d %H:%M') for time in init_time_options]

    # Fetch and display the data
    if st.button("Fetch Data"):
        if not selected_init_times:
            st.warning("Please select at least one initialization time.")
        else:
            st.write("Note: Data loading may take up to 5 minutes. Please be patient...")
            data = get_forecast(forecast_date, lat, lon, parameter_value, selected_init_times, model="ifs")

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

                # Downloadable CSV
                csv = data.to_csv(index=False)
                file_name = f"{forecast_date.strftime('%Y-%m-%d')}_{parameter_option}_comparison_data.csv"
                st.download_button(label="Download data as CSV", data=csv, file_name=file_name, mime='text/csv')
            else:
                st.warning("No data was collected.")
