from plots.ramp_rate import make_ramp_rate_plot

from datetime import datetime


def test_make_pinball_plot(db_session, metrics_ramp_rate):
    _ = make_ramp_rate_plot(
        session=db_session,
        starttime=datetime(2023, 1, 1),
        endtime=datetime(2023, 1, 1),
        model_name="test_model",
    )
