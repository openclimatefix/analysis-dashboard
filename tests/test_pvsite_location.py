from pvsite_forecast import calculate_penalty
import pandas as pd
import numpy as np
import pytest


def test_calculate_penalty():
    """
    Test the calculate_penalty function with mock data and fixed capacity.
    """

    # Create a mock DataFrame
    df = pd.DataFrame(
        {
            "datetime": pd.date_range("2021-01-01", periods=5, freq="D"),
            "forecast_power_kw": [0.1, 0.2, 0.3, 0.4, 0.5],
            "generation_power_kw": [0.2, 0.3, 0.5, 0.5, 1],
        }
    )

    # Assume capacity and mock region + asset type mapping
    capacity_kw = 2
    region = "Karnataka"
    asset_type = "solar"

    # Set penalty bands for the region and asset type
    penalty_bands = {
        ("Karnataka", "solar"): [
            (10, 20, 0.1),  # Band 1
            (20, 30, 0.5),  # Band 2
            (30, None, 0.75),  # Open-ended Band
        ]
    }

    # Calculate penalty
    penalty_df, total_penalty = calculate_penalty(df, region, asset_type, capacity_kw, penalty_bands)

    # Expected results for validation
    expected_total_penalty = 0.42  # Adjust based on correct calculations
    expected_penalty_df = pd.Series([0.01, 0.02, 0.05, 0.05, 0.29], index=df.index)

    # Assertions
    np.testing.assert_almost_equal(total_penalty, expected_total_penalty, decimal=2)
    pd.testing.assert_series_equal(penalty_df, expected_penalty_df, check_dtype=False)

