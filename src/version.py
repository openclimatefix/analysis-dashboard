from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    try:
        return version("analysis-dashboard")
    except PackageNotFoundError:
        return "v?"
