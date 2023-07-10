# UK Analysis Dashboard

Internal dashboard for OCF to track forecast statistics for the UK. 

The analysis dashboard is a tool that has been developed over the last three months for OCF’s internal use and continues to evolve. 

Built with [Streamlit](https://streamlit.io/), a python-based framework made specifically for creating data apps, the dashboard tracks and displays Quartz Solar’s mean absolute error (MAE) on both the national and GSP level. 

The database generates this statistic using PVLive day-after updated values as the baseline for measuring error --the larger the error, the less accurate the forecast. Thanks to the analysis dashboard, OCF has a valuable feedback tool for understanding the accuracy of both the Quartz Solar forecast and other models in production.

``

## Installing and running the app 

First make sure you're in the main project folder: `internal_ui`

Install Streamlit: `pip install streamlit` or `pip3 install streamlit`

Check that Streamlit installed by running `streamlit hello`

Install all requirements with `pip install -r requirements.txt`

Check that Streamlit installed: `streamlit hello`

Create a login secret: `echo "password = example" > src/.streamlit/secrets.toml`

Run the app: `cd src && streamlit run main.py`




