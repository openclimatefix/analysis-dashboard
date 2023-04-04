""" 
Internal UI for OCF 
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

import logging
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

st.sidebar.title("Navigation")
st.sidebar.subheader("Select Date Range")
starttime = st.sidebar.date_input("Start Date", datetime(2022, 12, 6))
endtime = st.sidebar.date_input("End Date", datetime(2023, 1, 2))

#create columns with the actual MAE values for yesterday and today

# select mae for a single day

# ask peter if I'm getting the right number

url = "postgresql://main:lnOgnQV8b9le1liM@localhost:5433/forecastdevelopment"
connection = DatabaseConnection(url=url, echo=True)

st.title("OCF Dashboard")

# DATE_TIME = 'created_utc'
# ID = 'id'
# DATA_FILE = ('metrics_data.csv')


# def load_data():
#     df = pd.read_csv(DATA_FILE)
#     return df



st.subheader('Daily Latest Mean Absolute Error')
# st.write('visualizing data from metrics_data.csv')

# def load_data():
#     df = pd.read_csv(DATA_FILE)
#     return df

# st.write(load_data())

# def make_line_chart():
#     df = pd.read_csv(DATA_FILE)
#     df.columns = df.columns.str.replace("created_utc", "Date")
#     df.columns = df.columns.str.replace("value", "Value (MW)")
#     df['Only Date'] = pd.to_datetime(df['Date'])
    
#     return df

# st.line_chart(data=make_line_chart(), y="Value (MW)", x="Only Date")

# with st.expander("*Mean Absolute Error"):
#     st.write("This metric calculates the MAE for the latest OCF forecast and compares with the PVLive values. The data is from one day.")




# # get gsp yields from database
# with connection.get_session() as session:
#     # read database
#     gsp_yields = get_gsp_yield(
#         session=session,
#         gsp_ids=range(0, 1),  # could be 0 to 318
#         start_datetime_utc=(starttime),
#         end_datetime_utc=(endtime),
#     )

#     # list of pydantic objects
#     gsp_yields = [GSPYield.from_orm(gsp_yield) for gsp_yield in gsp_yields]

#     x_pv_live = [gsp_yield.datetime_utc for gsp_yield in gsp_yields]
#     y_pv_live = [gsp_yield.solar_generation_kw / 1000 for gsp_yield
#                  in gsp_yields]

# # get latest forecasts from database
# with connection.get_session() as session:
#     #read database 
#     forecasts = get_latest_forecast_for_gsps(
#         session=session,
#         gsp_ids=range(0, 1),
#         historic=True,
#         start_target_time=datetime(2022, 12, 6),
#         end_target_time=datetime(2022, 12, 25),
#     )

#     forecasts = [Forecast.from_orm_latest(forecast) for forecast in forecasts]


# x_forecast = [forecast_value.target_time for forecast_value in forecasts[0].forecast_values]
# y_forecast = [
#     forecast_value.expected_power_generation_megawatts
#     for forecast_value in forecasts[0].forecast_values
# ]
# df = pd.DataFrame(
#     {
#     "x_forecast": x_forecast,
#     "y_forecast": y_forecast,
#     }
# )

# df2 = pd.DataFrame(
#      {
#     "x_pv_live": x_pv_live,
#     "y_pv_live": y_pv_live,
#     }
# )

# st.write('Attempts at visualizing data from the database')
# st.subheader('Dataframe with pv actual numbers and a chart')
# st.write(df2)
# st.line_chart(data=df2, x="x_pv_live", y="y_pv_live")
# st.area_chart(data=df, x="x_forecast", y="y_forecast")

# got an error when I didn't connect to the database so am connecting here again
url = "postgresql://main:lnOgnQV8b9le1liM@localhost:5433/forecastdevelopment"
connection = DatabaseConnection(url=url, echo=True)

with connection.get_session() as session:
    # read database metric values 

    metric_values = get_metric_value(
        session=session,
        name="Daily Latest MAE",
        gsp_id=0,
        start_datetime_utc=starttime,
        end_datetime_utc=endtime,
    )



    #transform SQL object into something readable
    metric_values = [MetricValue.from_orm(value) for value in metric_values]

    #select data to show in the chart mean absolute error and date from the above date range 
    x_mae = [value.datetime_interval.start_datetime_utc for value in metric_values]
    y_mae = [round(float(value.value),2) for value in metric_values]
    
col1, col2 = st.columns([2, 2])
col1.subheader("Today's MAE")
col1.metric(label="Today's MAE", value=round(float(y_mae[0]), 2))

col2.subheader("Yesterday's MAE")
col2.metric(label="Yesterday's MAE", value=round(float(y_mae[1]),2))

st.title("Nowcasting Forecast MAE") 

df = pd.DataFrame(
    {
    "MAE": y_mae,
    "date_time_utc": x_mae,
    }
)

st.sidebar.subheader("Choose Chart Type")
chart = st.sidebar.radio("Select", ("Bar Chart", "Line Chart", "Line & Bar Chart"))

if chart == "Bar Chart":
    fig = px.bar(df, x="date_time_utc", y="MAE", title='MAE Nowcasting Forecast', hover_data=['MAE'], color_discrete_sequence=['#FFD053'],)
    st.plotly_chart(fig, theme="streamlit")
elif chart == "Line Chart":
    fig = px.line(df, x="date_time_utc", y="MAE", title='MAE Nowcasting Forecast', hover_data=['MAE'], color_discrete_sequence=['#FCED4D'],)
    st.plotly_chart(fig, theme="streamlit")
else: 
     fig = px.bar(df, x="date_time_utc", y="MAE", title='MAE Nowcasting Forecast', hover_data=['MAE'], color_discrete_sequence=['#FFD053'],)
     st.plotly_chart(fig, theme="streamlit")

     fig = px.line(df, x="date_time_utc", y="MAE", title='MAE Nowcasting Forecast', hover_data=['MAE'], color_discrete_sequence=['#FCED4D'],)
     st.plotly_chart(fig, theme="streamlit")
   

st.subheader('Raw Data')
df = pd.DataFrame(
    {
    "MAE": y_mae,
    "date_time_utc": x_mae,
     }
)

st.write(df)