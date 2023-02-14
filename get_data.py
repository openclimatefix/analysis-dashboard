""" Read database functions
1. Get the one metric
2. Get metric value
3. get datetime interval
"""
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm.session import Session

from nowcasting_datamodel.models.gsp import LocationSQL
from nowcasting_datamodel.models.metric import DatetimeIntervalSQL, MetricSQL, MetricValueSQL, MetricValue

logger = logging.getLogger(__name__)


def get_metric(session: Session, name: str) -> MetricSQL:
    """
    Get metric object from database
    :param session: database session
    :param name: name of the metric
    return: One Metric SQl object
    """

    # start main query
    query = session.query(MetricSQL)

    # filter on name
    query = query.filter(MetricSQL.name == name)

    # get all results
    metrics = query.all()

    if len(metrics) == 0:
        logger.debug(f"Metric for name {name} does not exist so going to add it")

        metric = MetricSQL(name=name, description="TODO need to update")

        session.add(metric)
        session.commit()

    else:
        metric = metrics[0]

    return metric

# this is the newer function to get metric value from the database
def get_metric_value(
    session: Session,
    name: str,
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
    gsp_id: Optional[int] = None,
    forecast_horizon_minutes: Optional[int] = None,
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
        # select forecast_horizon_minutes is Null, which gets the last forecast
        query = query.filter(MetricValueSQL.forecast_horizon_minutes is None)

    # order by 'created_utc' desc, so we get the latest one
    query = query.order_by(
        DatetimeIntervalSQL.start_datetime_utc, MetricValueSQL.created_utc.desc()
    )

    # filter
    metric_values = query.all()

    return metric_values


def get_datetime_interval(
    session: Session, start_datetime_utc: datetime, end_datetime_utc: datetime
) -> DatetimeIntervalSQL:
    """
    Get datetime interval object from database
    :param session: database session
    :param start_datetime_utc: start datetime of the interval
    :param end_datetime_utc: end datetime of the interval
    return: One Datetime interval SQl object
    """

    # start main query
    query = session.query(DatetimeIntervalSQL)

    # filter on start_datetime_utc
    query = query.filter(DatetimeIntervalSQL.start_datetime_utc == start_datetime_utc)

    # filter on end_datetime_utc
    query = query.filter(DatetimeIntervalSQL.end_datetime_utc == end_datetime_utc)

    # get all results
    datetime_intervals = query.all()

    if len(datetime_intervals) == 0:
        logger.debug(
            f"Datetime interbal for {start_datetime_utc=} "
            f"and {end_datetime_utc=} does not exist so going to add it"
        )

        datetime_interval = DatetimeIntervalSQL(
            start_datetime_utc=start_datetime_utc, end_datetime_utc=end_datetime_utc
        )

        session.add(datetime_interval)
        session.commit()

    else:
        datetime_interval = datetime_intervals[0]

    return datetime_interval