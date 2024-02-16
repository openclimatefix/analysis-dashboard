from nowcasting_datamodel.models import MetricValue

line_color = [
    "#9EC8FA",
    "#9AA1F9",
    "#FFAC5F",
    "#9F973A",
    "#7BCDF3",
    "#086788",
    "#63BCAF",
    "#4C9A8E",
]
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


def hex_to_rgb(value):
    value = value.lstrip("#")
    lv = len(value)
    return tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3))


def get_colour_from_model_name(model_name, opacity=1.0):

    # get colour from model, some models have a space and a datetime
    model_name_only = model_name.split(" ")[0]
    colour = colour_per_model.get(model_name_only, "#FFFFFF")
    if "PVLive" in model_name:
        colour = colour_per_model.get(model_name, "#FFFFFF")

    # change opacity to hex
    rgb = hex_to_rgb(colour)

    # add opacity
    colour = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{opacity})"

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


MAE_LIMIT_DEFAULT = 800
MAE_LIMIT_DEFAULT_HORIZON_0 = 300
