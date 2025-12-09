"""Cache utilities for the forecast module."""

from datetime import UTC, datetime, timedelta

from dp_sdk.ocf import dp

from dataplatform.forecast.constant import cache_seconds


def key_builder_remove_client(func: callable, *args: list, **kwargs: dict) -> str:
    """Custom key builder that ignores the client argument for caching purposes."""
    key = f"{func.__name__}:"
    for arg in args:
        if not isinstance(arg, dp.DataPlatformDataServiceStub):
            key += f"{arg}-"

    for k, v in kwargs.items():
        key += f"{k}={v}-"

    # get the time now to the closest 5 minutes, this forces a new cache every 5 minutes
    current_time = datetime.now(UTC).replace(second=0, microsecond=0)
    current_time = current_time - timedelta(
        minutes=current_time.minute % (int(cache_seconds / 60)),
    )
    key += f"time={current_time}-"

    return key
