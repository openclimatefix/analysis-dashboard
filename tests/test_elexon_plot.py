import pandas as pd
import pytest
from datetime import datetime


from plots.elexon_plots import  determine_start_and_end_datetimes

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
