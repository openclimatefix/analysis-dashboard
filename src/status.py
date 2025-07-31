import logging
import os

import pandas as pd
import requests
import streamlit as st
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.models import Status
from nowcasting_datamodel.read.read import get_latest_status
from pvsite_datamodel.connection import DatabaseConnection as SitesDatabaseConnection
from pvsite_datamodel.read.status import get_latest_status as get_latest_status_site
from pvsite_datamodel.sqlmodels import StatusSQL

STATUS_API_URL = os.getenv("STATUS_API_URL", "https://status.quartz.energy")

def get_colour(status) -> str:
    """
    Get the colour for the status

    green = ok
    orange = warning
    red = error
    """
    colour = "green"
    if status.status == "warning":
        colour = "orange"
    elif status.status == "error":
        colour = "red"
    return colour


# Region setting to determine which options to show
region = os.getenv("REGION", "uk")


def get_current_status(session, national_or_sites="National"):
    """Get the current status from the database"""
    if national_or_sites == "National":
        status = get_latest_status(session=session)
    else:  # Sites
        status = get_latest_status_site(session=session)

    return status


def display_update_status():
    """Display the update status form"""
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(f"""<div class="label">Select the new status</div>""", unsafe_allow_html=True)
        status_level = st.selectbox(
            "New status?", ("Ok", "Warning", "Error"), label_visibility="collapsed"
        )
    with col2:
        st.markdown(f"""<div class="label">Enter a message</div>""", unsafe_allow_html=True)
        value = st.text_input("Message", label_visibility="collapsed")

    return str(status_level).lower(), value


def write_new_status(session, status, status_level, value, national_or_sites="National"):
    """Write a new status to the database"""

    """Write a new status to the database"""
    if national_or_sites == "National":
        # make a new Pydanitc object, this gets validated
        s = Status(status=status_level, message=value)

        # change to sqlalchemy object
        s = s.to_orm()

        # bumpy the id
        s.id = status.id + 1
    else:
        s = StatusSQL(status=status_level, message=value)

    # commit to database
    session.add(s)
    session.commit()

@st.cache_data(ttl=600)  # cache for 1 minute
def fetch_data_providers_status():
    """Fetch the status of data providers"""
    try:
        logging.info("Fetching data provider statuses...")
        response = requests.get(f"{STATUS_API_URL}/data/providers", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return None

@st.cache_data(ttl=600)  # cache for 1 minute
def get_eumetsat_details():
    try:
        response = requests.get(f"{STATUS_API_URL}/data/providers/eumetsat?verbose=true", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch EUMETSAT details: {e}")
        return {}

def data_providers_status():
    """Display the status of data providers"""
    st.markdown(
        f'<h2 style="color:#63BCAF;font-size:24px;">{"Data Providers"}</h2>',
        unsafe_allow_html=True,
    )

    # Add css for making metrics smaller
    st.markdown(
        """
        <style>
            .stMetric > div * {
                font-size: 1.25rem !important;
            }
            .stMetric > label * {
                font-size: 0.875rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Fetch the latest status from the Status API
    data_statuses = fetch_data_providers_status()

    if data_statuses:
        # Display the status of each data provider
        for item in data_statuses:
            provider = item["provider"]
            source = item["source"]
            status = item["status"]
            msg = item["statusMessage"]
            details = item.get("details", {})

            emoji = "🟢" if status == "ok" else "🔴"

            col1, col2, col3 = st.columns([3, 1, 2])

            with col1:
                st.metric(source, f"{emoji} {provider}")

            with col2:
                st.metric("Status", status)

            with col3:
                st.markdown(f"""<div style="font-size: 0.875rem">Message</div>""", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.875rem; color:#ccc; margin-top: 0.25rem;'>{msg if msg else '–'}</div>", unsafe_allow_html=True)

            if provider == "EUMETSAT":
                if details:
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                    with col1:
                        st.metric("Latest (UTC)", details.get("latestTimestamp", "-"))

                    with col2:
                        st.metric("Complete", details.get("complete", "-"))

                    with col3:
                        st.metric("Incomplete", details.get("incomplete", "-"))

                    with col4:
                        undelivered = details.get("undeliveredPlanned", 0) + details.get("undeliveredUnplanned", 0)
                        st.metric("Undelivered", undelivered)
                with st.expander("Show full delivery timeline"):
                    extra = get_eumetsat_details()
                    result_data = extra.get("details", {}).get("results", [])

                    if len(result_data) >= 2:
                        records = result_data[0]
                        headers = result_data[1]
                        df = pd.DataFrame(records, columns=headers)
                        df["datetime"] = pd.to_datetime(df["datetime"])
                        df = df.sort_values("datetime", ascending=False)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No extended data available.")
            st.markdown(f"""<hr style="padding: 0; margin: 0;" />""", unsafe_allow_html=True)

    else:
        st.error("Failed to fetch data provider statuses.")


def status_page():
    """Main page for status"""
    st.set_page_config(layout="wide", page_title="OCF • Status", initial_sidebar_state="collapsed")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
            f'<h1 style="color:#63BCAF;font-size:48px;">{"Status Page"}</h1>',
            unsafe_allow_html=True,
        )
        # Data providers status
        data_providers_status()


    with col2:
        # Get database URLs
        db_url = os.getenv("DB_URL", None)
        db_url_sites = os.getenv("SITES_DB_URL", None)

        # Add database selection in sidebar, similar to user_page.py
        if region == "uk":
            national_or_sites = st.sidebar.selectbox("Select", ["National", "Sites"], index=0)
        else:
            national_or_sites = "Sites"

        # GENERAL STATUS SECTION
        # Get the appropriate connection for the selected database
        if national_or_sites == "National":
            connection = DatabaseConnection(url=db_url, echo=True)
        else:  # Sites
            connection = SitesDatabaseConnection(url=db_url_sites, echo=True)

        with connection.get_session() as session:
            # Get general status
            status = get_current_status(national_or_sites=national_or_sites, session=session)

            # show current status
            st.markdown(
                f'<h2 style="color:#63BCAF;font-size:24px;">{"Current Status"}</h2>',
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                colour = get_colour(status)
                st.write("Status")
                st.markdown(f":{colour}[{status.status}]")
            with col2:
                st.write("Message")
                # show the message or "-" if empty
                st.write(f"{status.message}" if status.message else "–")
            with col3:
                st.write("Last Updated")
                st.write(f"{status.created_utc}")

            st.write("")
            st.write("")

            # status_level, value = display_update_status()
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                st.markdown(f"""<div class="label">New status</div>""", unsafe_allow_html=True)
                status_level = st.selectbox(
                    "New status?", ("Ok", "Warning", "Error"), label_visibility="collapsed"
                )
            with col2:
                st.markdown(f"""<div class="label">Enter a message</div>""", unsafe_allow_html=True)
                value = st.text_input("Message", label_visibility="collapsed")
            with col3:
                st.markdown(f"""<div class="label">&nbsp;</div>""", unsafe_allow_html=True)
                if st.button(f"Update", key="general_status_button"):
                    write_new_status(
                        session, status, status_level, value, national_or_sites=national_or_sites
                    )
                    st.rerun()

