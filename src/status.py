import os
import streamlit as st
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.models import Status
from nowcasting_datamodel.read.read import get_latest_status , get_sites #, get_latest_site_status
from pvsite_datamodel.connection import DatabaseConnection as SitesDatabaseConnection
from utils import load_css, parse_timestamp, format_time
from pvsite_datamodel.read.status import SiteStatus  
#from pvsite_datamodels import get_latest_site_status


# Region setting to determine which options to show
region = os.getenv("REGION", "uk")

def get_current_status(national_or_sites="National"):
    """Get the current status from the database"""
    if national_or_sites == "National":
        url = os.getenv("DB_URL", None)
        connection = DatabaseConnection(url=url, echo=True)
    else:  # Sites
        url = os.getenv("SITES_DB_URL", None)
        connection = SitesDatabaseConnection(url=url, echo=True)
        
    with connection.get_session() as session:
        status = get_latest_status(session=session)
    return status

def get_current_site_status(site_id, national_or_sites="National"):
    """Get the current status for a specific site from the database"""
    if national_or_sites == "National":
        url = os.getenv("DB_URL", None)
        connection = DatabaseConnection(url=url, echo=True)
    else:  # Sites
        url = os.getenv("SITES_DB_URL", None)
        connection = SitesDatabaseConnection(url=url, echo=True)
        
    with connection.get_session() as session:
        site_status = get_latest_status(session=session, site_id=site_id)

    return site_status

def get_all_sites(national_or_sites="National"):
    """Get all available sites from the database"""
    if national_or_sites == "National":
        url = os.getenv("DB_URL", None)
        connection = DatabaseConnection(url=url, echo=True)
    else:  # Sites
        url = os.getenv("SITES_DB_URL", None)
        connection = SitesDatabaseConnection(url=url, echo=True)
        
    with connection.get_session() as session:
        sites = get_sites(session=session)
    return sites

def display_update_status():
    """Display the update status form"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""<div class="label">Select the new status</div>""",
            unsafe_allow_html=True
        )
        status_level = st.selectbox("New status?", ("Ok", "Warning", "Error"), label_visibility="collapsed")
    with col2:
        st.markdown(
            f"""<div class="label">Enter a message</div>""",
            unsafe_allow_html=True
        )
        value = st.text_input("Message", label_visibility="collapsed")

    return str(status_level).lower(), value    

def display_update_site_status(sites):
    """Display the update status form for site API"""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""<div class="label">Select site</div>""",
            unsafe_allow_html=True
        )
        site_options = {site.name: site.id for site in sites}
        selected_site_name = st.selectbox("Site", options=list(site_options.keys()), label_visibility="collapsed")
        selected_site_id = site_options[selected_site_name]
        
    with col2:
        st.markdown(
            f"""<div class="label">Select the new status</div>""",
            unsafe_allow_html=True
        )
        status_level = st.selectbox("New site status?", ("Ok", "Warning", "Error"), key="site_status", label_visibility="collapsed")
    
    with col3:
        st.markdown(
            f"""<div class="label">Enter a message</div>""",
            unsafe_allow_html=True
        )
        value = st.text_input("Site Message", key="site_message", label_visibility="collapsed")

    return selected_site_id, str(status_level).lower(), value

def write_new_status(session, status, status_level, value, national_or_sites="National"):
    """Write a new status to the database"""
    # make a new Pydanitc object, this gets validated
    s = Status(status=status_level, message=value)

    # change to sqlalchemy object
    s = s.to_orm()

    # bump the id
    if status:
        s.id = status.id + 1
    else:
        s.id = 1

    # commit to database
    session.add(s)
    session.commit()

def write_new_site_status(session, site_id, site_status, status_level, value, national_or_sites="National"):
    """Write a new site status to the database"""
    # make a new Pydanitc object, this gets validated
    s = SiteStatus(site_id=site_id, status=status_level, message=value)

    # bump the id if site_status exists
    if site_status:
        s.id = site_status.id + 1
    else:
        # If no existing site status, start with ID 1
        s.id = 1

    # commit to database
    session.add(s)
    session.commit()

def display_status_table(status, title="Current Status"):
    """Display the current status in a styled table"""
    if status:
        # Parse and format the timestamp
        local_time = parse_timestamp(status)
        formatted_date, formatted_time, timezone_name = format_time(local_time)
        
        # Show current status in a styled table
        st.markdown(
            f"""
            <div class="sub-heading">{title}</div>
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
    else:
        st.markdown(
            f"""
            <div class="sub-heading">No status available for {title}</div>
            """,
            unsafe_allow_html=True,
        )

def status_page():
    """Main page for status"""
    st.markdown(
        f"""<div class="heading" style="align-item:center;">STATUS SECTION</div>
        <div class="sub-heading" style="align-item:center;">Check the Current Status</div>""",
        unsafe_allow_html=True,
    )
    
    # Load CSS for table styling
    base_dir = os.path.dirname(os.path.abspath(__file__))
    css_file_path = os.path.join(base_dir, "assets", "css", "status.css")
    load_css(css_file_path)
    
    # Get database URLs
    db_url = os.getenv("DB_URL", None)
    db_url_sites = os.getenv("SITES_DB_URL", None)
    
    # Add database selection in sidebar, similar to user_page.py
    if region == 'uk':
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
        status = get_current_status(national_or_sites=national_or_sites)
        
        # Display current status
        display_status_table(status, title=f"{national_or_sites} General Status")
        
        # Status Update Section
        st.markdown(
            f"""<div class="sub-heading">Update {national_or_sites} General Status</div>""",
            unsafe_allow_html=True,
        )
        
        status_level, value = display_update_status()
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            if st.button(f"Update {national_or_sites} Status", key="general_status_button"):
                write_new_status(session, status, status_level, value, national_or_sites=national_or_sites)
                st.rerun()
    
    # Add horizontal divider
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # SITE STATUS SECTION
    # Reestablish connection to ensure the session is fresh
    if national_or_sites == "National":
        connection = DatabaseConnection(url=db_url, echo=True)
    else:  # Sites
        connection = SitesDatabaseConnection(url=db_url_sites, echo=True)
        
    with connection.get_session() as session:
        # Get sites
        sites = get_all_sites(national_or_sites=national_or_sites)
        
        # Site API Status Section
        st.markdown(
            f"""<div class="sub-heading">{national_or_sites} Site Status</div>""",
            unsafe_allow_html=True,
        )
        
        if sites:
            # Display dropdown to select site for viewing current status
            site_options = {site.name: site.id for site in sites}
            selected_view_site = st.selectbox("Select site to view status", 
                                        options=list(site_options.keys()),
                                        key="view_site_status")
            selected_view_site_id = site_options[selected_view_site]
            
            # Get and display the current status for the selected site
            site_status = get_current_site_status(site_id=selected_view_site_id, national_or_sites=national_or_sites)
            display_status_table(site_status, title=f"{selected_view_site} Status")
            
            # Site status update form
            st.markdown(
                f"""<div class="sub-heading">Update {national_or_sites} Site Status</div>""",
                unsafe_allow_html=True,
            )
            
            selected_site_id, site_status_level, site_value = display_update_site_status(sites)
            
            # Find the site name for the selected ID
            selected_site_name = next((site.name for site in sites if site.id == selected_site_id), "Unknown")
            
            # Get current status for the selected site
            current_site_status = get_current_site_status(site_id=selected_site_id, national_or_sites=national_or_sites)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button(f"Update {selected_site_name} Status", key="site_status_button"):
                    write_new_site_status(session, selected_site_id, current_site_status, 
                                         site_status_level, site_value, national_or_sites=national_or_sites)
                    st.rerun()
        else:
            st.warning(f"No sites found in the {national_or_sites} database.")