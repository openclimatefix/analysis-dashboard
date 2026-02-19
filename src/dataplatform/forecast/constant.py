"""Constants for the forecast module."""

colours = [
    "#FFD480",
    "#FF8F73",
    "#4675C1",
    "#65B0C9",
    "#58B0A9",
    "#FAA056",
    "#306BFF",
    "#FF4901",
    "#B701FF",
    "#17E58F",
]

metrics = {
    "MAE": "MAE is absolute mean error, average(abs(forecast-actual))",
    "ME": "ME is mean (bias) error, average((forecast-actual))",
}

cache_seconds = 300  # 5 minutes

# This is used for a specific case for the UK National and GSP
observer_names = ["pvlive_in_day", "pvlive_day_after", "nednl"]
