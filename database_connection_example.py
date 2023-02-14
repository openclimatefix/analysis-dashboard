# import packages
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.read.read_gsp import get_gsp_yield
from nowcasting_datamodel.read.read import get_latest_forecast_for_gsps
from nowcasting_datamodel.models.gsp import GSPYield
from nowcasting_datamodel.models.forecast import Forecast
from datetime import datetime

# make connection
url = "postgresql://main:lnOgnQV8b9le1liM@localhost:5433/forecastdevelopment"
connection = DatabaseConnection(url=url, echo=True)


# get gsp yields
with connection.get_session() as session:
    # read database
    gsp_yields = get_gsp_yield(
        session=session,
        gsp_ids=range(0, 1),  # could be 0 to 318
        start_datetime_utc=datetime(2022, 7, 1),
        end_datetime_utc=datetime(2022, 7, 2),
    )

    # list of pydantic objects
    gsp_yields = [GSPYield.from_orm(gsp_yield) for gsp_yield in gsp_yields]


# get latest foreasts
with connection.get_session() as session:
    forecasts = get_latest_forecast_for_gsps(
        session=session,
        gsp_ids=range(0, 1),
        historic=True,
        start_target_time=datetime(2022, 7, 1),
        end_target_time=datetime(2022, 7, 2),
    )

    forecasts = [Forecast.from_orm_latest(forecast) for forecast in forecasts]


# plot
import plotly.graph_objects as go

x_pv_live = [gsp_yield.datetime_utc for gsp_yield in gsp_yields]
y_pv_live = [gsp_yield.solar_generation_kw / 1000 for gsp_yield in gsp_yields]

x_forecast = [forecast_value.target_time for forecast_value in forecasts[0].forecast_values]
y_forecast = [
    forecast_value.expected_power_generation_megawatts
    for forecast_value in forecasts[0].forecast_values
]

fig = go.Figure(
    data=[
        go.Scatter(x=x_pv_live, y=y_pv_live, name="pvlive"),
        go.Scatter(x=x_forecast, y=y_forecast, name="forecast"),
    ]
)
fig.show(renderer="browser")
