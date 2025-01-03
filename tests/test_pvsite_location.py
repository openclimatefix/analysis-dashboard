from pvsite_forecast import calculate_penalty
import pandas as pd
import numpy as np
import pytest


def test_calculate_penalty():
    """
    Test the calculate_penalty function with mock data using the correct calculation approach.
    """
    df = pd.DataFrame({
        "datetime": pd.date_range("2021-01-01", periods=5, freq="D"),
        "forecast_power_kw": [0.1, 0.2, 0.3, 0.4, 0.5],  # forecast
        "generation_power_kw": [0.2, 0.3, 0.5, 0.5, 1.0],  # actual
        "capacity_kw": [2.0, 2.0, 2.0, 2.0, 2.0]  # AVC
    })

    region = "Karnataka"
    asset_type = "solar"
    capacity_kw = 2.0

    # Let's calculate expected results manually for one row to verify:
    # For first row:
    # deviation = 100 * (0.2 - 0.1) / 2 = 5% (below 15% threshold, no penalty)
    # For third row:
    # deviation = 100 * (0.5 - 0.3) / 2 = 10% (below 15% threshold, no penalty)
    # For fifth row:
    # deviation = 100 * (1.0 - 0.5) / 2 = 25% (in 25-35% band)

    penalty_bands = {
        ("Karnataka", "solar"): [
            (15, 25, 0.1),  # Band 1: 15-25%
            (25, 35, 0.2),  # Band 2: 25-35%
            (35, None, 0.3),  # Band 3: >35%
        ]
    }

    penalty_df, total_penalty = calculate_penalty(df, str(region), str(asset_type), capacity_kw)
    
    # With these deviations, most values fall below the 15% threshold except the last one
    expected_penalty_df = pd.Series([0.0, 0.0, 0.0, 0.0, 0.3], index=df.index)
    expected_total_penalty = 0.3

    # Assertions
    np.testing.assert_almost_equal(total_penalty, expected_total_penalty, decimal=2)
    pd.testing.assert_series_equal(
        penalty_df,
        expected_penalty_df,
        check_dtype=False,
        check_exact=False,
    )