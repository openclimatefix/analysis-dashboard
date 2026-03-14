from datetime import UTC, datetime

import pandas as pd

from dataplatform.forecast.plot import plot_forecast_time_series


def _make_forecast_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["target_timestamp_utc"] = pd.to_datetime(df["target_timestamp_utc"])
    df["created_timestamp_utc"] = pd.to_datetime(df["created_timestamp_utc"])
    return df


def test_current_forecast_prefers_latest_created_when_horizon_ties():
    forecast_df = _make_forecast_df(
        [
            {
                "target_timestamp_utc": datetime(2026, 3, 11, 12, 30, tzinfo=UTC),
                "forecaster_name": "pvnet_v2",
                "horizon_mins": 0,
                "created_timestamp_utc": datetime(2026, 3, 11, 11, 0, tzinfo=UTC),
                "p50_watts": 9_800,
            },
            {
                "target_timestamp_utc": datetime(2026, 3, 11, 12, 30, tzinfo=UTC),
                "forecaster_name": "pvnet_v2",
                "horizon_mins": 0,
                "created_timestamp_utc": datetime(2026, 3, 11, 11, 30, tzinfo=UTC),
                "p50_watts": 10_300,
            },
            {
                "target_timestamp_utc": datetime(2026, 3, 11, 12, 30, tzinfo=UTC),
                "forecaster_name": "pvnet_v2",
                "horizon_mins": 30,
                "created_timestamp_utc": datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
                "p50_watts": 9_500,
            },
        ],
    )

    fig = plot_forecast_time_series(
        all_forecast_data_df=forecast_df,
        all_observations_df=pd.DataFrame(),
        forecaster_names=["pvnet_v2"],
        observer_names=[],
        scale_factor=1.0,
        units="W",
        selected_forecast_type="Current",
        selected_forecast_horizon=0,
        selected_t0s=None,
        show_probabilistic=False,
    )

    assert len(fig.data) == 1
    assert list(fig.data[0].y) == [10_300]


def test_horizon_forecast_prefers_latest_created_for_selected_horizon():
    forecast_df = _make_forecast_df(
        [
            {
                "target_timestamp_utc": datetime(2026, 3, 11, 12, 30, tzinfo=UTC),
                "forecaster_name": "pvnet_v2",
                "horizon_mins": 0,
                "created_timestamp_utc": datetime(2026, 3, 11, 11, 0, tzinfo=UTC),
                "p50_watts": 9_900,
            },
            {
                "target_timestamp_utc": datetime(2026, 3, 11, 12, 30, tzinfo=UTC),
                "forecaster_name": "pvnet_v2",
                "horizon_mins": 0,
                "created_timestamp_utc": datetime(2026, 3, 11, 11, 15, tzinfo=UTC),
                "p50_watts": 10_200,
            },
            {
                "target_timestamp_utc": datetime(2026, 3, 11, 12, 30, tzinfo=UTC),
                "forecaster_name": "pvnet_v2",
                "horizon_mins": 30,
                "created_timestamp_utc": datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
                "p50_watts": 9_600,
            },
        ],
    )

    fig = plot_forecast_time_series(
        all_forecast_data_df=forecast_df,
        all_observations_df=pd.DataFrame(),
        forecaster_names=["pvnet_v2"],
        observer_names=[],
        scale_factor=1.0,
        units="W",
        selected_forecast_type="Horizon",
        selected_forecast_horizon=0,
        selected_t0s=None,
        show_probabilistic=False,
        strict_horizon_filtering=True,
    )

    assert len(fig.data) == 1
    assert list(fig.data[0].y) == [10_200]
