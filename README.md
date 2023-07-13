# uk_analysis_dashboard

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

Internal dashboard for OCF to track UK forecast statistics. 

The analysis dashboard is a tool that was developed for OCF’s internal use and continues to evolve. 

Built with [Streamlit](https://streamlit.io/), a Python-based framework made specifically for creating data apps, the dashboard tracks and displays Quartz Solar and other data model statistics, such as mean absolute error (MAE) on both the national and GSP level. The database provides the error statistic using Sheffield Solar's PVLive day-after updated values as the baseline --the larger the error, the less accurate the forecast. 

Thanks to the analysis dashboard, OCF has a valuable feedback tool for understanding the accuracy of both the Quartz Solar forecast and other models in production.

## Installation 

Move into the main project folder: `cd internal_ui`.

Install all requirements: `pip install -r requirements.txt` or `pip3 install -r requirements.txt`.

Check that Streamlit installed: run `streamlit hello`. If all is working as it should, a "Welcome to Streamlit!" page opens in the browser.

Create a login secret: `echo "password = example" > src/.streamlit/secrets.toml`. 

## Database connection 

OCF team members can connect to the `forecast development database` using [these Notion instructions](https://www.notion.so/openclimatefix/Connecting-to-AWS-RDS-bf35b3fbd61f40df9c974c240e042354). Add `DB_URL= (db_url from notion documents)` to the `secrets.toml` file. Follow the instructions to connect to the SSH tunnel. 

Run app: `cd src && streamlit run main.py`.

## main.py

`main.py` contains functions for the `home page` of the app, which focuses on MAE for the OCF `Quartz Solar` forecast.

## forecast.py

`forecast.py` contains functions for the `forecast page`. The forecast page looks at how well each of OCF's forecast models is performing compared to `PVLive updated` truth values. 

## status.py

`status.py` contains functionality for the `status pagwe` and allows the OCF team to update the forecast status in the database. This is one of the advantages of using an interface like Streamlit, facilitating status updates in a database. 

## auth.py

`auth.py` contains code for the basic authenticaion that's been put in place. 

## 🛠️ infrastructure

`.github/workflows` contains a number of CI actions
1. linters.yaml: Runs linting checks on the code
2. release.yaml: Make and pushes docker files on a new code release
3. test-docker.yaml': Runs tests on every push

The docker file is in the folder `infrastructure/docker/`

The version is bumped automatically for any push to `main`.

## Environmental Variables

- DB_URL: The database url which the forecasts will be saved too

## Contributors 

The following folks have contributed to this repo. 








