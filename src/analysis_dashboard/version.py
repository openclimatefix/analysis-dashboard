from importlib.metadata import version, PackageNotFoundError

def get_version() -> str:
    try:
        return version("analysis-dashboard")
    except PackageNotFoundError:
        return "unknown"
