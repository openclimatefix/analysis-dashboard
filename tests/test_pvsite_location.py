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

    # Test inputs
    region = "Karnataka"
    asset_type = "solar"
    capacity_kw = 2  # Small capacity for testing

    # Expected results
    expected_total_penalty = 0.42  # Adjust based on manual calculation
    expected_penalty_df = pd.Series([0.01, 0.02, 0.05, 0.05, 0.29], index=df.index)

    # Run penalty calculation
    penalty_df, total_penalty = calculate_penalty(df, str(region), str(asset_type), capacity_kw)

    # Debugging outputs
    print("Calculated total penalty:", total_penalty)
    print("Calculated penalties by block:", penalty_df)

    # Assertions
    np.testing.assert_almost_equal(total_penalty, expected_total_penalty, decimal=2)
    pd.testing.assert_series_equal(penalty_df, expected_penalty_df, check_dtype=False)
