""" 
Internal UI for OCF 
"""

import streamlit as st
import pandas as pd
import numpy as np

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


st.title("OCF Dashboard")

DATE_TIME = 'created_utc'
ID = 'id'
DATA_FILE = ('metrics_data.csv')


def load_data():
    df = pd.read_csv(DATA_FILE)
    return df



st.subheader('Daily Latest MAE*')
st.write('visualizing data from metrics_data.csv')

def load_data():
    df = pd.read_csv(DATA_FILE)
    return df

st.write(load_data())

def make_line_chart():
    df = pd.read_csv(DATA_FILE)
    df.columns = df.columns.str.replace("created_utc", "Date")
    df.columns = df.columns.str.replace("value", "Value (MW)")
    df['Only Date'] = pd.to_datetime(df['Date']).dt.date
    
    return df

st.line_chart(data=make_line_chart(), y="Value (MW)", x="Only Date")

with st.expander("*Mean Absolute Error"):
    st.write("This metric calculates the MAE for the latest OCF forecast and compares with the PVLive values. The data is from one day.")



url = "postgresql://main:lnOgnQV8b9le1liM@localhost:5433/forecastdevelopment"
connection = DatabaseConnection(url=url, echo=True)
# get gsp yields from database
with connection.get_session() as session:
    # read database
    gsp_yields = get_gsp_yield(
        session=session,
        gsp_ids=range(0, 1),  # could be 0 to 318
        start_datetime_utc=datetime(2022, 12, 6),
        end_datetime_utc=datetime(2022, 12, 25),
    )

    # list of pydantic objects
    gsp_yields = [GSPYield.from_orm(gsp_yield) for gsp_yield in gsp_yields]

    x_pv_live = [gsp_yield.datetime_utc for gsp_yield in gsp_yields]
    y_pv_live = [gsp_yield.solar_generation_kw / 1000 for gsp_yield in gsp_yields]

# get latest forecasts from database
with connection.get_session() as session:
    #read database 
    forecasts = get_latest_forecast_for_gsps(
        session=session,
        gsp_ids=range(0, 1),
        historic=True,
        start_target_time=datetime(2022, 12, 6),
        end_target_time=datetime(2022, 12, 25),
    )

    forecasts = [Forecast.from_orm_latest(forecast) for forecast in forecasts]
    print(forecasts)


x_forecast = [forecast_value.target_time for forecast_value in forecasts[0].forecast_values]
y_forecast = [
    forecast_value.expected_power_generation_megawatts
    for forecast_value in forecasts[0].forecast_values
]
df = pd.DataFrame(
    {
    "x_forecast": x_forecast,
    "y_forecast": y_forecast,
    }
)

df2 = pd.DataFrame(
     {
    "x_pv_live": x_pv_live,
    "y_pv_live": y_pv_live,
    }
)

st.write('Attempts at visualizing data from the database')
st.subheader('Dataframe with pv actual numbers')
st.write(df2)


st.area_chart(data=df, x="x_forecast", y="y_forecast")

st.line_chart(data=df2, x="x_pv_live", y="y_pv_live")

# got an error when I didn't connect to the database so am connecting here again
url = "postgresql://main:lnOgnQV8b9le1liM@localhost:5433/forecastdevelopment"
connection = DatabaseConnection(url=url, echo=True)

with connection.get_session() as session:
    # read database
    metric_values = get_metric_value(
        session=session,
        name="Daily Latest MAE",
        gsp_id=range(0, 1),
        start_datetime_utc=datetime(2022, 9, 11),
        end_datetime_utc=datetime(2022, 11, 29),
    )


    values = [MetricValue.from_orm(value) for value in metric_values]

    x_mae = [metric_value.created_utc for metric_value in values]
    y_mae = [metric_value.value for metric_value in values]

st.write('Should be MAE numbers but only get an empty dataframe')
df = pd.DataFrame(
    {"y_mae_value": x_mae,
     "x_mae_value": y_mae}
)

st.write(df)

st.line_chart(data=df, x="x_mae_value", y="y_mae_value")

print(df)

