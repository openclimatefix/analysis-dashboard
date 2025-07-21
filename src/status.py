import os
from datetime import datetime
import streamlit as st
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.models import Status
from nowcasting_datamodel.read.read import get_latest_status
from pvsite_datamodel.connection import DatabaseConnection as SitesDatabaseConnection
from pvsite_datamodel.read.status import get_latest_status as get_latest_status_site
from pvsite_datamodel.sqlmodels import StatusSQL


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
    col1, col2 = st.columns(2)

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


def status_page():
    """Main page for status"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Status Page"}</h1>',
        unsafe_allow_html=True,
    )

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
        st.write("Current status")

        # format into 3 columns
        col1, col2, col3 = st.columns(3)
        with col1:
            colour = get_colour(status)
            st.markdown(f":{colour}[{status.status}]")
        with col2:
            st.write(f"{status.message}")
        with col3:
            st.write(f"{status.created_utc}")

        st.write("")
        st.write("")

        status_level, value = display_update_status()
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            if st.button(f"Update {national_or_sites} Status", key="general_status_button"):
                write_new_status(
                    session, status, status_level, value, national_or_sites=national_or_sites
                )
                st.rerun()

    st.markdown(
        f'<h2 style="color:#ffd053;font-size:32px;">{"Example messages"}</h2>',
        unsafe_allow_html=True,
    )
    # example messages
    st.write(
        "We are doing some upgrades, and dont expect any downtime. "
        "We will keep you informed if anything changes"
    )

    st.write("We are experiencing some issues, " "and we are current investigating the issue.")

    st.write(
        "We are experiencing some issues with the Forecast, "
        "we hope to resolve them as soon as possible"
    )

    st.write(
        "We are experiencing some issues with the Forecast, "
        "we hope to resolve them as soon as possible. "
        "This is due to a 3rd party NWP data provider."
    )

    st.write("There is a major issue with the Quartz Solar API,"
             "we are looking into this and "
             "hope to solve this as soon as possible")

    st.write(
        f"We experienced some issues with the Forecast on {datetime.now().date()}. "
        "We apologies for these issues, "
        "this was due to missing 3rd party Satellite data."
    )
