from typing import Callable
import pandas as pd
from datetime import datetime, date, timedelta
from plotly import graph_objects as go
import streamlit as st

def fetch_forecast_data(api_func: Callable, start_date: datetime, end_date: datetime, process_type: str) -> pd.DataFrame:
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
            solar_df = solar_df.resample("30T")["quantity"].sum().reset_index()

        return solar_df
    except Exception as e:
        st.error(f"Error fetching data for process type '{process_type}': {e}")
        return pd.DataFrame()

def determine_start_and_end_datetimes(start_datetimes, end_datetimes):
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
        end_datetime_utc = start_datetime_utc + timedelta(days=7)

    # Ensure end_datetime_utc is a datetime object
    if isinstance(end_datetime_utc, date) and not isinstance(end_datetime_utc, datetime):
        end_datetime_utc = datetime.combine(end_datetime_utc, datetime.min.time())

    # Assert that start is before end
    assert start_datetime_utc < end_datetime_utc, "Start datetime must be before end datetime."

    return start_datetime_utc, end_datetime_utc