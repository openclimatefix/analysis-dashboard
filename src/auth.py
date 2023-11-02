import os
import streamlit as st
import ssl
from auth0_component import login_button
import logging

clientId = os.getenv("AUTH0_CLIENT_ID")
domain = os.getenv("AUTH0_DOMAIN")

# need this for the login to work
ssl._create_default_https_context = ssl._create_unverified_context


logger = logging.getLogger(__name__)


def password_entered():
    """Checks whether a password entered by the user is correct."""
    if st.session_state["password"] == st.secrets["password"]:
        st.session_state["password_correct"] = True
        del st.session_state["password"]  # don't store password
    else:
        st.session_state["password_correct"] = False


def check_password():
    """Returns `True` if the user had the correct password."""

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>',
            unsafe_allow_html=True,
        )

    auth0_logged = False
    password_logged = False

    # check if we have logged on with a password, if we havent show auth0
    if ("password_correct" not in st.session_state) or (not st.session_state["password_correct"]):
        show_auth0 = True
    else:
        show_auth0 = False

    with col2:
        if show_auth0:
            # show auth0 log in
            try:
                user_info = login_button(clientId=clientId, domain=domain,debug_logs=True)
            except Exception as e:
                st.text('Could not run auth')
                logger.error(f'Could not run auth {e}')

            if user_info is None:
                st.text('No user info')

            if user_info:
                if '@openclimatefix.' not in user_info['email']:
                    st.text('This is only available to OCF members')
                else:
                    auth0_logged = True

        # if we have not logged in with auth0
        if not auth0_logged:
            if "password_correct" not in st.session_state:
                # First run, show input for password.
                st.text_input(
                    "Password", type="password", on_change=password_entered, key="password", autocomplete="current-password"
                )

            elif not st.session_state["password_correct"]:
                # Password not correct, show input + error.
                st.text_input(
                    "Password", type="password", on_change=password_entered, key="password", autocomplete="current-password"
                )
                st.error("😕 Password incorrect")

            else:
                # Password correct, show success message.
                st.success("🔒 Password correct")
                password_logged = True

        if auth0_logged or password_logged:
            return True
        else:
            st.text('Please log in')
            return False
