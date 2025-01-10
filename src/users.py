import os
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from nowcasting_datamodel.connection import DatabaseConnection
from pvsite_datamodel.connection import DatabaseConnection as SitesDatabaseConnection

from nowcasting_datamodel.read.read_user import (
    get_all_last_api_request,
    get_api_requests_for_one_user,
)
from pvsite_datamodel.read.user import get_all_last_api_request as get_all_last_api_request_sites
from pvsite_datamodel.read.user import (
    get_api_requests_for_one_user as get_api_requests_for_one_user_sites,
)

from plots.users import make_api_requests_plot, make_api_frequency_requests_plot

region = os.getenv("REGION", "uk")

# Simplified dictionary for API request functions based on region
get_all_last_api_request_dict = {
    "uk": {
        "National": get_all_last_api_request,
        "Sites": get_all_last_api_request_sites
    },
    "default": {
        "Sites": get_all_last_api_request_sites
    }
}[region] if region == 'uk' else get_all_last_api_request_dict["default"]

def user_page():
    """
    Streamlit page to display API user statistics and request details
    """
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"API Users Page"}</h1>',
        unsafe_allow_html=True,
    )

    st.text("See which users have been using the API")

    # Date range selection with reasonable defaults
    start_time = st.sidebar.date_input(
        "Start Date",
        min_value=datetime.today() - timedelta(days=365),
        max_value=datetime.today(),
        value=datetime.today() - timedelta(days=31),
    )
    end_time = st.sidebar.date_input(
        "End Date",
        min_value=datetime.today() - timedelta(days=365),
        max_value=datetime.today() + timedelta(days=1),
        value=datetime.today() + timedelta(days=1),
    )

    # Database connection setup
    db_url = os.getenv("DB_URL", None)
    db_url_sites = os.getenv("SITES_DB_URL", None)

    # Database selection logic
    if region == 'uk':
        national_or_sites = st.sidebar.selectbox("Select", ["National", "Sites"], index=0)
    else:
        national_or_sites = "Sites"

    # Choose appropriate connection and request functions
    connection = (
        DatabaseConnection(url=db_url, echo=True) if national_or_sites == "National" 
        else SitesDatabaseConnection(url=db_url_sites, echo=True)
    )
    get_api_requests_for_one_user_func = (
        get_api_requests_for_one_user if national_or_sites == "National"
        else get_api_requests_for_one_user_sites
    )

    # Get last API requests
    last_request = get_last_request_by_user(_connection=connection, national_or_sites=national_or_sites)

    # Process and display last requests
    last_request = pd.DataFrame(last_request, columns=["email", "last API request"])
    last_request = last_request.sort_values(by="last API request", ascending=False)
    last_request.set_index("email", inplace=True)

    st.write(last_request)

    # User selection
    email_selected = st.sidebar.selectbox("Select User", last_request.index.tolist(), index=0)

    # Fetch API requests for selected user
    with connection.get_session() as session:
        api_requests_sql = get_api_requests_for_one_user_func(
            session=session, 
            email=email_selected, 
            start_datetime=start_time, 
            end_datetime=end_time
        )

        # Transform SQL requests to DataFrame
        api_requests = [
            (api_request_sql.created_utc, api_request_sql.url)
            for api_request_sql in api_requests_sql
        ]
    
    api_requests = pd.DataFrame(api_requests, columns=["created_utc", "url"])

    # Plot individual API requests
    fig = make_api_requests_plot(api_requests, email_selected, end_time, start_time)
    st.plotly_chart(fig, theme="streamlit")

    # Plot API request frequency
    api_requests["created_utc"] = pd.to_datetime(api_requests["created_utc"])
    api_requests["date"] = api_requests["created_utc"].dt.date
    api_requests_days = api_requests[["date", "url"]].groupby("date").count()
    api_requests_days.reset_index(inplace=True)

    fig = make_api_frequency_requests_plot(api_requests_days, email_selected, end_time, start_time)
    st.plotly_chart(fig, theme="streamlit")


@st.cache_data(ttl=60)
def get_last_request_by_user(_connection, national_or_sites:str):
    """
    Get the last request by user with 1-minute cache

    Args:
        _connection: Database connection
        national_or_sites: Source of API requests ('National' or 'Sites')

    Returns:
        List of tuples with user email and last request timestamp
    """
    _get_all_last_api_request_func = get_all_last_api_request_dict[national_or_sites]

    with _connection.get_session() as session:
        last_requests_sql = _get_all_last_api_request_func(session=session)

        last_request = [
            (last_request_sql.user.email, last_request_sql.created_utc)
            for last_request_sql in last_requests_sql
        ]
    return last_request
