from pvsite_forecast import calculate_penalty
import pandas as pd
import numpy as np
import pytest


def test_calculate_penalty():
    df = pd.DataFrame(
        {
            "datetime": pd.date_range("2021-01-01", periods=5, freq="D"),
            "forecast_power_kw": [0.1, 0.2, 0.3, 0.4, 0.5],
            "generation_power_kw": [0.2, 0.3, 0.5, 0.5, 1],
        }
    )

    region = "Karnataka"
    asset_type = "solar"
    capacity_kw = 2

    penalty_bands = {
        ("Karnataka", "solar"): [
            (10, 20, 0.25),
            (20, 30, 0.5),
            (30, None, 0.75),
        ]
    }

    penalty_df, total_penalty = calculate_penalty(df, str(region), str(asset_type), capacity_kw)
    
    expected_penalty_df = pd.Series([0.0, 0.0, 0.0, 0.0, 0.3], index=df.index)
    expected_total_penalty = 0.3

    np.testing.assert_almost_equal(total_penalty, expected_total_penalty, decimal=2)
    pd.testing.assert_series_equal(
        penalty_df,
        expected_penalty_df,
        check_dtype=False,
        check_exact=False,
    )