import os
import streamlit as st
from datetime import datetime, timedelta, time, timezone
from pvsite_datamodel.connection import DatabaseConnection
from pvsite_datamodel.read import (
    get_all_sites,
    get_user_by_email,
)
from get_data import (
    get_all_users, 
    get_all_site_groups, 
    update_user_site_group, 
    )


import plotly.graph_objects as go


# get_user_details(): select user and show details for that user: Say how many sites the user has up the top
# Add company name (also to db) 
# Allow users to view and search on the sites’ user ID (I.e. what the users call the site)

def get_user_details(session, email):
  """Get the user details from the database"""
  user_details = get_user_by_email(session=session,
                                         email=email)
  user_site_group = user_details.site_group.site_group_name
  user_site_count = len(user_details.site_group.sites)
  user_sites= [{"site_uuid": str(site.site_uuid), "client_site_id": str(site.client_site_id)} for site in user_details.site_group.sites]
  return user_sites, user_site_group, user_site_count

def sites_toolbox_page():
  st.markdown(
     f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>',
     unsafe_allow_html=True,
    )
  st.markdown(
     f'<h1 style="color:#63BCAF;font-size:48px;">{"Sites Toolbox"}</h1>',
     unsafe_allow_html=True,
    )

  url = "postgresql://main:7o5geKryjWVnVVfu@localhost:5434/pvsitedevelopment"
  connection = DatabaseConnection(url=url, echo=True)
  with connection.get_session() as session:
      # get the user details
      users = get_all_users(session=session)
      user_list = [user.email for user in users]
      sites = get_all_sites(session=session)
      sites = [str(site.site_uuid)for site in sites]
      site_groups = get_all_site_groups(session=session)
      site_groups = [site_groups.site_group_name for site_groups in site_groups]

  st.markdown(
     f'<h1 style="color:#63BCAF;font-size:32px;">{"Get User Details"}</h1>',
     unsafe_allow_html=True,
    )
  email = st.selectbox("Enter email of user you want to know about.", user_list)
  
  if st.button("Get user details"):
    user_sites, user_site_group, user_site_count = get_user_details(session=session, email=email)
    st.write("This user is part of the", user_site_group, "site group, which contains", user_site_count, "sites.")
    st.write("Here are the site_uuids and client_site_ids for this group:", user_sites)
    if st.button("Close user details"):
            st.empty()