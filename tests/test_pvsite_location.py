from pvsite_forecast import calculate_penalty
import pandas as pd


def test_calculate_penalty():

    # set up dataframe
    df = pd.DataFrame(
        {
            "datetime": pd.date_range("2021-01-01", periods=5, freq="D"),
            "forecast": [0.1, 0.2, 0.3, 0.4, 0.5],
            "actual": [0.2, 0.3, 0.4, 0.5, 0.6],
        }
    )

    # calculate penalty
    penalty = calculate_penalty(df)

    # check results
    # TODO check result
    assert penalty == 0.05
