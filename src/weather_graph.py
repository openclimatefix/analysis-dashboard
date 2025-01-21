import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pvsite_datamodel.read.site import get_all_sites, get_site_by_uuid
from pvsite_datamodel.connection import DatabaseConnection
import os

def weather_graph_page():
    st.title("Weather Data Viewer")

    # Database connection to fetch predefined sites
    url = os.environ["SITES_DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)

    # Fetch all sites from the database
    with connection.get_session() as session:
        sites = get_all_sites(session=session)
        site_uuids = [site.site_uuid for site in sites if site.site_uuid is not None]

    # Sidebar toggle to select sites by site_uuid or client_site_name
    query_method = st.sidebar.radio("Select site by", ("site_uuid", "client_site_name"))

    if query_method == "site_uuid":
        site_selection_uuid = st.sidebar.selectbox(
            "Select sites by site_uuid",
            site_uuids,
        )
    else:
        client_site_name = st.sidebar.selectbox(
            "Select sites by client_site_name",
            sorted([site.client_site_name for site in sites])
        )
        site_selection_uuid = [
            site.site_uuid for site in sites if site.client_site_name == client_site_name
        ][0]

    # Fetch site details
    with connection.get_session() as session:
        site = get_site_by_uuid(session, site_selection_uuid)
        latitude = site.latitude
        longitude = site.longitude

    # Select parameters to display
    parameters = st.sidebar.multiselect(
        "Select Parameters", 
        ["Temperature (°C)", "Wind Speed (10m) (m/s)", "Wind Speed (100m) (m/s)", "Cloud Cover (Total)","Direct Normal Irradiance (DNI)"],
        default=["Temperature (°C)"]
    )

    parameter_map = {
        "Temperature (°C)": "temperature_2m",
        "Wind Speed (10m) (m/s)": "wind_speed_10m",
        "Wind Speed (100m) (m/s)": "wind_speed_100m",
        "Direct Normal Irradiance (DNI)": "direct_normal_irradiance",
        "Cloud Cover (Total)": "cloudcover"
    }

    selected_parameters = [parameter_map[param] for param in parameters]

    # Toggle for Historical or Forecast data
    data_type = st.sidebar.radio("Choose Data Type", ("Forecast", "Historical"))

    # Date range input
    start_date = st.sidebar.date_input(
        "Start Date",
        min_value=datetime.today() - timedelta(days=365),
        max_value=datetime.today(),
    )
    end_date = st.sidebar.date_input(
        "End Date",
        value=start_date + timedelta(days=3),
    )

    # Function to fetch weather data
    def fetch_weather_data(latitude, longitude, start_date, end_date, api_url, parameters):
        # API parameters
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(parameters),
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }

        try:
            # Fetch weather data
            response = requests.get(api_url, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()

            # Extract hourly data
            times = data["hourly"]["time"]
            variables = {param: data["hourly"].get(param, []) for param in parameters}

            # Convert times to a readable format
            times = [datetime.strptime(time, '%Y-%m-%dT%H:%M') for time in times]

            return times, variables

        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching weather data: {e}")
            return None, None

    # Fetch data when the user clicks the button
    if st.button("Fetch Weather Data"):
        if data_type == "Historical":
            api_url = "https://archive-api.open-meteo.com/v1/era5"
        else:
            api_url = "https://api.open-meteo.com/v1/forecast"

        times, variables = fetch_weather_data(latitude, longitude, start_date, end_date, api_url, selected_parameters)

        if times and variables:
            # Create the plot using Plotly
            fig = go.Figure()
            for param, values in variables.items():
                fig.add_trace(go.Scatter(x=times, y=values, mode='lines+markers', name=param))

            # Update layout
            fig.update_layout(
                title=f"Weather Data ({start_date} to {end_date})",
                xaxis_title="Time",
                yaxis_title="Values",
                template="plotly_white",
                xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=45),
                yaxis=dict(showgrid=True, gridcolor='lightgray'),
            )

            # Display the plot
            st.plotly_chart(fig)
