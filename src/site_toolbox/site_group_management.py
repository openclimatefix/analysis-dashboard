"""This module contains functions for managing site groups."""

import re
import streamlit as st
from pvsite_datamodel.read import (
    get_all_sites,
    get_user_by_email,
    get_site_by_uuid,
    get_site_group_by_name
)

# from get_data import get_site_by_client_site_id
from pvsite_datamodel.read.site import get_site_by_client_site_id

from pvsite_datamodel.write.user_and_site import (
    add_site_to_site_group,
    update_user_site_group,
)


# select site by site_uuid or client_site_id 
def select_site_id(dbsession, query_method: str):
    """Select site by site_uuid or client_site_id"""
    if query_method == "site_uuid":
        site_uuids = [str(site.site_uuid) for site in get_all_sites(session=dbsession)]
        selected_uuid = st.selectbox("Sites by site_uuid", site_uuids)
    elif query_method == "client_site_id":
        client_site_ids = [
            str(site.client_site_id) for site in get_all_sites(session=dbsession)
        ]
        client_site_id = st.selectbox("Sites by client_site_id", client_site_ids)
        site = get_site_by_client_site_id(
            session=dbsession, client_site_id=client_site_id
        )
        selected_uuid = str(site.site_uuid)
    elif query_method not in ["site_uuid", "client_site_id"]:
        raise ValueError("Please select a valid query_method.")
    return selected_uuid



# update a site's site groups
def update_site_group(session, site_uuid: str, site_group_name: str):
    """Add a site to a site group"""
    site_group = get_site_group_by_name(
        session=session, site_group_name=site_group_name
    )
    site_group_sites = add_site_to_site_group(
        session=session, site_uuid=site_uuid, site_group_name=site_group_name
    )
    site_group_sites = [
        {"site_uuid": str(site.site_uuid), "client_site_id": str(site.client_site_id)}
        for site in site_group.sites
    ]
    site = get_site_by_uuid(session=session, site_uuid=site_uuid)
    site_site_groups = [site_group.site_group_name for site_group in site.site_groups]
    return site_group, site_group_sites, site_site_groups


# change site group for user
def change_user_site_group(session, email: str, site_group_name: str):
    """
    Change user to a specific site group name
    :param session: the database session
    :param email: the email of the user"""
    update_user_site_group(
        session=session, email=email, site_group_name=site_group_name
    )
    user = get_user_by_email(session=session, email=email)
    user_site_group = user.site_group.site_group_name
    user = user.email
    return user, user_site_group


# add all sites to the ocf site group
def add_all_sites_to_ocf_group(session, site_group_name="ocf"):
    """Add all sites to the ocf site group
    :param session: the database session
    :param site_group_name: the name of the site group"""
    all_sites = get_all_sites(session=session)

    ocf_site_group = get_site_group_by_name(
        session=session, site_group_name=site_group_name
    )

    site_uuids = [site.site_uuid for site in ocf_site_group.sites]

    sites_added = []

    for site in all_sites:
        if site.site_uuid not in site_uuids:
            ocf_site_group.sites.append(site)
            sites_added.append(str(site.site_uuid))
            session.commit()
            message = f"Added {len(sites_added)} sites to group {site_group_name}."

    if len(sites_added) == 0:
        message = f"There are no new sites to be added to {site_group_name}."

    return message, sites_added


# validate email address
def validate_email(email):
    if re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return True
    return False

