import pandas as pd
import plotly.graph_objects as go
from pvsite_datamodel.read.user import get_user_by_email
from pvsite_datamodel.read.site import get_sites_from_user
import streamlit as st

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


def make_api_frequency_requests_plot(
    api_requests: pd.DataFrame, email_selected: str, end_time: datetime, start_time: datetime
):
    """
    Make plot of API frequency requests

    Parameters
    ----------
    api_requests : pd.DataFrame, need to have columns "date" and "url"
    email_selected : str, email of user
    end_time : datetime, end time of plot
    start_time : datetime, start time of plot

    """

    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(
                text=f"Number of API requests for {email_selected} between {start_time} and {end_time}"
            ),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Numer of API requests")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )
    fig.add_trace(
        go.Bar(
            x=api_requests["date"],
            y=api_requests["url"],
            name="API requests",
        )
    )
    fig.update_yaxes(visible=False)
    return fig

def make_sites_over_time_plot(session, email):
    """
    Create a bar chart showing the cumulative number of sites forecasted for a user over time.
    
    Args:
        session: SQLAlchemy session object.
        email (str): Email of the user.
    
    Returns:
        plotly.graph_objects.Figure: The bar chart figure.
    """
    # Get user and their sites
    user = get_user_by_email(session=session, email=email)
    sites = get_sites_from_user(session=session, user=user)
    
    # Convert sites to a DataFrame
    sites_df = pd.DataFrame([site.__dict__ for site in sites], columns=["created_utc"])
    sites_df['created_utc'] = pd.to_datetime(sites_df['created_utc'])
    #printout number of sites to doublecheck
    
    # Group by month and calculate cumulative counts
    monthly_cumulative = sites_df.groupby(pd.Grouper(key='created_utc', freq='ME')).size().cumsum()

    
    # Create the line graph
    fig = go.Figure(
        data=go.Scatter(x=monthly_cumulative.index, y=monthly_cumulative, mode='lines+markers', name="Sites"),
        layout=dict(
            title=f'Increase in Number of Sites Over Time for {email}',
            xaxis_title="Date",
            yaxis_title="Cumulative Number of Sites",
            showlegend=True
        )
    )

    # Display the graph in Streamlit
    st.plotly_chart(fig, theme="streamlit")