from datetime import datetime, timedelta

import streamlit as st


def make_recent_summary_stats(values, title:str = "Recent MAE"):
    day_before_yesterday, today, yesterday = get_recent_daily_values(values)

    with st.expander(title):
        st.subheader(title)
        t = datetime.today() - timedelta(days=1)
        t2 = datetime.today() - timedelta(days=2)
        t3 = datetime.today() - timedelta(days=3)
        col1, col2, col3 = st.columns([1, 1, 1])

        col1.metric(label=t3.strftime("%d/%m/%y"), value=day_before_yesterday)
        col2.metric(label=t2.strftime("%d/%m/%y"), value=yesterday)
        col3.metric(label=t.strftime("%d/%m/%y"), value=today)


def get_recent_daily_values(values):
    """
    Get the recent daily values from the metric values
    """
    if len(values) == 0:
        day_before_yesterday = None
        yesterday = None
        today = None
    elif len(values) == 1:
        day_before_yesterday = None
        yesterday = None
        today = values[len(values) - 1]
    elif len(values) == 2:
        day_before_yesterday = None
        yesterday = values[len(values) - 2]
        today = values[len(values) - 1]
    else:
        day_before_yesterday = values[len(values) - 3]
        yesterday = values[len(values) - 2]
        today = values[len(values) - 1]

    return day_before_yesterday, yesterday, today
