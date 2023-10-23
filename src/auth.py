import os
import streamlit as st
import ssl
from auth0_component import login_button

clientId = os.getenv("AUTH0_CLIENT_ID")
domain = os.getenv("AUTH0_DOMAIN")

# need this for the login to work
ssl._create_default_https_context = ssl._create_unverified_context


def check_password():
    """Returns `True` if the user had the correct password."""

    with st.sidebar:
        try:
            user_info = login_button(clientId=clientId, domain=domain,debug_logs=True)
        except:
            st.text('Could not run auth')
            return False

    if user_info is None:
        st.text('No user info')
        return False

    if not user_info:
        st.text('Please log in')
        return False

    if '@openclimatefix.' not in user_info['email']:
        st.text('This is only available to OCF members')
        return False

    return user_info
