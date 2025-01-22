import streamlit as st
import json
import requests
from datetime import datetime
import pytz


def load_css(css_file):
    """Load CSS from a file."""
    try:
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found: {css_file}")


def parse_timestamp(status):
    """Parse the timestamp from the status object and return local time"""
    timestamp = str(status.created_utc)
    timestamp = timestamp.replace(" ", "T")  # Replace space with T for ISO 8601
    try:
        parsed_time = datetime.fromisoformat(timestamp)
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {e}")

    if parsed_time.tzinfo is not None:
        utc_time = parsed_time.astimezone(pytz.utc)
    else:
        # If no timezone is specified, assume it's UTC
        utc_time = parsed_time.replace(tzinfo=pytz.utc)

    # Convert to specific timezone (Asia/Kolkata)
    local_timezone = pytz.timezone("Asia/Kolkata")
    local_time = parsed_time.astimezone(local_timezone)

    return local_time


def format_time(local_time):
    """Format date and time"""
    formatted_date = local_time.strftime("%Y-%m-%d")
    formatted_time = local_time.strftime("%H:%M")
    timezone_name = local_time.tzname()
    return formatted_date, formatted_time, timezone_name
