from plots.users import make_api_requests_plot
import pandas as pd

def test_make_api_requests_plot():

    # create fake data
    api_requests = pd.DataFrame(
        {
            "created_utc": ["2021-01-01", "2021-01-02", "2021-01-03"],
            "url": ["https://api.solarforecastarbiter.org/", "https://api.solarforecastarbiter.org/", "https://api.solarforecastarbiter.org/"],
        }
    )
    _ = make_api_requests_plot(api_requests, "", "", "")