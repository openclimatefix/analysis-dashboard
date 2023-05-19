import os

import streamlit as st
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.models import Status
from nowcasting_datamodel.read.read import get_latest_status


def get_current_status():
    """Get the current status from the database"""

    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:

        status = get_latest_status(session=session)

    return status


# main page
def status_page():
    """Main page for status"""
    st.markdown(
        f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>', unsafe_allow_html=True
    )
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Status"}</h1>', unsafe_allow_html=True
    )

    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)

    with connection.get_session() as session:
        # get the status
        status = get_current_status()

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

        # update status
        st.write("Update status")
        col1, col2 = st.columns(2)
        with col1:
            status_level = st.selectbox("New status?", ("ok", "warning", "error"))
        with col2:
            value = st.text_input("New status message")

        if st.button("Update status"):
            s = Status(status=status_level, message=value)
            s = s.to_orm()
            session.add(s)
            session.commit()

            # this reloads this page, so the new current status shown
            st.experimental_rerun()


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
