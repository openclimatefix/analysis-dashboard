from unittest.mock import Mock, patch
import pandas as pd
import pytest
from datetime import datetime
from plotly import graph_objects as go
from plots.elexon_plots import  add_elexon_plot, determine_start_and_end_datetimes, fetch_forecast_data
from elexonpy.api_client import ApiClient
from elexonpy.api.generation_forecast_api import GenerationForecastApi

def test_determine_start_and_end_datetimes_no_input():
    # Test with no input
    now = datetime.utcnow()
    start, end = determine_start_and_end_datetimes([], [])
    assert start < now, "Start time should be before current time."
    assert end > start, "End time should be after start time."

def test_determine_start_and_end_datetimes_with_start_only():
    start_date = datetime(2024, 8, 1)
    start, end = determine_start_and_end_datetimes([start_date], [])
    assert start == start_date, "Start time should match provided start_date."
    assert end > start, "End time should be 7 days after the start time."

def test_determine_start_and_end_datetimes_with_invalid_dates():
    with pytest.raises(AssertionError):
        determine_start_and_end_datetimes([datetime(2024, 8, 10)], [datetime(2024, 8, 5)])

def test_fetch_forecast_data_empty_response():
    # Mock the API function to return an empty response
    mock_api_func = Mock()
    mock_api_func.return_value.data = []

    result = fetch_forecast_data(mock_api_func, datetime(2024, 8, 1), datetime(2024, 8, 2), "Day Ahead")
    assert result.empty, "Result should be an empty DataFrame"

def test_fetch_forecast_data_api_failure():
    # Mock the API function to raise an exception
    mock_api_func = Mock(side_effect=Exception("API failure"))

    result = fetch_forecast_data(mock_api_func, datetime(2024, 8, 1), datetime(2024, 8, 2), "Day Ahead")
    assert result.empty, "Result should be an empty DataFrame in case of an API failure"

@patch('plots.elexon_plots.fetch_forecast_data')
def test_add_elexon_plot_with_data(mock_fetch):
    # Mock fetch_forecast_data to return a non-empty DataFrame
    mock_fetch.return_value = pd.DataFrame({
        "start_time": pd.date_range("2024-08-01", periods=3, freq="30T"),
        "quantity": [100, 200, 150]
    })

    # Create an empty Plotly figure
    fig = go.Figure()

    start_datetime = [datetime(2024, 8, 1)]
    end_datetime = [datetime(2024, 8, 2)]
    updated_fig = add_elexon_plot(fig, start_datetime, end_datetime)

    # Assert
    assert len(updated_fig.data) > 0, "Figure should have traces added"
    assert updated_fig.data[0].name.startswith("Elexon"), "Trace should be labeled as Elexon"
    assert updated_fig.data[0].line.dash == "solid", "Line style should be solid for the first trace"

@patch('plots.elexon_plots.fetch_forecast_data')
def test_add_elexon_plot_no_data(mock_fetch):
    # Mock fetch_forecast_data to return an empty DataFrame
    mock_fetch.return_value = pd.DataFrame()

    # Create an empty Plotly figure
    fig = go.Figure()
    start_datetime = [datetime(2024, 8, 1)]
    end_datetime = [datetime(2024, 8, 2)]
    updated_fig = add_elexon_plot(fig, start_datetime, end_datetime)

    # Assert
    assert len(updated_fig.data) == 0, "Figure should have no traces added if no data is available"

@pytest.mark.integration
def test_fetch_forecast_data_integration():
    # Initialize the actual API client and the function to be tested
    api_client = ApiClient()
    forecast_api = GenerationForecastApi(api_client)
    forecast_generation_wind_and_solar_day_ahead_get = forecast_api.forecast_generation_wind_and_solar_day_ahead_get

    # Define the start and end date for fetching the data
    start_date = datetime(2024, 8, 1)
    end_date = datetime(2024, 8, 2)

    # Call the function with real data
    result = fetch_forecast_data(forecast_generation_wind_and_solar_day_ahead_get, start_date, end_date, "Day Ahead")

    # Assertions to check the returned DataFrame
    assert isinstance(result, pd.DataFrame), "Result should be a DataFrame"

    # If data exists for the given dates, the DataFrame shouldn't be empty
    if not result.empty:
        assert "start_time" in result.columns, "DataFrame should contain 'start_time' column"
        assert result["quantity"].notna().all(), "Quantity values should not be NaN"
    else:
        # If the DataFrame is empty, it indicates no data was returned for the given date range
        print("No data returned for the given date range.")