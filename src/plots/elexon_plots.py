from typing import Callable, List, Optional, Tuple, Union
import pandas as pd
from datetime import datetime, date, timedelta
from plotly import graph_objects as go
import streamlit as st
from elexonpy.api_client import ApiClient
from elexonpy.api.generation_forecast_api import GenerationForecastApi


def add_elexon_plot(
    fig: go.Figure,
    start_datetimes: List[Optional[datetime]],
    end_datetimes: List[Optional[datetime]],
) -> go.Figure:
    """
    Adds Elexon forecast data to the given Plotly figure.

    Parameters:
    - fig (go.Figure): The Plotly figure to which the Elexon data will be added.
    - start_datetimes (List[Optional[datetime]]): List of start datetimes for the forecast.
    - end_datetimes (List[Optional[datetime]]): List of end datetimes for the forecast.

    Returns:
    - go.Figure: The modified Plotly figure with Elexon data added.
    """
    start_datetime_utc, end_datetime_utc = determine_start_and_end_datetimes(
        start_datetimes, end_datetimes
    )

    if start_datetime_utc and end_datetime_utc:
        # Initialize Elexon API client
        api_client = ApiClient()
        forecast_api = GenerationForecastApi(api_client)
        forecast_generation_wind_and_solar_day_ahead_get = (
            forecast_api.forecast_generation_wind_and_solar_day_ahead_get
        )
        # Fetch data for each process type
        process_types = ["Day Ahead", "Intraday Process", "Intraday Total"]
        line_styles = ["solid", "dash", "dot"]
        forecasts = [
            fetch_forecast_data(
                forecast_generation_wind_and_solar_day_ahead_get,
                start_datetime_utc,
                end_datetime_utc,
                pt,
            )
            for pt in process_types
        ]

        for i, (forecast, line_style) in enumerate(zip(forecasts, line_styles)):
            if forecast.empty:
                continue
            # Remove NaNs and zero values to ensure clean data for plotting
            forecast = forecast[forecast["quantity"].notna() & (forecast["quantity"] > 0)]

            full_time_range = pd.date_range(
                start=start_datetime_utc,
                end=end_datetime_utc,
                freq="30min",
                tz=forecast["start_time"].dt.tz,
            )
            full_time_df = pd.DataFrame(full_time_range, columns=["start_time"])
            forecast = full_time_df.merge(forecast, on="start_time", how="left")

            # Hide all Elexon forecast types by default
            visibility = 'legendonly'

            fig.add_trace(
                go.Scatter(
                    x=forecast["start_time"],
                    y=forecast["quantity"],
                    mode="lines",
                    name=f"Elexon {process_types[i]}",
                    line=dict(color="#318CE7", dash=line_style),
                    connectgaps=False,
                    visible=visibility
                )
            )

    return fig


def fetch_forecast_data(
    api_func: Callable, start_date: datetime, end_date: datetime, process_type: str
) -> pd.DataFrame:
    """
    Fetches forecast data from an API and processes it.

    Parameters:
    api_func (Callable): The API function to call for fetching data.
    start_date (datetime): The start date for the data fetch.
    end_date (datetime): The end date for the data fetch.
    process_type (str): The type of process for which data is being fetched.

    Returns:
    pd.DataFrame: A DataFrame containing the processed solar generation data.
    """
    try:
        response = api_func(
            _from=start_date.isoformat(),
            to=end_date.isoformat(),
            process_type=process_type,
            format="json",
        )
        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame([item.to_dict() for item in response.data])
        solar_df = df[df["business_type"] == "Solar generation"]
        solar_df["start_time"] = pd.to_datetime(solar_df["start_time"])
        solar_df = solar_df.set_index("start_time")

        # Resample if there's data
        if not solar_df.empty:
            solar_df = solar_df.resample("30min")["quantity"].sum().reset_index()

        return solar_df
    except Exception as e:
        st.error(f"Error fetching data for process type '{process_type}': {e}")
        return pd.DataFrame()


def determine_start_and_end_datetimes(
    start_datetimes: List[Union[datetime, date]], end_datetimes: List[Union[datetime, date]]
) -> Tuple[datetime, datetime]:
    """
    Determines the start and end datetime in UTC.
    Parameters:
    - start_datetimes: list of datetime or date objects
    - end_datetimes: list of datetime or date objects
    Returns:
    - start_datetime_utc: datetime object in UTC
    - end_datetime_utc: datetime object in UTC
    """
    now = datetime.utcnow()

    # Determine start_datetime_utc
    if start_datetimes:
        start_datetime_utc = start_datetimes[0]
    else:
        start_datetime_utc = now - timedelta(days=2)
    # Ensure start_datetime_utc is a datetime object
    if isinstance(start_datetime_utc, date) and not isinstance(start_datetime_utc, datetime):
        start_datetime_utc = datetime.combine(start_datetime_utc, datetime.min.time())

    # Determine end_datetime_utc
    if end_datetimes and end_datetimes[-1]:
        end_datetime_utc = end_datetimes[-1]
    else:
        end_datetime_utc = start_datetime_utc + timedelta(days=3)

    # Ensure end_datetime_utc is a datetime object
    if isinstance(end_datetime_utc, date) and not isinstance(end_datetime_utc, datetime):
        end_datetime_utc = datetime.combine(end_datetime_utc, datetime.min.time())

    # Assert that start is before end
    assert start_datetime_utc < end_datetime_utc, "Start datetime must be before end datetime."

    return start_datetime_utc, end_datetime_utc
