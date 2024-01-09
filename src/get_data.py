""" Read database functions
1. Get metric value
2. Get all users
3. Get all site groups
4. Update user site group
# TODO move to nowcasting_datamodel
"""
import logging
import json
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional
import sqlalchemy as sa
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.functions import func
from sqlalchemy.orm import joinedload

from nowcasting_datamodel.models.gsp import LocationSQL
from nowcasting_datamodel.models import MLModelSQL
from nowcasting_datamodel.models.metric import (
    DatetimeIntervalSQL,
    MetricSQL,
    MetricValueSQL,
)
from pvsite_datamodel.sqlmodels import UserSQL, SiteGroupSQL, SiteSQL, ForecastValueSQL, ForecastSQL

from data.gsp import get_gsp
from data.dno import get_dno

logger = logging.getLogger(__name__)


def get_metric_value(
    session: Session,
    name: str,
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
    gsp_id: Optional[int] = None,
    forecast_horizon_minutes: Optional[int] = None,
    model_name: Optional[str] = None,
    plevel: Optional[int] = None,
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
        query = query.filter(
            DatetimeIntervalSQL.start_datetime_utc >= start_datetime_utc
        )
        # this pre loads the datetimes internals, so they don't have be loaded each time later
        query = query.options(joinedload(MetricValueSQL.datetime_interval))

    # filter on end time
    if end_datetime_utc is not None:
        query = query.filter(DatetimeIntervalSQL.end_datetime_utc <= end_datetime_utc)

    # filter on gsp_id
    if gsp_id is not None:
        query = query.join(LocationSQL)
        query = query.filter(LocationSQL.gsp_id == gsp_id)

    # filter forecast_horizon_minutes
    if forecast_horizon_minutes is not None:
        query = query.filter(
            MetricValueSQL.forecast_horizon_minutes == forecast_horizon_minutes
        )
    else:
        # select forecast_horizon_minutes is Null, which gets the last forecast.
        # !! This has to be a double equals or it won't work
        query = query.filter(MetricValueSQL.forecast_horizon_minutes == None)

    if model_name is not None:
        query = query.join(MLModelSQL)
        query = query.filter(MLModelSQL.name == model_name)

    if plevel is not None:
        query = query.filter(MetricValueSQL.p_level == plevel)

    # order by 'created_utc' desc, so we get the latest one
    query = query.order_by(
        DatetimeIntervalSQL.start_datetime_utc, MetricValueSQL.created_utc.desc()
    )

    # filter
    metric_values = query.all()

    return metric_values


# get all users
def get_all_users(session: Session) -> List[UserSQL]:
    """Get all users from the database.
    :param session: database session
    """
    query = session.query(UserSQL)

    query = query.order_by(UserSQL.email.asc())

    users = query.all()

    return users


# get all site groups
def get_all_site_groups(session: Session) -> List[SiteGroupSQL]:
    """Get all users from the database.
    :param session: database session
    """
    query = session.query(SiteGroupSQL)

    query = query.order_by(SiteGroupSQL.site_group_name.asc())

    site_groups = query.all()

    return site_groups


# update user site group; users only belong to one site group
def update_user_site_group(
    session: Session, email: str, site_group_name: str
) -> UserSQL:
    """Change site group for user.
    :param session: database session
    :param email: email of user
    :param site_group_name: name of site group
    """
    site_group = (
        session.query(SiteGroupSQL)
        .filter(SiteGroupSQL.site_group_name == site_group_name)
        .first()
    )

    user = session.query(UserSQL).filter(UserSQL.email == email)

    user = user.update({"site_group_uuid": site_group.site_group_uuid})

    session.commit()

    return user


# get site group by name
def get_site_by_client_site_id(session: Session, client_site_id: str) -> List[SiteSQL]:
    """Get site by client site id.
    :param session: database session
    :param client_site_id: client site id
    """
    query = session.query(SiteSQL)

    query = query.filter(SiteSQL.client_site_id == client_site_id)

    site = query.first()

    return site
