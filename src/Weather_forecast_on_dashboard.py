import streamlit as st
import pandas as pd
import plotly.express as px
from herbie import FastHerbie
from datetime import datetime, timedelta
import numpy as np
import os

# Function to get weather data based on the selected parameter and user input lat/lon
def get_weather_data(date_time, lat, lon, parameter):
    try:
        FH = FastHerbie([date_time], model="ifs", fxx=range(0, 12, 3), fast=True)
        FH.download()  # Ensure the file is downloaded

        variable_subset = ":10[u|v]" if parameter == "u10:v10" else ":100[u|v]" if parameter == "u100:v100" else "2t"
        ds = FH.xarray(variable_subset, remove_grib=False)
        if isinstance(ds, list):
            ds = ds[0]

        interpolated_data = []
        for step in ds.step:
            if parameter == "u10:v10":
                u = ds['u10'].interp(latitude=lat, longitude=lon, method="nearest", step=step).values
                v = ds['v10'].interp(latitude=lat, longitude=lon, method="nearest", step=step).values
                value = np.sqrt(u**2 + v**2)  # Calculate wind speed at 10m
            elif parameter == "u100:v100":
                u = ds['u100'].interp(latitude=lat, longitude=lon, method="nearest", step=step).values
                v = ds['v100'].interp(latitude=lat, longitude=lon, method="nearest", step=step).values
                value = np.sqrt(u**2 + v**2)  # Calculate wind speed at 100m
            else:  # temp
                value = ds['t2m'].interp(latitude=lat, longitude=lon, method="nearest", step=step).values - 273.15  # Convert temperature from Kelvin to Celsius

            interpolated_data.append({
                'date_time': date_time + step.values,
                'latitude': lat,
                'longitude': lon,
                'value': value
            })

        return pd.DataFrame(interpolated_data)
    except FileNotFoundError as fnf_error:
        st.error(f"File not found: {fnf_error}")
        st.warning(f"Check if the model data is available for {date_time}. Ensure the directory '{os.path.dirname(fnf_error.filename)}' exists.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error processing data for {date_time}: {e}")
        return pd.DataFrame()

# Streamlit app
st.title("Weather Data Visualization")

# Dropdown menu mapping user-friendly names to internal parameters
parameter_mapping = {
    "Wind Speed (10m)": "u10:v10",
    "Wind Speed (100m)": "u100:v100",
    "Temperature": "2t"
}

# Sidebar for parameter selection
parameter_option = st.sidebar.selectbox(
    "Select Parameter",
    options=list(parameter_mapping.keys())  # Display user-friendly names
)

# Get the actual parameter value to use in the Herbie function
parameter_value = parameter_mapping[parameter_option]

# Input fields for user to enter latitude and longitude
lat = st.number_input("Enter Latitude", value=27.035, format="%.6f")
lon = st.number_input("Enter Longitude", value=70.515, format="%.6f")

# Input date range
start_date = st.date_input("Select start date", datetime(2024, 7, 20))
end_date = st.date_input("Select end date", start_date + timedelta(days=1))

# Fetch data button
if st.button("Fetch Data"):
    date_range = pd.date_range(start=start_date, end=end_date, freq="6h")

    all_data = []
    for current_date in date_range:
        data = get_weather_data(current_date, lat, lon, parameter_value)
        if not data.empty:
            all_data.append(data)

    if all_data:
        final_data = pd.concat(all_data, ignore_index=True)

        # Plot: Value over time
        fig = px.line(
            final_data,
            x='date_time',
            y='value',
            labels={
                'date_time': 'Date and Time',
                'value': f'{parameter_option} ({"m/s" if "Wind Speed" in parameter_option else "°C"})',
                'latitude': 'Latitude',
                'longitude': 'Longitude'
            },
            title=f"{parameter_option} Over Time at ({lat}, {lon})"
        )
        st.plotly_chart(fig)

        # Download as CSV button
        csv = final_data.to_csv(index=False)
        start_datetime_str = start_date.strftime('%Y-%m-%d_%H-%M')
        file_name = f"{start_datetime_str}_{parameter_option}_data.csv"
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name=file_name,
            mime='text/csv',
        )
    else:
        st.warning("No data was collected.")
