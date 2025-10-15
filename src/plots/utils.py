from itertools import cycle
from nowcasting_datamodel.read.read_models import get_models
import os
from datetime import datetime, timedelta
import plotly.express as px

PALETTE = px.colors.qualitative.Dark24

colour_per_model = {
    "cnn": "#FFD053",
    "National_xg": "#7BCDF3",
    "pvnet_v2": "#4c9a8e",
    "pvnet_gsp_sum": "#7e47d6",
    "blend": "#FF9736",
    "PVLive Initial Estimate": "#e4e4e4",
    "PVLive Updated Estimate": "#e4e4e4",
    "PVLive GSP Sum Estimate": "#FF9736",
    "PVLive GSP Sum Updated": "#FF9736",
}

# Make a cycle for extra models not in colour_per_model
# Skip first 3 colours as they are too similar to colours in colour_per_model

def hex_to_rgb(value):
    value = value.lstrip("#")
    lv = len(value)
    return tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3))


def get_colour_from_model_name(model_name, opacity=1.0):
    """Get colour from model label"""
    if "PVLive" in model_name:
        return colour_per_model.get(model_name, "#e4e4e4")
    else:
        # Some models have a space and a datetime
        model_name_only = model_name.split(" ")[0]
        if model_name_only in colour_per_model:
            colour = colour_per_model[model_name_only]
        else:
            idx = abs(hash(model_name_only)) % len(PALETTE)
            colour = PALETTE[idx]
            colour_per_model[model_name_only] = colour
    return colour


def get_x_y(metric_values):
    """
    Extra x and y values from the metric values

    x is the time
    y is the metric value
    """

    # select data to show in the chart MAE and RMSE and date from the above date range
    x = [value.datetime_interval.start_datetime_utc for value in metric_values]
    y = [round(float(value.value), 2) for value in metric_values]

    return x, y


def model_is_probabilistic(model_name):
    """Return whether the model is probabilistic given its name"""
    is_prob = (
        (model_name in ["National_xg", "blend"])
        or
        (model_name.startswith("pvnet") and not model_name.endswith("_gsp_sum"))
    )
    return is_prob


def model_is_gsp_regional(model_name):
    """Return whether the model has GSP results given its name"""
    is_regional = (
        (model_name=="cnn")
        or
        (model_name.startswith("pvnet") and not model_name.endswith("_gsp_sum"))
    )
    return is_regional


def get_recent_available_model_names(session):
    """Get recent available model names"""

    available_models = get_models(
        session=session,
        with_forecasts=True,
        forecast_created_utc=datetime.today() - timedelta(days=7),
    )
    available_models = [model.name for model in available_models]

    show_gsp_sum = os.getenv("SHOW_PVNET_GSP_SUM", "False").lower() == "true"
    
    if not show_gsp_sum:
        available_models = [m for m in available_models if not m.endswith("_gsp_sum")]
    return available_models


MAE_LIMIT_DEFAULT = 800
MAE_LIMIT_DEFAULT_HORIZON_0 = 300
