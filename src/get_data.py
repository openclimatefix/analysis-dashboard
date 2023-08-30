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
from pvsite_datamodel.sqlmodels import UserSQL, SiteGroupSQL, SiteSQL

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


def get_all_users(session: Session) -> List[UserSQL]:

    """Get all users from the database.
     :param session: database session
    """
    query = session.query(UserSQL)
    
    query = query.order_by(UserSQL.email.asc())
    
    users = query.all()

    return users


def get_all_site_groups(session: Session) -> List[SiteGroupSQL]:

    """Get all users from the database.
     :param session: database session
    """
    query = session.query(SiteGroupSQL)
    
    query = query.order_by(SiteGroupSQL.site_group_name.asc())
    
    site_groups = query.all()

    return site_groups


def attach_site_group_to_user(session: Session, email: str, site_group_name: str) -> UserSQL:
    """Attach a site group to a user.
    :param session: database session
    :param email: email of user
    :param site_group_name: name of site group
    """
    site_group = session.query(SiteGroupSQL).filter(SiteGroupSQL.site_group_name == site_group_name).first()

    user = session.query(UserSQL).filter(UserSQL.email == email)

    user = user.update({"site_group_uuid": site_group.site_group_uuid})

    session.commit()


def attach_site_to_site_group(session: Session, site_uuid: str, site_group_name: str) -> SiteGroupSQL:
    """Attach a site to a site group.
    :param session: database session
    :param site_uuid: uuid of site
    :param site_group_name: name of site group
    """
  site_group = session.query(SiteGroupSQL).filter(SiteGroupSQL.site_group_name == site_group_name).first()

  site = session.query(SiteSQL).filter(SiteSQL.site_uuid == site_uuid)

  if site not in site_group:
    site_group.add(site)

  session.commit()
 




    

    
      

  

   