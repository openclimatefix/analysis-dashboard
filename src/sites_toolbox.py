"""This module contains the sites toolbox for the OCF dashboard"""
import os
import json
import streamlit as st
import re
from datetime import datetime, timezone
from sqlalchemy import func
from pvsite_datamodel.connection import DatabaseConnection
from pvsite_datamodel.sqlmodels import SiteSQL
# from pvsite_datamodel.write.user_and_site import create_site_group
from pvsite_datamodel.read import (
    get_all_sites,
    get_user_by_email,
    get_site_by_uuid,
    get_site_group_by_name
)
from pvsite_datamodel.read.model import get_models

from get_data import get_all_users, get_all_site_groups, get_site_by_client_site_id
from pvsite_datamodel.write.user_and_site import (
    assign_model_name_to_site,
    create_site,
    create_user,
    delete_site,
    delete_user,
    delete_site_group,
    add_site_to_site_group,
    update_user_site_group,
    create_site_group
)

from Site_toolbox.get_details import (
    get_user_details,
    get_site_details,
    get_site_group_details,
)

from Site_toolbox.site_group_management import (
    select_site_id,
    update_site_group,
    change_user_site_group,
    add_all_sites_to_ocf_group,
    validate_email,
)

# sites toolbox page
def sites_toolbox_page():

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Sites Toolbox"}</h1>',
        unsafe_allow_html=True,
    )

    url = "postgresql://postgres:mayanksharma@localhost:5432/sitedatabase"

    connection = DatabaseConnection(
        url=url,
        echo=True,
    )
    with connection.get_session() as session:
        # get the user details
        users = get_all_users(session=session)
        user_list = [user.email for user in users]
        site_groups = get_all_site_groups(session=session)
        site_groups = [site_group.site_group_name for site_group in site_groups]
        site_uuids = get_all_sites(session=session)
        site_uuid_list = [site.site_uuid for site in site_uuids]

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
        site_details = get_site_details(session=session, site_uuid=site_id)
        site_id = (
            site_details["client_site_id"]
            if query_method == "client_site_id"
            else site_details["site_uuid"]
        )
        st.write("Here are the site details for site", site_id, ":", site_details)
        if st.button("Close site details"):
            st.empty()

    # getting site group details
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:32px;">{"Get Site Group Details"}</h1>',
        unsafe_allow_html=True,
    )
    site_group_name = st.selectbox("Enter the site group name.", site_groups)
    if st.button("Get site group details"):
        site_group_sites, site_group_users = get_site_group_details(
            session=session, site_group_name=site_group_name
        )
        st.write(
            "Site group",
            site_group_name,
            "contains the following",
            len(site_group_sites),
            "sites:",
            site_group_sites,
        )
        st.write(
            "The following",
            len(site_group_users),
            "users are part of this group:",
            site_group_users,
        )
        if st.button("Close site group details"):
            st.empty()
        # add site to site group
    st.markdown(
        f'<h1 style="color:#ffd053;font-size:32px;">{"Add Site to Site Group"}</h1>',
        unsafe_allow_html=True,
    )
    site_uuid = st.selectbox("Select site", site_uuid_list, key="add")
    site_group = st.selectbox("Select site group", site_groups)
    if st.button("Add site to site group"):
        site_group, site_group_sites, site_site_groups = update_site_group(
            session=session, site_uuid=site_uuid, site_group_name=site_group
        )
        st.write(
            "Site",
            site_uuid,
            "has been added to",
            site_group.site_group_name,
            ", which has",
            len(site_group_sites),
            "sites: ",
            site_group_sites,
        )
        st.write(
            "The following site groups include site", site_uuid, ":", site_site_groups
        )
        if st.button("Close details"):
            st.empty()

    # getting site group details
    st.markdown(
        f'<h1 style="color:#ffd053;font-size:32px;">{"Add All Sites to OCF Group"}</h1>',
        unsafe_allow_html=True,
    )
    if st.button("Add Sites to OCF group"):
        message = add_all_sites_to_ocf_group(session=session, site_group_name="ocf")
        st.write(message)
        if st.button("Close details"):
            st.empty()

    # update user site group
    st.markdown(
        f'<h1 style="color:#ffd053;font-size:32px;">{"Change User Site Group"}</h1>',
        unsafe_allow_html=True,
    )
    email = st.selectbox("Select user whose site group will change.", user_list)
    site_group_name = st.selectbox("Select site group for user", site_groups)

    if st.button("Change user's site group"):
        user, user_site_group = change_user_site_group(
            session=session, email=email, site_group_name=site_group_name
        )
        st.write(user, "is now in the", user_site_group, "site group.")
        if st.button("Close"):
            st.empty()

    # update ml model to site
    st.markdown(
        f'<h1 style="color:#ffd053;font-size:32px;">{"Assign ML Model to Site"}</h1>',
        unsafe_allow_html=True,
    )
    site_uuid = st.selectbox("Select the site", site_uuid_list)
    with connection.get_session() as session:
        ml_models = get_models(session=session, site_uuid=site_uuid)
        ml_model_names = [model.name for model in ml_models]
        ml_model_name = st.selectbox("Select the ml model", ml_model_names)

        if st.button("Assign ML Model to Site"):
            assign_model_name_to_site(session=session, site_uuid=site_uuid, model_name=ml_model_name)


    # create a new site
    st.markdown(
        f'<h1 style="color:#7bcdf3;font-size:32px;">{"Create Site"}</h1>',
        unsafe_allow_html=True,
    )
    with st.expander("Input new site data"):
        with connection.get_session() as session:
            st.markdown(
                f'<h1 style="color:#FFD053;font-size:22px;">{"Client Information"}</h1>',
                unsafe_allow_html=True,
            )
            # ml_id = max_ml_id + 1
            client_site_id = st.number_input("Client Site Id *", step=1)
            client_site_name = st.text_input("Client Site Name *")

            st.markdown(
                f'<h1 style="color:#FFD053;font-size:22px;">{"Geographical Information"}</h1>',
                unsafe_allow_html=True,
            )

            latitude = st.text_input("latitude *")
            longitude = st.text_input("longitude *")
            region = st.text_input("region")

            st.markdown(
                f'<h1 style="color:#FFD053;font-size:22px;">{"PV Information"}</h1>',
                unsafe_allow_html=True,
            )
            capacity_kw = st.text_input("Capacity [kwp] *")
            orientation = st.text_input("Orientation")
            tilt = st.text_input("Tilt")
            inverter_capacity_kw = st.text_input("Inverter capacity [kwp]")
            module_capacity_kw = st.text_input("Module Capacity [kwp]")

            if st.button(f"Create new site"):
                if "" in [
                    client_site_id,
                    client_site_name,
                    latitude,
                    longitude,
                    capacity_kw,
                ]:
                    error = (
                        f"Please check that you've entered data for each field. "
                        f"{client_site_id=} {client_site_name=} "
                        f"{latitude=} {longitude=} {capacity_kw=}"
                    )
                    st.write(error)
                else:  # create new
                    site, message = create_site(
                        session=session,
                        client_site_id=client_site_id,
                        client_site_name=client_site_name,
                        region=region,
                        orientation=orientation,
                        tilt=tilt,
                        latitude=latitude,
                        longitude=longitude,
                        inverter_capacity_kw=inverter_capacity_kw,
                        module_capacity_kw=module_capacity_kw,
                        capacity_kw=capacity_kw,
                    )
                    site_details = {
                        "site_uuid": str(site.site_uuid),
                        "ml_id": str(site.ml_id),
                        "client_site_id": str(site.client_site_id),
                        "client_site_name": str(site.client_site_name),
                        "site_group_names": [
                            site_group.site_group_name
                            for site_group in site.site_groups
                        ],
                        "latitude": str(site.latitude),
                        "longitude": str(site.longitude),
                        "DNO": str(site.dno),
                        "GSP": str(site.gsp),
                        "tilt": str(site.tilt),
                        "orientation": str(site.orientation),
                        "inverter_capacity_kw": (f"{site.inverter_capacity_kw} kw"),
                        "module_capacity_kw": (f"{site.module_capacity_kw} kw"),
                        "capacity": (f"{site.capacity_kw} kw"),
                        "date_added": (site.created_utc.strftime("%Y-%m-%d")),
                    }
                    st.write(message)
                    st.write("Here are the site details for the new site")
                    st.json(site_details)
                    if st.button("Close site details"):
                        st.empty()

    # create a new user
    st.markdown(
        f'<h1 style="color:#7bcdf3;font-size:32px;">{"Create User"}</h1>',
        unsafe_allow_html=True,
    )

    with st.expander("Input new user data"):
        with connection.get_session() as session:
            user_list = get_all_users(session=session)
            user_list = [user.email for user in user_list]
            st.markdown(
                f'<h1 style="color:#FFD053;font-size:22px;">{"User Information"}</h1>',
                unsafe_allow_html=True,
            )
            email = st.text_input("User Email")
            site_group_name = st.selectbox(
                "Select a group", site_groups, key="site_group"
            )
            email_validation = validate_email(email)
            # check that site group exists
            if st.button(f"Create new user"):
                if email_validation is False:
                    st.markdown(
                        f'<p style="color:#f07167;font-size:16px;">{"Please enter a valid email address."}</p>',
                        unsafe_allow_html=True,
                    )
                elif email in user_list:
                    st.markdown(
                        f'<p style="color:#f07167;font-size:16px;">{"This user already exists."}</p>',
                        unsafe_allow_html=True,
                    )
                else:
                    user = create_user(
                        session=session,
                        email=email,
                        site_group_name=site_group_name,
                    )

                    user_details = {
                        "email": str(user.email),
                        "site_group": str(site_group_name),
                        "date_added": (user.created_utc.strftime("%Y-%m-%d")),
                    }
                    st.json(user_details)

                if st.button("Close details"):
                    st.empty()

    # create site group
    st.markdown(
        f'<h1 style="color:#7bcdf3;font-size:32px;">{"Create Site Group"}</h1>',
        unsafe_allow_html=True,
    )

    with st.expander("Input new group data"):
        with connection.get_session() as session:
            st.markdown(
                f'<h1 style="color:#FFD053;font-size:22px;">{"Site Group Information"}</h1>',
                unsafe_allow_html=True,
            )
            new_site_group_name = st.text_input("Enter new site group name")
            # check that site group exists
            if st.button(f"Create new site group"):
                if new_site_group_name == "":
                    st.markdown(
                        f'<p style="color:#f07167;font-size:16px;">{"Please enter a valid name for the site group."}</p>',
                        unsafe_allow_html=True,
                    )
                elif new_site_group_name in site_groups:
                    st.markdown(
                        f'<p style="color:#f07167;font-size:16px;">{"This site group already exists."}</p>',
                        unsafe_allow_html=True,
                    )
                else:
                    new_site_group = create_site_group(
                        db_session=session,
                        site_group_name=new_site_group_name,
                    )
                    new_site_group_details = {
                        "site_group": str(new_site_group.site_group_name),
                        "site_group_uuid": str(new_site_group.site_group_uuid),
                        "date_added": (new_site_group.created_utc.strftime("%Y-%m-%d")),
                    }
                    st.json(new_site_group_details)

                if st.button("Close details"):
                    st.empty()

# delete site
    st.markdown(
        f'<h1 style="color:#E63946;font-size:32px;">{"Delete Site"}</h1>',
        unsafe_allow_html=True,
    )

    with st.expander("Input site data"):
        with connection.get_session() as session:
            st.markdown(
                f'<h1 style="color:#FF9736;font-size:22px;">{"Site UUID"}</h1>',
                unsafe_allow_html=True,
            )
            site_uuid = st.selectbox("Enter site uuid", site_uuid_list)
            if st.button("Delete Site"):
                message = delete_site(session=session, site_uuid=site_uuid)
                st.write(message)
    
    st.markdown(
        f'<h1 style="color:#E63946;font-size:32px;">{"Delete User"}</h1>',
        unsafe_allow_html=True,
    )

    with st.expander("Input user email"):
        with connection.get_session() as session:
            st.markdown(
                f'<h1 style="color:#FF9736;font-size:22px;">{"User Information"}</h1>',
                unsafe_allow_html=True,
            )
            email = st.selectbox("Enter user email", user_list)
            if st.button("Delete User"):
                message = delete_user(session=session, email=email)
                st.write(message)

# delete site group
    st.markdown(
        f'<h1 style="color:#E63946;font-size:32px;">{"Delete Site Group"}</h1>',
        unsafe_allow_html=True,
    )

    with st.expander("Input site group information"):
        with connection.get_session() as session:
            site_groups = get_all_site_groups(session=session)
            site_groups = [site_group.site_group_name for site_group in site_groups]
            st.markdown(
                f'<h1 style="color:#FF9736;font-size:22px;">{"Site Group Information"}</h1>',
                unsafe_allow_html=True,
            )
            site_group_name = st.selectbox("Enter site group", site_groups)
            if st.button("Delete Site Group"):
                message = delete_site_group(session=session, site_group_name=site_group_name)
                st.write(message)
