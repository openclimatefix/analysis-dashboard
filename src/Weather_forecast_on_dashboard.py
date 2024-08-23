import streamlit as st
import pandas as pd
import plotly.express as px
from herbie import FastHerbie
from datetime import datetime, timedelta
import numpy as np
import os

# Define the points with the provided coordinates and create a human-readable location column
points = pd.DataFrame(
    {
        "latitude": [
            27.035, 27.188, 27.085, 27.055, 27.186, 27.138, 26.97, 26.898,
            26.806, 26.706, 26.698, 26.708, 26.679, 26.8, 26.704, 26.5,
            26.566, 26.679, 26.201, 26.501, 26.463, 26.718, 26.63, 24.142,
            23.956, 23.657
        ],
        "longitude": [
            70.515, 70.661, 70.638, 70.72, 70.81, 71.024, 70.917, 70.99599,
            70.732, 70.81, 70.875, 70.982, 71.027, 71.128, 71.12699, 71.285,
            71.369, 71.452, 71.295, 72.512, 72.836, 73.049, 73.581, 74.73099,
            74.625, 74.772
        ],
        "stid": [
            "aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh", "ii", "jj", "kk", "ll",
            "mm", "nn", "oo", "pp", "qq", "rr", "ss", "tt", "uu", "vv", "ww", "xx", "yy", "zz"
        ]
    }
)

# Add a location column for human-readable representation
points["location"] = points["latitude"].astype(str) + ", " + points["longitude"].astype(str)

# Function to get weather data based on the selected parameter
def get_weather_data(date_time, points, parameter):
    try:
        FH = FastHerbie([date_time], model="ifs", fxx=range(0, 12, 3), fast=True)
        FH.download()  # Ensure the file is downloaded

        variable_subset = ":10[u|v]" if parameter == "u10:v10" else ":100[u|v]" if parameter == "u100:v100" else "2t"
        ds = FH.xarray(variable_subset, remove_grib=False)
        if isinstance(ds, list):
            ds = ds[0]

        interpolated_data = []
        for i, row in points.iterrows():
            lat = row['latitude']
            lon = row['longitude']
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
                    'location': row['location'],
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

# Sidebar for site selection
site_option = st.sidebar.selectbox(
    "Select Site",
    options=["All Sites", "Mean of All Sites"] + points["location"].tolist()
)

# Input date range
start_date = st.date_input("Select start date", datetime(2024, 7, 20))
end_date = st.date_input("Select end date", start_date + timedelta(days=1))

# Fetch data button
if st.button("Fetch Data"):
    date_range = pd.date_range(start=start_date, end=end_date, freq="6h")

    all_data = []
    for current_date in date_range:
        data = get_weather_data(current_date, points, parameter_value)
        if not data.empty:
            all_data.append(data)

    if all_data:
        final_data = pd.concat(all_data, ignore_index=True)

        if site_option == "Mean of All Sites":
            # Calculate the mean value across all sites
            mean_data = final_data.groupby('date_time')['value'].mean().reset_index()
            mean_data['location'] = 'Mean of All Sites'

            # Plot: Mean value over time
            fig = px.line(
                mean_data,
                x='date_time',
                y='value',
                labels={
                    'date_time': 'Date and Time',
                    'value': f'Mean {parameter_option} ({"m/s" if "Wind Speed" in parameter_option else "°C"})',
                    'location': 'Location'
                },
                title=f"Mean {parameter_option} Over Time"
            )
            st.plotly_chart(fig)

        else:
            # Filter data by selected location
            if site_option != "All Sites":
                final_data = final_data[final_data['location'] == site_option]

            # Plot: Value over time
            fig = px.line(
                final_data,
                x='date_time',
                y='value',
                color='location' if site_option == "All Sites" else None,
                labels={
                    'date_time': 'Date and Time',
                    'value': f'{parameter_option} ({"m/s" if "Wind Speed" in parameter_option else "°C"})',
                    'location': 'Location'
                },
                title=f"{parameter_option} Over Time for {'All Sites' if site_option == 'All Sites' else site_option}"
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
