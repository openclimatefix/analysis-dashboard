""" Read database functions
1. Get metric value
# TODO move to nowcasting_datamodel
"""
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import func

from nowcasting_datamodel.models.gsp import LocationSQL, GSPYieldSQL, GSPYield
from nowcasting_datamodel.models import MLModelSQL
from nowcasting_datamodel.models.metric import DatetimeIntervalSQL, MetricSQL, MetricValueSQL

logger = logging.getLogger(__name__)


def get_metric_value(
    session: Session,
    name: str,
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
    gsp_id: Optional[int] = None,
    forecast_horizon_minutes: Optional[int] = None,
    model_name: Optional[str] = None,
) -> List[MetricValueSQL]:
    """
    Get Metric values, for example MAE for gsp_id 5 on 2023-01-01
    :param session: database session
    :param name: name of metric e.g. Daily Latest MAE
    :param start_datetime_utc: the start datetime to filter on
    :param end_datetime_utc: the end datetime to filter on
    :param gsp_id: the gsp id to filter on
    :param forecast_horizon_minutes: filter on forecast_horizon_minutes.
        240 means the forecast main 4 horus before delivery.
    """

    # setup and join
    query = session.query(MetricValueSQL)
    query = query.join(MetricSQL)
    query = query.join(DatetimeIntervalSQL)

    # distinct on
    query = query.distinct(DatetimeIntervalSQL.start_datetime_utc)

    # metric name
    query = query.filter(MetricSQL.name == name)

    # filter on start time
    if start_datetime_utc is not None:
        query = query.filter(DatetimeIntervalSQL.start_datetime_utc >= start_datetime_utc)

    # filter on end time
    if end_datetime_utc is not None:
        query = query.filter(DatetimeIntervalSQL.end_datetime_utc <= end_datetime_utc)

    # filter on gsp_id
    if gsp_id is not None:
        query = query.join(LocationSQL)
        query = query.filter(LocationSQL.gsp_id == gsp_id)

    # filter forecast_horizon_minutes
    if forecast_horizon_minutes is not None:
        query = query.filter(MetricValueSQL.forecast_horizon_minutes == forecast_horizon_minutes)
    else:
        # select forecast_horizon_minutes is Null, which gets the last forecast.
        # !! This has to be a double equals or it won't work
        query = query.filter(MetricValueSQL.forecast_horizon_minutes == None)

    if model_name is not None:
        query = query.join(MLModelSQL)
        query = query.filter(MLModelSQL.name == model_name)

    # order by 'created_utc' desc, so we get the latest one
    query = query.order_by(
        DatetimeIntervalSQL.start_datetime_utc, MetricValueSQL.created_utc.desc()
    )

    # filter
    metric_values = query.all()

    return metric_values


def get_gsp_yield_sum(
    session: Session,
    gsp_ids: List[int],
    start_datetime_utc: datetime,
    regime: Optional[str] = None,
    end_datetime_utc: Optional[datetime] = None,
) -> List[GSPYield]:
    """
    Get the sum of gsp yield values.

    :param session: sqlalchemy sessions
    :param gsp_ids: list of gsp ids that we filter on
    :param start_datetime_utc: filter values on this start datetime
    :param regime: filter query on this regim. Can be "in-day" or "day-after"
    :param end_datetime_utc: optional end datetime filter

    :return: list of GSPYield objects
    """

    logger.info(f"Getting gsp yield sum for {len(gsp_ids)} gsp systems")

    if regime is None:
        logger.debug("No regime given, defaulting to 'in-day'")
        regime = "in-day"

    # start main query
    query = session.query(
        GSPYieldSQL.datetime_utc,
        func.sum(GSPYieldSQL.solar_generation_kw).label("solar_generation_kw"),
    )

    # join with location table
    query = query.join(LocationSQL)

    # select only the gsp systems we want
    query = query.where(LocationSQL.gsp_id.in_(gsp_ids))

    # filter on regime
    query = query.where(GSPYieldSQL.regime == regime)

    # filter on datetime
    query = query.where(GSPYieldSQL.datetime_utc >= start_datetime_utc)
    if end_datetime_utc is not None:
        query = query.where(GSPYieldSQL.datetime_utc <= end_datetime_utc)
    
    query = query.where(GSPYieldSQL.solar_generation_kw+1 > GSPYieldSQL.solar_generation_kw)
    
    # group and order by datetime
    query = query.group_by(GSPYieldSQL.datetime_utc)
    query = query.order_by(GSPYieldSQL.datetime_utc)

    results = query.all()

    # format results
    results = [
        GSPYield(
            datetime_utc=result.datetime_utc,
            solar_generation_kw=result.solar_generation_kw,
            regime=regime,
        )
        for result in results
    ]

    return results
