from pvsite_forecast import calculate_penalty
import pandas as pd
import numpy as np
import pytest


def test_calculate_penalty():
    """
    Test the calculate_penalty function with mock data, regions, asset types, and dynamic capacities.
    """

    # Mock input DataFrame
    df = pd.DataFrame(
        {
            "datetime": pd.date_range("2021-01-01", periods=5, freq="D"),
            "forecast_power_kw": [0.1, 0.2, 0.3, 0.4, 0.5],
            "generation_power_kw": [0.2, 0.3, 0.5, 0.5, 1],
        }
    )

    # Mock region, asset type, and capacity
    region = "Karnataka"
    asset_type = "solar"
    capacity_kw = 2  # Capacity specific to the mock site

    # Penalty bands configuration
    penalty_bands = {
        ("Karnataka", "solar"): [
            (10, 20, 0.1),  # Band 1
            (20, 30, 0.5),  # Band 2
            (30, None, 0.75),  # Open-ended Band
        ]
    }

    # Check if penalty bands exist for the provided region and asset type
    if (region, asset_type) not in penalty_bands:
        pytest.fail(f"No penalty bands found for region '{region}' and asset type '{asset_type}'")

    # Call the calculate_penalty function
    penalty_df, total_penalty = calculate_penalty(df, region, asset_type, capacity_kw)

    # Define expected results
    expected_total_penalty = 0.42  # Update based on correct manual calculations
    expected_penalty_df = pd.Series([0.01, 0.02, 0.05, 0.05, 0.29], index=df.index)

    # Assertions
    np.testing.assert_almost_equal(total_penalty, expected_total_penalty, decimal=2)
    pd.testing.assert_series_equal(
        penalty_df,
        expected_penalty_df,
        check_dtype=False,
        check_exact=False,
    )

    # Print outputs for debugging
    print("Penalty DataFrame:\n", penalty_df)
    print("Total Penalty:", total_penalty)


