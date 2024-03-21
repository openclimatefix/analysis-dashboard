from plots.users import make_api_requests_plot, make_api_frequency_requests_plot
import pandas as pd


def test_make_api_requests_plot():

    # create fake data
    api_requests = pd.DataFrame(
        {
            "created_utc": ["2021-01-01", "2021-01-02", "2021-01-03"],
            "url": [
                "https://api.solarforecastarbiter.org/",
                "https://api.solarforecastarbiter.org/",
                "https://api.solarforecastarbiter.org/",
            ],
        }
    )
    _ = make_api_requests_plot(api_requests, "", "", "")


def test_make_api_requests_freq_plot():

    # create fake data
    api_requests = pd.DataFrame(
        {
            "date": ["2021-01-01", "2021-01-02", "2021-01-03"],
            "url": [1, 2, 3],
        }
    )
    _ = make_api_frequency_requests_plot(api_requests, "", "", "")
