import datetime as dt

import pytest
from nowcasting_datamodel.models.base import Base_Forecast
from nowcasting_datamodel.models.metric import MetricSQL, MetricValueSQL, DatetimeIntervalSQL
from nowcasting_datamodel.read.read import get_location
from nowcasting_datamodel.read.read_models import get_model
from pvsite_datamodel.sqlmodels import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def engine():
    """Database engine fixture."""
    with PostgresContainer("postgres:14.5") as postgres:
        # TODO need to setup postgres database with docker
        url = postgres.get_connection_url()
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        Base_Forecast.metadata.create_all(engine)

        yield engine


@pytest.fixture()
def db_session(engine):
    """Return a sqlalchemy session, which tears down everything properly post-test."""
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction

    with Session(bind=connection) as session:
        yield session

        session.close()
        # roll back the broader transaction
        transaction.rollback()
        # put back the connection to the connection pool
        connection.close()
        session.flush()

    engine.dispose()


@pytest.fixture()
def metrics_pinball(db_session):

    metric = MetricSQL(name="pinball_loss", description="Pinball loss")
    db_session.add(metric)

    d = DatetimeIntervalSQL(
        start_datetime_utc=dt.datetime(2021, 1, 1, 0, 0, 0),
        end_datetime_utc=dt.datetime(2021, 1, 1, 0, 0, 0),
    )
    db_session.add(d)
    db_session.commit()

    for forecast_horizon_minutes in [60, 120, 180]:
        for plevel in [10, 90]:
            m = MetricValueSQL(
                forecast_horizon_minutes=forecast_horizon_minutes,
                p_level=plevel,
                value=1.0,
                number_of_data_points=7,
            )
            m.metric = metric
            m.datetime_interval = d
            m.location = get_location(db_session, gsp_id=0)
            m.model = get_model(db_session, name="test_model")
            db_session.add(m)


@pytest.fixture()
def metrics_ramp_rate(db_session):

    metric = MetricSQL(name="Ramp rate MAE", description="Ramp Rate")
    db_session.add(metric)

    d = DatetimeIntervalSQL(
        start_datetime_utc=dt.datetime(2021, 1, 1, 0, 0, 0),
        end_datetime_utc=dt.datetime(2021, 1, 1, 0, 0, 0),
    )
    db_session.add(d)
    db_session.commit()

    for forecast_horizon_minutes in [60, 120, 180]:
        m = MetricValueSQL(
            forecast_horizon_minutes=forecast_horizon_minutes,
            value=1.0,
            number_of_data_points=7,
        )
        m.metric = metric
        m.datetime_interval = d
        m.location = get_location(db_session, gsp_id=0)
        m.model = get_model(db_session, name="test_model")
        db_session.add(m)
