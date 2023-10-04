from plots.pinball_and_exceedance_plots import make_pinball_or_exceedance_plot

from datetime import datetime


def test_make_pinball_plot(db_session, metrics_pinball):
    _ = make_pinball_or_exceedance_plot(
        session=db_session,
        starttime=datetime(2023, 1, 1),
        endtime=datetime(2023, 1, 1),
        metric_name="Pinball loss",
        model_name="test_model",
        forecast_horizon_selection=[60, 120, 180],
    )


def test_make_exceedance_plot(db_session, metrics_pinball):
    _ = make_pinball_or_exceedance_plot(
        session=db_session,
        starttime=datetime(2023, 1, 1),
        endtime=datetime(2023, 1, 1),
        metric_name="Exceedance",
        model_name="test_model",
        forecast_horizon_selection=[60, 120, 180],
    )
