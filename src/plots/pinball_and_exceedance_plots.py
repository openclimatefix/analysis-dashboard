""" Make pinball and exceedance plots."""
from datetime import datetime
import pandas as pd
from typing import List

from sqlalchemy.orm import Session
import plotly.graph_objects as go
from nowcasting_datamodel.models.metric import MetricValue

from get_data import get_metric_value
from .utils import line_color


def make_pinball_or_exceedance_plot(
    session: Session,
    forecast_horizon_selection: List[int],
    starttime: datetime,
    endtime: datetime,
    model_name: str,
    metric_name: str,
):
    """Make pinball or exceedance plot."""

    assert metric_name in ["Pinball loss", "Exceedance"]

    if metric_name == "Pinball loss":
        x_label = "MAE [MW]"
    else:
        x_label = "Exceedance [%]"

    # make plot
    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text=f'{metric_name} {model_name}'),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text=x_label)),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    avergae_values = []
    for plevel in [10, 90]:
        for i, forecast_horizon in enumerate(forecast_horizon_selection):
            # read database metric values
            metric_values = get_metric_value(
                session=session,
                name=metric_name,
                gsp_id=0,
                forecast_horizon_minutes=forecast_horizon,
                start_datetime_utc=starttime,
                end_datetime_utc=endtime,
                model_name=model_name,
                plevel=plevel,
            )
            metric_values = [MetricValue.from_orm(value) for value in metric_values]
            average_value = sum(value.value for value in metric_values) / len(metric_values)

            # format
            x_horizon = [value.datetime_interval.start_datetime_utc for value in metric_values]
            y_horizon = [round(float(value.value), 2) for value in metric_values]

            # add to plot
            fig.add_traces(
                [
                    go.Scatter(
                        x=x_horizon,
                        y=y_horizon,
                        name=f"p{plevel}_{forecast_horizon}-minute horizon",
                        mode="lines",
                        line=dict(color=line_color[i%len(line_color)]),
                    )
                ]
            )
            avergae_values.append(
                {
                    "plevel": f'p{plevel}',
                    "forecast_horizon": forecast_horizon,
                    "average_value": average_value,
                }
            )

    average_values = pd.DataFrame(avergae_values)

    # pivot by plevel, to level the columns forecast_horizon, p10, p90
    average_values = average_values.pivot(
        index="forecast_horizon", columns="plevel", values="average_value"
    )
    return fig, average_values
