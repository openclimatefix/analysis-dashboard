# uk_analysis_dashboard

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-3-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

Internal dashboard for OCF to track UK forecast statistics. 

The analysis dashboard is a tool that was developed in Spring 2023 for OCF’s internal use and continues to evolve. 

Built with [Streamlit](https://streamlit.io/), a Python-based framework made specifically for creating data apps, the dashboard tracks and displays Quartz Solar’s mean absolute error (MAE) on both the national and GSP level. 
The database provides this statistic using PVLive day-after updated values as the baseline for measuring error --the larger the error, the less accurate the forecast. Thanks to the analysis dashboard, OCF has a valuable feedback tool for understanding the accuracy of both the Quartz Solar forecast and other models in production.

## Installation 

First make sure you're in, `internal_ui`, the main project folder.

Install Streamlit with `pip install streamlit` or `pip3 install streamlit`

Check that Streamlit installed by running `streamlit hello`

Install all requirements with `pip install -r requirements.txt`

Check that Streamlit installed with `streamlit hello`

Create a login secret: `echo "password = example" > src/.streamlit/secrets.toml`

Run the app with `cd src && streamlit run main.py`

## main.py

## forecast.py

## status.py

## auth.py

## 🛠️ infrastructure

## Environmental Variables

- DB_URL: The database url which the forecasts will be saved too

## Contributors 

The following folks have contributed to this repo. 








