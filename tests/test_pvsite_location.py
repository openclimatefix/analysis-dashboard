from pvsite_forecast import calculate_penalty
import pandas as pd
import numpy as np


def test_calculate_penalty():

    # set up dataframe
    df = pd.DataFrame(
        {
            "datetime": pd.date_range("2021-01-01", periods=5, freq="D"),
            "forecast_power_kw": [0.1, 0.2, 0.3, 0.4, 0.5],
            "generation_power_kw": [0.2, 0.3, 0.5, 0.5, 1],
        }
    )

    # calculate penalty
    penalty_df, total_penalty = calculate_penalty(df, capacity_kw=2)
    print(penalty_df)

    # check results
    # TODO check result
    assert np.round(total_penalty,2) == 0.42
