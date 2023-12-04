import pandas as pd
from plotly import graph_objects as go

from datetime import datetime


def make_api_requests_plot(
    api_requests: pd.DataFrame, email_selected: str, end_time: datetime, start_time: datetime
):
    """
    Make plot of API requests

    Parameters
    ----------
    api_requests : pd.DataFrame, need to have columns "created_utc" and "url"
    email_selected : str, email of user
    end_time : datetime, end time of plot
    start_time : datetime, start time of plot

    """

    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(
                text=f"Api requests for {email_selected} between {start_time} and {end_time}"
            ),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="API request")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=api_requests["created_utc"],
            y=api_requests["url"],
            mode="markers",
            name="API requests",
        )
    )
    fig.update_yaxes(visible=False)
    return fig
