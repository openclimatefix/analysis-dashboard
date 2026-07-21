import logging
import os

import altair as alt
import pandas as pd
import requests
import streamlit as st
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models.models import Status
from nowcasting_datamodel.read.read import get_latest_status
from pvsite_datamodel.connection import DatabaseConnection as SitesDatabaseConnection
from pvsite_datamodel.read.status import get_latest_status as get_latest_status_site
from pvsite_datamodel.sqlmodels import StatusSQL

ENV = os.getenv("ENVIRONMENT", "development")
STATUS_API_URL = "https://status.quartz.energy" if ENV == "production" else "https://status-dev.quartz.energy"

# Map the dashboard's selectable status targets to Status API product keys.
PRODUCTS = {"National": "gb-solar", "NL": "nl-solar", "Assets": "asset-solar"}


def get_colour_for_value(value) -> str:
    """Get the colour for a status value

    green = ok
    orange = warning
    red = error
    """
    colour = "green"
    if value == "warning":
        colour = "orange"
    elif value == "error":
        colour = "red"
    return colour


def get_colour(status) -> str:
    """Get the colour for a status object (has a `.status` attribute)."""
    return get_colour_for_value(status.status)


@st.cache_data(ttl=60)  # cache for 1 minute
def get_product_status(key):
    """Fetch the current status for a product from the Status API."""
    response = requests.get(f"{STATUS_API_URL}/products/{key}", timeout=10)
    response.raise_for_status()
    return response.json()  # {key, name, status, message, source, updatedAt}


def put_product_status(key, status_level, message, token):
    """Set a product's status via the Status API admin PUT action.

    Requires a JWT bearer token with the read:admin scope.
    """
    response = requests.put(
        f"{STATUS_API_URL}/products/{key}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": status_level, "message": message},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def format_updated_at(value):
    """Format the API's ISO `updatedAt` string as a UTC timestamp for display."""
    if not value:
        return "–"
    try:
        return pd.to_datetime(value, utc=True).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return value


# Region setting to determine which options to show
region = os.getenv("REGION", "uk")


def get_current_status(session, national_or_sites="National"):
    """Get the current status from the database"""
    if national_or_sites == "National":
        status = get_latest_status(session=session)
    else:  # Sites
        status = get_latest_status_site(session=session)

    return status


def display_update_status(
    status, session, national_or_sites="National",
):
    """Display the update status form"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.markdown("""<div class="label">New status</div>""", unsafe_allow_html=True)
        status_level = st.selectbox(
            "New status?", ("ok", "warning", "error"), label_visibility="collapsed",
        )
    with col2:
        st.markdown("""<div class="label">Enter a message</div>""", unsafe_allow_html=True)
        value = st.text_input("Message", label_visibility="collapsed")
    with col3:
        st.markdown("""<div class="label">&nbsp;</div>""", unsafe_allow_html=True)
        if st.button("Update", key="general_status_button"):
            write_new_status(
                session, status, status_level, value, national_or_sites=national_or_sites,
            )
            st.success(f"Status updated to {status_level} with message: {value}")
            st.rerun()


def write_new_status(session, status, status_level, value, national_or_sites="National"):
    """Write a new status to the database"""
    """Write a new status to the database"""
    if national_or_sites == "National":
        # make a new Pydanitc object, this gets validated
        s = Status(status=status_level, message=value)

        # change to sqlalchemy object
        s = s.to_orm()

        # bumpy the id
        s.id = status.id + 1
    else:
        s = StatusSQL(status=status_level, message=value)

    # commit to database
    session.add(s)
    session.commit()

def submit_product_status(key, status_level, message):
    """Send a status update to the Status API and surface any auth/other errors."""
    token = st.session_state.get("access_token")
    if not token:
        st.error("You must be logged in via Auth0 to update the status.")
        return
    try:
        put_product_status(key, status_level, message, token)
    except requests.exceptions.HTTPError as e:
        resp = e.response
        code = resp.status_code if resp is not None else None
        body = resp.text if resp is not None else str(e)
        if code == 401:
            # token rejected: invalid signature / audience / expired
            st.error(f"Status API rejected the token (401). Response: {body}")
        elif code == 403:
            # authenticated but missing the required admin permission
            st.error(f"Token accepted but not authorised to set status (403). Response: {body}")
        else:
            st.error(f"Failed to update status ({code}): {body}")
        return
    except Exception as e:
        st.error(f"Failed to update status: {e}")
        return

    st.success(f"Status updated to {status_level} with message: {message}")
    # drop the cached read so the new value shows on rerun
    get_product_status.clear()
    st.rerun()


def render_product_status_card(product_name, key):
    """Show one product's current status and an inline update form.

    All widgets are keyed by the product `key` so several cards can be stacked without
    Streamlit duplicate-widget-id clashes.
    """
    with st.container(border=True):
        try:
            status = get_product_status(key)
        except Exception as e:
            st.error(f"Failed to fetch status for {product_name}: {e}")
            return

        colour = get_colour_for_value(status.get("status"))
        header_col, updated_col = st.columns([2, 3])
        with header_col:
            st.markdown(
                f"**{status.get('name', product_name)}** &nbsp; :{colour}[{status.get('status')}]"
            )
        with updated_col:
            st.caption(f"Last updated {format_updated_at(status.get('updatedAt'))} UTC", text_alignment="right")

        st.markdown(
            '<p style="color:#888888;font-size:12px;margin-bottom:0;">Current message</p>',
            unsafe_allow_html=True,
        )
        st.write(status.get("message") if status.get("message") else "–")

        status_col, message_col, button_col = st.columns([1, 2, 1])
        with status_col:
            status_level = st.selectbox(
                "New status", ("ok", "warning", "error"), key=f"status_level_{key}",
            )
        with message_col:
            message = st.text_input("Message", key=f"status_message_{key}")
        with button_col:
            # spacer so the button lines up with the inputs (past their labels)
            st.markdown("<div style='height: 1.75rem'></div>", unsafe_allow_html=True)
            update = st.button("Update", key=f"status_update_{key}", use_container_width=True)

        if update:
            submit_product_status(key, status_level, message)


def ocf_status_api():
    """Show and update OCF product statuses via the Status API (UK/EU)."""
    st.markdown(
        '<h2 style="color:#63BCAF;font-size:24px;">OCF Product Statuses</h2>',
        unsafe_allow_html=True,
    )
    for product_name, key in PRODUCTS.items():
        render_product_status_card(product_name, key)


def ocf_status():
    # UK/EU statuses now come from the Status API; India stays on the legacy DB path
    # until a Status API product is spun up for it.
    if region == "uk":
        ocf_status_api()
        return

    # --- Legacy DB-backed path (India, Sites only) ---
    db_url_sites = os.getenv("SITES_DB_URL", None)
    national_or_sites = "Sites"

    connection = SitesDatabaseConnection(url=db_url_sites, echo=True)

    with connection.get_session() as session:
        # Get general status
        status = get_current_status(national_or_sites=national_or_sites, session=session)

        # show current status
        st.markdown(
            f'<h2 style="color:#63BCAF;font-size:24px;">OCF {national_or_sites} Status &nbsp;'
            f'<small style="font-size: 0.875rem; font-weight: 300; color: #ffffff;">[Select region in sidebar]</small></h2>',
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            colour = get_colour(status)
            st.write("Status")
            st.markdown(f":{colour}[{status.status}]")
        with col2:
            st.write("Message")
            # show the message or "-" if empty
            st.write(f"{status.message}" if status.message else "–")
        with col3:
            st.write("Last Updated (UTC)")
            st.markdown(f"<small>{status.created_utc.strftime('%Y-%m-%d %H:%M:%S')}</small>", unsafe_allow_html=True)


        display_update_status(status, session, national_or_sites=national_or_sites)

def example_status_messages():
    """Example status messages, grouped into tabs and shown as copy-ready blocks."""
    st.markdown(
        '<h2 style="color:#63BCAF;font-size:24px;">Example messages</h2>',
        unsafe_allow_html=True,
    )

    major_tab, minor_tab, maintenance_tab, providers_tab, resolved_tab = st.tabs(
        [
            ":red[Major issue]",
            ":orange[Minor issue]",
            ":orange[Maintenance]",
            ":orange[Data providers]",
            ":green[Resolved]",
        ]
    )

    with major_tab:
        st.code(
            "We are currently investigating a major issue with the forecast, and will aim "
            "to resolve them as soon as possible. Please exercise caution when using the "
            "current forecast.",
            wrap_lines=True,
        )

    with minor_tab:
        st.code(
            "We are currently investigating minor issues with the forecast, and will aim "
            "to resolve them as soon as possible.",
            wrap_lines=True,
        )

    with maintenance_tab:
        st.code(
            "We are upgrading our infrastructure between {start_datetime} and "
            "{end_datetime}, and there may be some minor downtime. We hope to keep "
            "disruption to a minimum.",
            wrap_lines=True,
        )

    with providers_tab:
        st.code(
            "We are currently experiencing issues with a third-party NWP data provider, "
            "which may affect the forecast. We hope to resolve this as soon as possible.",
            wrap_lines=True,
        )
        st.code(
            "We are currently experiencing issues with a third-party satellite data "
            "provider, which may affect the forecast. We hope to resolve this as soon as "
            "possible.",
            wrap_lines=True,
        )
        st.code(
            "A solar eclipse is expected at {datetime}, please exercise caution around the "
            "forecast during this time.",
            wrap_lines=True,
        )

    with resolved_tab:
        st.code(
            "The {minor / major} issue with the forecast from {datetime} to {datetime} is "
            "now resolved. This was due to {reason}.",
            wrap_lines=True,
        )
        st.code(
            "The {minor / major} issue with the forecast from {datetime} to {datetime} "
            "{reason} has now been resolved.",
            wrap_lines=True,
        )
        st.code(
            "The {minor / major} issue with the forecast from {datetime} to {datetime} has "
            "now been resolved as of {fixed_date}.",
            wrap_lines=True,
        )

    st.markdown(
        "More examples in "
        "[Notion](https://www.notion.so/openclimatefix/Useful-Status-messages-d746d92701c8474293aedb12797b2d32).",  # noqa
    )


@st.cache_data(ttl=60)  # cache for 1 minute
def fetch_data_providers_status():
    """Fetch the status of data providers"""
    try:
        logging.info("Fetching data provider statuses...")
        response = requests.get(f"{STATUS_API_URL}/data/providers", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return None

@st.cache_data(ttl=60)  # cache for 1 minute
def get_eumetsat_details(satellite_id=None):
    try:
        url = f"{STATUS_API_URL}/data/providers/eumetsat?verbose=true"
        if satellite_id:
            url += f"&satelliteId={satellite_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch EUMETSAT details: {e}")
        return {}

def display_eumetsat_details(satellite_id, details=None):
    if details:
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            st.metric("Latest (UTC)", details.get("latestTimestamp", "-"))

        with col2:
            st.metric("Complete", details.get("complete", "-"))

        with col3:
            st.metric("Incomplete", details.get("incomplete", "-"))

        with col4:
            undelivered = details.get("undeliveredPlanned", 0) + details.get("undeliveredUnplanned", 0)
            st.metric("Undelivered", undelivered)
    with st.expander("Show full delivery timeline"):
        extra = get_eumetsat_details(satellite_id)
        result_data = extra.get("details", {}).get("results", [])

        if len(result_data) >= 2:
            records = result_data[0]
            headers = result_data[1]
            df = pd.DataFrame(records, columns=headers)
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime", ascending=False)

            # –– Add compact delivery chart ––
            # Melt for compact horizontal status chart
            df_melt = df.melt(
                id_vars="datetime",
                value_vars=["deliveryStatus", "timelyStatus"],
                var_name="category",
                value_name="status",
            )

            chart = alt.Chart(df_melt).mark_rect(height=12).encode(
                x=alt.X("datetime:T", title="Time", axis=alt.Axis(format="%H:%M")),
                y=alt.Y("category:N", title=""),
                color=alt.Color("status:N",
                                scale=alt.Scale(
                                    domain=["complete", "incomplete", "late", "onTime", "unavailable-unplanned", "unavailable-planned"],
                                    range=["#4caf50", "#f44336", "#ff9800", "#2196f3", "#f44336", "#9e9e9e"],
                                ),
                                # no title
                                legend=alt.Legend(title=None,
                                                  titlePadding=-15,
                                                  labelFontSize=10,
                                                  symbolSize=90,
                                                  padding=1,
                                                  offset=10,
                                                  ),
                                ),
                tooltip=[
                    alt.Tooltip("datetime:T", title="Timestamp", format="%Y-%m-%d %H:%M"),
                    alt.Tooltip("category:N", title="Type"),
                    alt.Tooltip("status:N", title="Status"),
                ],
            ).properties(
                height=110,
                width="container",
            )

            st.altair_chart(chart, use_container_width=True)

        else:
            st.info("No extended data available.")

def data_providers_status():
    """Display the status of data providers"""
    st.markdown(
        f'<h2 style="color:#63BCAF;font-size:24px;">{"Data Providers"}</h2>',
        unsafe_allow_html=True,
    )

    # Add css for making metrics smaller
    st.markdown(
        """
        <style>
            .stMetric > div * {
                font-size: 1.25rem !important;
            }
            .stMetric > label * {
                font-size: 0.875rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Fetch the latest status from the Status API
    data_statuses = fetch_data_providers_status()

    if data_statuses:
        # Display the status of each data provider
        for item in data_statuses:
            provider = item["provider"]
            source = item["source"]
            status = item["status"]
            msg = item["statusMessage"]
            details = item.get("details", {})
            status_page_link = item.get("statusPageUrl", "")

            emoji = "🟢" if status == "ok" else "🔴"

            col1, col2, col3 = st.columns([3, 1, 2])

            with col1:
                st.markdown(f"""<div style="font-size: 0.875rem">{source}</div>""", unsafe_allow_html=True)
                st.markdown(
                    f"<div style='font-size: 1.25rem; color:#ccc;'>{emoji} {provider} &nbsp;<a style='text-decoration: none; font-size: 0.875rem;' href='{status_page_link}' target='_blank' rel='noopener noreferrer'>🔗</a></div>",
                    unsafe_allow_html=True)

            with col2:
                st.metric("Status", status)

            with col3:
                st.markdown("""<div style="font-size: 0.875rem">Message</div>""", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.875rem; color:#ccc; margin-top: 0.25rem;'>{msg if msg else '–'}</div>", unsafe_allow_html=True)

            if provider == "EUMETSAT":
                satellite_id = "MET-11" if "MET 11" in source else "MET-10"
                # Display extra EUMETSAT details, with detailed delivery timeline, on request
                display_eumetsat_details(satellite_id, details)

            st.markdown("""<hr style="padding: 0; margin: 0;" />""", unsafe_allow_html=True)

    else:
        st.error("Failed to fetch data provider statuses.")


def status_page():
    """Main page for status"""
    st.set_page_config(layout="wide", page_title="OCF • Status", initial_sidebar_state="collapsed")

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Status Page"}</h1>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        ocf_status()
        example_status_messages()

    with col2:
        # Data providers status
        data_providers_status()


