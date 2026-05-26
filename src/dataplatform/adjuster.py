"""Data Platform Adjuster Streamlit Page.

Loads adjuster (week-average delta) values from the Data Platform
and plots delta_fraction vs forecast horizon.
"""

import asyncio
import os
from datetime import UTC, datetime, time

import grpc.aio
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from aiocache import Cache, cached
from ocf.dp.dp import common_pb2
from ocf.dp.dp_data import messages_pb2, service_pb2_grpc

from dataplatform.forecast.cache import key_builder_remove_client
from dataplatform.forecast.constant import cache_seconds, observer_names
from dataplatform.forecast.setup import get_forecasters, get_location_names


@cached(ttl=cache_seconds, cache=Cache.MEMORY, key_builder=key_builder_remove_client)
async def get_observer_names(
    client: service_pb2_grpc.DataPlatformDataServiceStub,
) -> list[str]:
    """Get all observer names from the Data Platform."""
    response = await client.ListObservers(messages_pb2.ListObserversRequest())
    names = sorted({o.observer_name for o in response.observers})
    return names or list(observer_names)


async def get_week_average_deltas(
    client: service_pb2_grpc.DataPlatformDataServiceStub,
    location: messages_pb2.ListLocationsResponse.LocationSummary,
    forecaster: messages_pb2.Forecaster,
    observer_name: str,
    pivot_timestamp_utc: datetime,
) -> messages_pb2.GetWeekAverageDeltasResponse:
    """Call the GetWeekAverageDeltas API."""
    request = messages_pb2.GetWeekAverageDeltasRequest(
        location_uuid=location.location_uuid,
        energy_source=common_pb2.EnergySource.ENERGY_SOURCE_SOLAR,
        pivot_timestamp_utc=pivot_timestamp_utc,
        forecaster=messages_pb2.Forecaster(
            forecaster_name=forecaster.forecaster_name,
            forecaster_version=forecaster.forecaster_version,
        ),
        observer_name=observer_name,
    )
    return await client.GetWeekAverageDeltas(request)


def dp_adjuster_page() -> None:
    """Wrapper to run the async adjuster page."""
    asyncio.run(_async_dp_adjuster_page())


async def _async_dp_adjuster_page() -> None:
    """Async adjuster page that loads values from the Data Platform."""
    st.markdown(
        '<h1 style="color:#63BCAF;font-size:48px;">DP Adjuster</h1>',
        unsafe_allow_html=True,
    )
    st.write(
        "This page loads week-average delta (adjuster) values from the Data Platform "
        "and plots them against forecast horizon.",
    )

    data_platform_host = os.getenv("DATA_PLATFORM_HOST", "localhost")
    data_platform_port = int(os.getenv("DATA_PLATFORM_PORT", "50051"))
    channel = grpc.aio.insecure_channel(f"{data_platform_host}:{data_platform_port}")
    client = service_pb2_grpc.DataPlatformDataServiceStub(channel)

    # Location type + location
    location_types = [
        common_pb2.LocationType.LOCATION_TYPE_NATION,
        common_pb2.LocationType.LOCATION_TYPE_STATE,
        common_pb2.LocationType.LOCATION_TYPE_GSP,
        common_pb2.LocationType.LOCATION_TYPE_SITE,
    ]
    location_type = st.sidebar.selectbox(
        "Select a Location Type",
        location_types,
        format_func=lambda v: common_pb2.LocationType.Name(v).removeprefix(
            "LOCATION_TYPE_",
        ),
        index=0,
        key="adjuster_location_type",
    )
    location_names = {
        k: v for k, v in (await get_location_names(client)).items()
        if v.location_type == location_type
    }
    if not location_names:
        st.warning("No locations found for the selected location type.")
        return
    selected_location_name = st.sidebar.selectbox(
        "Select a Location",
        location_names.keys(),
        index=0,
        key="adjuster_location",
    )
    selected_location = location_names[selected_location_name]

    # Forecaster (single select — adjuster is per-forecaster)
    forecasters = await get_forecasters(client)
    forecaster_labels = {
        f"{f.forecaster_name}:{f.forecaster_version}": f for f in forecasters
    }
    forecaster_keys = sorted(forecaster_labels.keys())
    default_index = next(
        (i for i, k in enumerate(forecaster_keys) if k.startswith("pvnet_v2:")),
        0,
    )
    selected_forecaster_key = st.sidebar.selectbox(
        "Select a Forecaster",
        forecaster_keys,
        index=default_index,
        key="adjuster_forecaster",
    )
    selected_forecaster = forecaster_labels[selected_forecaster_key]

    # Observer name
    all_observer_names = await get_observer_names(client)
    default_obs_index = (
        all_observer_names.index("pvlive_day_after")
        if "pvlive_day_after" in all_observer_names
        else 0
    )
    selected_observer_name = st.sidebar.selectbox(
        "Select an Observer",
        all_observer_names,
        index=default_obs_index,
        key="adjuster_observer",
    )

    # Pivot datetime — date + init time of day
    now = datetime.now(tz=UTC)
    pivot_date = st.sidebar.date_input(
        "Pivot date (UTC)",
        now.date(),
        key="adjuster_pivot_date",
    )
    pivot_time = st.sidebar.time_input(
        "Init time of day (UTC)",
        time(hour=now.hour, minute=0),
        key="adjuster_pivot_time",
    )
    pivot_timestamp_utc = datetime.combine(pivot_date, pivot_time).replace(
        tzinfo=UTC,
    )

    st.write(
        f"Location: `{selected_location.location_name}` "
        f"(`{selected_location.location_uuid}`)",
    )
    st.write(
        f"Forecaster: `{selected_forecaster.forecaster_name}:"
        f"{selected_forecaster.forecaster_version}`",
    )
    st.write(f"Observer: `{selected_observer_name}`")
    st.write(f"Pivot timestamp (UTC): `{pivot_timestamp_utc.isoformat()}`")

    try:
        response = await get_week_average_deltas(
            client=client,
            location=selected_location,
            forecaster=selected_forecaster,
            observer_name=selected_observer_name,
            pivot_timestamp_utc=pivot_timestamp_utc,
        )
    except Exception as e:  # noqa: BLE001
        st.error(f"Failed to fetch adjuster values: {e}")
        return

    if not response.deltas:
        st.warning("No adjuster values returned for this selection.")
        return

    df = pd.DataFrame(
        [
            {
                "horizon_mins": d.horizon_mins,
                "delta_fraction": d.delta_fraction,
                "effective_capacity_watts": int(d.effective_capacity_watts),
            }
            for d in response.deltas
        ],
    ).sort_values("horizon_mins")
    df["delta_watts"] = df["delta_fraction"] * df["effective_capacity_watts"]

    st.write(f"Init time of day (from response): `{response.init_time_of_day}`")

    fig = go.Figure(
        data=go.Scatter(
            x=df["horizon_mins"],
            y=df["delta_fraction"],
            mode="lines+markers",
            name="delta_fraction",
        ),
        layout=go.Layout(
            title=(
                f"Week-Average Delta for {selected_forecaster.forecaster_name} "
                f"@ {selected_location.location_name}"
            ),
            xaxis=go.layout.XAxis(
                title=go.layout.xaxis.Title(text="Forecast Horizon [minutes]"),
            ),
            yaxis=go.layout.YAxis(
                title=go.layout.yaxis.Title(text="Delta [fraction of capacity]"),
            ),
        ),
    )
    st.plotly_chart(fig, theme="streamlit")

    fig_watts = go.Figure(
        data=go.Scatter(
            x=df["horizon_mins"],
            y=df["delta_watts"],
            mode="lines+markers",
            name="delta_watts",
        ),
        layout=go.Layout(
            title="Week-Average Delta (watts)",
            xaxis=go.layout.XAxis(
                title=go.layout.xaxis.Title(text="Forecast Horizon [minutes]"),
            ),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Delta [W]")),
        ),
    )
    st.plotly_chart(fig_watts, theme="streamlit")

    st.subheader("Adjuster Values")
    st.dataframe(df)

    st.download_button(
        label="⬇️ Download adjuster values",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=(
            f"adjuster_{selected_location.location_uuid}_"
            f"{selected_forecaster.forecaster_name}_"
            f"{pivot_timestamp_utc.date()}.csv"
        ),
        mime="text/csv",
    )

# Required for the tests to run this as a script
if __name__ == "__main__":
    dp_adjuster_page()
