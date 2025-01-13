import os
import streamlit as st
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.models import Status
from nowcasting_datamodel.read.read import get_latest_status
from utils import load_css, parse_timestamp, format_time

def get_current_status():
    """Get the current status from the database"""
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:
        status = get_latest_status(session=session)
    return status


def display_update_status():
    """Display the update status form"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""<div class="label">Select the new status</div>""",
            unsafe_allow_html=True
        )
        status_level = st.selectbox("New status?", ("Ok", "Warning", "Error"),label_visibility="collapsed")
    with col2:
        
        st.markdown(
            f"""<div class="label">Enter a message</div>""",
            unsafe_allow_html=True
        )
        value = st.text_input("Message", label_visibility="collapsed")

    return str(status_level).lower(), value    

def write_new_status(session, status, status_level, value):
    """Write a new status to the database"""
    # make a new Pydanitc object, this gets validated
    s = Status(status=status_level, message=value)

    # change to sqlalchemy object
    s = s.to_orm()

    # bumpy the id
    s.id = status.id + 1

    # commit to database
    session.add(s)
    session.commit()

def status_page():
    """Main page for status"""
    st.markdown(
        f"""<div class="heading" style="align-item:center;">STATUS SECTION</div>
        <div class="sub-heading" style="align-item:center;">Check the Current Status</div>""",
        unsafe_allow_html=True,
    )
  
    # Fetch current status from the database
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=True)
    with connection.get_session() as session:
        status = get_current_status()
        
        # Load CSS for table styling
        base_dir = os.path.dirname(os.path.abspath(__file__))
        css_file_path = os.path.join(base_dir, "assets", "css", "status.css")
        load_css(css_file_path)

        # Parse and format the timestamp
        local_time = parse_timestamp(status)
        formatted_date, formatted_time, timezone_name = format_time(local_time)
        
        # Show current status in a styled table
        status_data = {
            "Status": [status.status],
            "Message": [status.message],
            "Date": [formatted_date],
            "Time": [f"{formatted_time} ({timezone_name})"],
        }

        st.markdown(
            f"""
            <table class="styled-table" style="margin: 0 auto; text-align: center;">
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Message</th>
                        <th>Date</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>{str(status.status).upper()}</td>
                        <td>{str(status.message).capitalize()}</td>
                        <td>{formatted_date}</td>
                        <td>{formatted_time} ({timezone_name})</td>
                    </tr>
                </tbody>
            </table>
        """,
            unsafe_allow_html=True,
        )
        
        st.markdown(
            f"""<div class="sub-heading" >Update the Status</div>""",
            unsafe_allow_html=True,
        )
        
        # Update status section
        status_level, value = display_update_status()
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            if st.button("Update Status", key="styled_button"):
                write_new_status(session, status, status_level, value)
                st.rerun()
