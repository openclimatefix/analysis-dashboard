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

# Charts rendered standalone (in an iframe, to keep Plotly animation frames working) don't
# inherit the Streamlit theme, so they have to restate it. Keep in sync with
# .streamlit/config.toml.
theme_background = "#0E1117"
theme_text = "#E4E4E4"
# The animated by-t0 chart sizes itself to a fraction of the viewer's screen height (so it
# fits laptop screens as well as large monitors) rather than a fixed pixel height. The panels
# are then proportioned via Plotly row_heights: main / delta / adjuster ≈ 50 / 25 / 25.
t0_chart_screen_fraction = 0.85
t0_chart_min_height = 480

# This is used for a specific case for the UK National and GSP
observer_names = ["pvlive_in_day", "pvlive_day_after", "nednl"]
