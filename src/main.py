""" 
Internal UI for OCF 
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

from datetime import datetime, timezone, timedelta 
from typing import List, Optional

from sqlalchemy.orm.session import Session
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.read.read_gsp import get_gsp_yield
from nowcasting_datamodel.read.read import get_latest_forecast_for_gsps
from nowcasting_datamodel.models.gsp import GSPYield
from nowcasting_datamodel.models.forecast import Forecast
from nowcasting_datamodel.models.gsp import LocationSQL
from nowcasting_datamodel.models.metric import MetricValueSQL, MetricSQL, MetricValue, DatetimeIntervalSQL
from get_data import get_metric_value, get_metric, get_datetime_interval

st.get_option("theme.primaryColor")
# set up title and subheader
st.markdown(f'<h1 style="color:#FFD053;font-size:48px;">{"OCF Dashboard"}</h1>', unsafe_allow_html=True)
# set up sidebar
st.sidebar.subheader("Select date range for charts")
# select start and end date
starttime = st.sidebar.date_input("Start Date", datetime.today()-timedelta(days=30))
endtime = st.sidebar.date_input("End Date", datetime.today())


# set up database connection
url = os.environ["DB_URL"]
connection = DatabaseConnection(url=url, echo=True)

# get metrics for comparing MAE and RMSE without forecast horizon

with connection.get_session() as session:
    
    # read database metric values 

        metric_values_mae = get_metric_value(
            session=session,
            name="Daily Latest MAE",
            gsp_id=0,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime
            )

        metric_values_rmse = get_metric_value(
            session=session,
            name="Daily Latest RMSE",
            gsp_id=0,
            start_datetime_utc=starttime,
            end_datetime_utc=endtime
            )
    

    #transform SQL object into something readable
        metric_values_mae = [MetricValue.from_orm(value) for value in metric_values_mae]

    #select data to show in the chart MAE and RMSE and date from the above date range 
        x_mae = [value.datetime_interval.start_datetime_utc for value in metric_values_mae]

        y_mae = [round(float(value.value), 2) for value in metric_values_mae]

#getting recent statistics for the dashboard
        day_before_yesterday_mae = y_mae[len( y_mae)-3]
        yesterday_mae = y_mae[len( y_mae)-2] 
        today_mae =  y_mae[len(y_mae)-1]  
    
        metric_values_rmse = [MetricValue.from_orm(value) for value in metric_values_rmse]

        y_rmse = [round(float(value.value), 2) for value in metric_values_rmse]
    
        x_rmse = [value.datetime_interval.start_datetime_utc for value in metric_values_rmse]
        
# getting recent rmse statistics for the dashboard
        day_before_yesterday_rmse = y_rmse[len(y_rmse)-3]
        yesterday_rmse = y_rmse[len(y_rmse)-2] 
        today_rmse = y_rmse[len(y_rmse)-1] 

st.markdown(f'<h1 style="color:#63BCAF;font-size:48px;">{"Nowcasting Forecast Statistics"}</h1>', unsafe_allow_html=True)

with st.expander("Recent MAE Values"):
    st.subheader("Recent MAE")
    t = datetime.today()-timedelta(days=1)
    t2 = datetime.today()-timedelta(days=2)
    t3 = datetime.today()-timedelta(days=3)
    col1, col2, col3 = st.columns([1, 1, 1])

    col1.metric(label=t3.strftime("%d/%m/%y"), value=day_before_yesterday_mae)
    col2.metric(label=t2.strftime("%d/%m/%y"), value=yesterday_mae)
    col3.metric(label=t.strftime("%d/%m/%y"), value=today_mae)

with st.expander("Recent RMSE Values"):
    st.subheader("Recent RMSE")
    col1, col2, col3 = st.columns([1, 1, 1])
    col1.metric(label=t3.strftime("%d/%m/%y"), value=day_before_yesterday_rmse)
    col2.metric(label=t2.strftime("%d/%m/%y"), value=yesterday_rmse)
    col3.metric(label=t.strftime("%d/%m/%y"), value=today_rmse)

df_mae = pd.DataFrame(
    {
    "MAE": y_mae,
    "datetime_utc": x_mae,
    }
)

df_rmse = pd.DataFrame(
    {
    "RMSE": y_rmse,
    "datetime_utc": x_rmse,
    }
)

# st.sidebar.subheader("Select Chart Type")
# chart = st.sidebar.radio("Select", ("Bar Chart", "Line Chart", "Chart with Forecast Horizon"))

st.sidebar.subheader("Select Forecast Horizon")
forecast_horizon_selection = st.sidebar.multiselect("Select", [60, 120, 180, 240, 300, 360, 420])

# set up title and subheader

fig = px.bar(df_mae, x="datetime_utc", y="MAE", title='MAE Nowcasting', hover_data=['MAE'], color_discrete_sequence=['#FFAC5F'],)
st.plotly_chart(fig, theme="streamlit")

fig2 = px.line(df_mae, x="datetime_utc", y="MAE", title='MAE Nowcasting Forecast', hover_data=['MAE'], color_discrete_sequence=['#FFD053'],)

    
with connection.get_session() as session:
    # read database metric values
    for forecast_horizon in forecast_horizon_selection:
        
        metric_values = get_metric_value(
                    session=session,
                    name="Daily Latest MAE",
                    gsp_id=0,
                    forecast_horizon_minutes=forecast_horizon,
                    start_datetime_utc=starttime,
                    end_datetime_utc=endtime,
            )
        metric_values = [MetricValue.from_orm(value) for value in metric_values]
        x_mae_horizon = [value.datetime_interval.start_datetime_utc for value in metric_values]
        y_mae_horizon = [round(float(value.value), 2) for value in metric_values]

        df = pd.DataFrame(
                {
                "MAE": y_mae_horizon,
                "datetime_utc": x_mae_horizon,
             }
            )
        fig2.add_traces([go.Scatter(x=df["datetime_utc"], y=df["MAE"], name=f"{forecast_horizon}-minute horizon",)]) 

    st.plotly_chart(fig2, theme="streamlit")

# comparing MAE and RMSE
fig3=px.line(df_mae, x="datetime_utc", y="MAE", title='Nowcasting MAE with RMSE for Comparison', hover_data=['MAE'], color_discrete_sequence=['#FFD053', '#FFAC5F', '#ff9736', "#7BCDF3", "#086788", "#63BCAF","#4C9A8E"],)

fig3.add_traces(go.Scatter(x=df_rmse["datetime_utc"], y=df_rmse["RMSE"], name="RMSE",))
st.plotly_chart(fig3, theme="streamlit")
# set up title and subheader

st.subheader('Raw Data')
col1, col2 = st.columns([1, 1])
col1.write(df_mae)
col2.write(df_rmse)

# color_discrete_sequence=['#FFD053', '#FFAC5F', '#ff9736', "#7BCDF3", "#086788", "#63BCAF","#4C9A8E"]