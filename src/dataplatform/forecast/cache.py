from dp_sdk.ocf import dp


def key_builder_remove_client(func, *args, **kwargs):
    """Custom key builder that ignores the client argument for caching purposes."""
    key = f"{func.__name__}:"
    for arg in args:
        if not isinstance(arg, dp.DataPlatformDataServiceStub):
            key += f"{arg}-"

    for k, v in kwargs.items():
        key += f"{k}={v}-"

    print(key)

    return key
