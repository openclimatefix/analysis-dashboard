import os
import streamlit as st
import ssl
from auth0_component import login_button
import logging


def _get_config(name):
    """Read config from env vars first, falling back to Streamlit secrets.

    Deployments provide these as environment variables; local runs typically put
    them in .streamlit/secrets.toml (which only populates st.secrets, not os.environ).
    """
    value = os.getenv(name)
    if value is None:
        try:
            value = st.secrets.get(name)
        except Exception:
            value = None
    return value


clientId = _get_config("AUTH0_CLIENT_ID")
# auth0_component builds URLs as "https://" + domain (e.g. the JWKS lookup during
# server-side token verification), so domain must be a bare host with no scheme or
# trailing slash. Normalise it here so a value like "https://tenant.auth0.com" still works.
domain = _get_config("AUTH0_DOMAIN")
if domain:
    domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
# Auth0 API identifier (audience) for the Status API. Requesting this audience means the
# returned access token is minted for the Status API and, via Auth0 RBAC, carries the
# read:admin permission needed to set statuses.
audience = _get_config("AUTH0_STATUS_AUDIENCE")

# need this for the login to work
ssl._create_default_https_context = ssl._create_unverified_context


logger = logging.getLogger(__name__)


def check_password():
    """Returns `True` if the user is logged in with an OCF Auth0 account."""

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>',
            unsafe_allow_html=True,
        )

    auth0_logged = False

    with col2:
        # show auth0 log in
        user_info = None
        try:
            user_info = login_button(
                clientId=clientId, domain=domain, audience=audience, debug_logs=True
            )
        except Exception as e:
            # Surface the underlying error (e.g. a JWT "Invalid audience" claim error)
            # so audience/config misconfiguration is visible rather than swallowed.
            st.error(f'Could not run auth: {type(e).__name__}: {e}')
            logger.error(f'Could not run auth {e}', exc_info=True)

        if user_info is None:
            st.text('No user info')

        if user_info:
            if not user_info['email'].lower().endswith('@openclimatefix.org'):
                st.text('This is only available to OCF members')
            else:
                auth0_logged = True
                # Stash the access token + email so pages can call authenticated APIs
                # (e.g. the Status API PUT action) on behalf of the logged-in user.
                st.session_state["access_token"] = user_info["token"]
                st.session_state["user_email"] = user_info["email"]

        if auth0_logged:
            return True
        else:
            st.text('Please log in')
            return False
