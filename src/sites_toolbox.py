"""This module contains the sites toolbox for the OCF dashboard"""
import os
import streamlit as st
from datetime import datetime as dt, timedelta, time, timezone
from pvsite_datamodel.connection import DatabaseConnection
from pvsite_datamodel.read import (
    get_all_sites,
    get_user_by_email,
    get_site_by_uuid,
)
from get_data import (
    get_all_users,
    get_all_site_groups,
    get_site_by_client_site_id,    
    update_user_site_group,
)


import plotly.graph_objects as go

# get details for one user 
def get_user_details(session, email):
    """Get the user details from the database"""
    user_details = get_user_by_email(session=session, email=email)
    user_site_group = user_details.site_group.site_group_name
    user_site_count = len(user_details.site_group.sites)
    user_sites = [
        {"site_uuid": str(site.site_uuid), "client_site_id": str(site.client_site_id)}
        for site in user_details.site_group.sites
    ]
    return user_sites, user_site_group, user_site_count

# get details for one site

def get_site_details(session, site_selection):
  """Get the site details for one site"""
  site_uuid = get_site_by_uuid(session=session, site_uuid=site_selection)
  site_details = {"site_uuid": str(site_uuid.site_uuid), 
                  "client_site_id": str(site_uuid.client_site_id),
                  "client_site_name": str(site_uuid.client_site_name),
                  "site_group_name": str(site_uuid.site_groups[0].site_group_name),
                  "latitude": str(site_uuid.latitude),
                  "longitude": str(site_uuid.longitude),
                  "DNO": str(site_uuid.dno),
                  "GSP": str(site_uuid.gsp),
                  "tilt": str(site_uuid.tilt),
                  "orientation": str(site_uuid.orientation),
                  "capacity": (f'{site_uuid.capacity_kw} kw'),
                  "date_added": (site_uuid.created_utc.strftime("%Y-%m-%d"))}
  return site_details

def select_site_id(dbsession, query_method):
        if query_method == "site_uuid":
            site_list = [str(site.site_uuid) for site in get_all_sites(session=dbsession)]
            selected_id = st.selectbox("Sites by site_uuid", site_list)
        elif query_method == "client_site_id":
            site_list= [str(site.client_site_id) for site in get_all_sites(session=dbsession)]
            selected_id = st.selectbox("Sites by client_site_id", site_list)
            selected_id = get_site_by_client_site_id(session=dbsession, client_site_id = selected_id)
            selected_id = str(selected_id.site_uuid)
        return selected_id


def sites_toolbox_page():
    st.markdown(
        f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Sites Toolbox"}</h1>',
        unsafe_allow_html=True,
    )

    url = os.environ["SITES_DB_URL"]

    connection = DatabaseConnection(
        url=url,
        echo=True,
    )
    with connection.get_session() as session:
        # get the user details
        users = get_all_users(session=session)
        user_list = [user.email for user in users]
      

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:32px;">{"Get User Details"}</h1>',
        unsafe_allow_html=True,
    )
    email = st.selectbox("Enter email of user you want to know about.", user_list)
    # getting user details 
    if st.button("Get user details"):
        user_sites, user_site_group, user_site_count = get_user_details(
            session=session, email=email
        )
        st.write(
            "This user is part of the",
            user_site_group,
            "site group, which contains",
            user_site_count,
            "sites.",
        )
        st.write(
            "Here are the site_uuids and client_site_ids for this group:", user_sites
        )
        if st.button("Close user details"):
            st.empty()
            
    # getting site details   
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:32px;">{"Get Site Details"}</h1>',
        unsafe_allow_html=True,
    )
    query_method = st.radio("Select site by", ("site_uuid", "client_site_id"))
    
    site_id = select_site_id(dbsession=session, query_method=query_method)

    if st.button("Get site details"):
        site_details = get_site_details(session=session, site_selection=site_id)
        site_id = site_details["client_site_id"] if query_method == "client_site_id" else site_details["site_uuid"]
        st.write("Here are the site details for site", site_id, ":", site_details)
        if st.button("Close site details"):
            st.empty()
    
