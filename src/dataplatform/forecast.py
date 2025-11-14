import streamlit as st
from datetime import datetime, timedelta, timezone
import os
import asyncio
from dp_sdk.ocf import dp
import pandas as pd
from grpclib.client import Channel
import plotly.graph_objects as go

data_platform_host = os.getenv("DATA_PLATFORM_HOST", "localhost")
data_platform_port = int(os.getenv("DATA_PLATFORM_PORT", "50051"))

# TODO make this dynamic
observer_names = ['pvlive_in_day','pvlive_day_after']


async def get_forecast_data(_client, location,start_date,end_date,selected_forecasters) -> pd.DataFrame:

    all_data_df = []

    # loop over 7 days of data
    temp_start_date = start_date
    while temp_start_date <= end_date:
        temp_end_date = temp_start_date + timedelta(days=7)
        if temp_end_date > end_date:
            temp_end_date = end_date

        # fetch data
        stream_forecast_data_request = dp.StreamForecastDataRequest(location_uuid=location.location_uuid,
                                    energy_source=dp.EnergySource.SOLAR,
                                    time_window=dp.TimeWindow(
                                        start_timestamp_utc=datetime.combine(temp_start_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                                        end_timestamp_utc=datetime.combine(temp_end_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                                    ),
                                    forecasters=selected_forecasters)
        stream_forecast_data_response = _client.stream_forecast_data(stream_forecast_data_request)


        i=0
        async for forecast_data in stream_forecast_data_response:

            forecast_data_dict = forecast_data.to_dict()
            forecast_data_dict.pop('otherStatisticsFractions')
            data_df = pd.DataFrame(forecast_data_dict, index=[i])
            all_data_df.append(data_df)

            i += 1

        temp_start_date = temp_start_date + timedelta(days=7)

    all_data_df = pd.concat(all_data_df, ignore_index=True)

    return all_data_df


async def get_all_observations(client, location, start_date, end_date) -> pd.DataFrame:

    all_observations_df = []

    for observer_name in observer_names:

        # loop over 7 days of data
        observation_one_df = []
        temp_start_date = start_date
        while temp_start_date <= end_date:
            temp_end_date = temp_start_date + timedelta(days=7)
            if temp_end_date > end_date:
                temp_end_date = end_date


            get_observations_request = dp.GetObservationsAsTimeseriesRequest(observer_name=observer_name,
                                                location_uuid=location.location_uuid,
                                                energy_source=dp.EnergySource.SOLAR,
                                                time_window=dp.TimeWindow(
                                                    start_timestamp_utc=datetime.combine(temp_start_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                                                    end_timestamp_utc=datetime.combine(temp_end_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                                                ),)
            get_observations_response = await client.get_observations_as_timeseries(get_observations_request)
            
            i=0
            for value in get_observations_response.values:
                observations_df = pd.DataFrame(value.to_dict(), index=[i])
                observation_one_df.append(observations_df)
                i += 1

            temp_start_date = temp_start_date + timedelta(days=7)
        
        observation_one_df = pd.concat(observation_one_df, ignore_index=True)
        observation_one_df = observation_one_df.sort_values(by='timestampUtc')
        observation_one_df['observer_name'] = observer_name

        all_observations_df.append(observation_one_df)
    
    all_observations_df = pd.concat(all_observations_df, ignore_index=True)

    return all_observations_df


def dp_forecast_page():
    asyncio.run(async_dp_forecast_page())


async def async_dp_forecast_page():    
    st.title("Data Platform Forecast Page")
    st.write("This is the forecast page from the Data Platform module. This is very much a WIP")

    async with Channel(host=data_platform_host, port=data_platform_port) as channel:
        client = dp.DataPlatformDataServiceStub(channel)

        # Select Country
        country = st.sidebar.selectbox("TODO Select a Country", ['UK', 'NL'], index=0)

        # Select Location Type
        location_types = [dp.LocationType.NATION, dp.LocationType.GSP, dp.LocationType.SITE]
        location_type = st.sidebar.selectbox("Select a Location Type", location_types, index=0)
        
        # List Location
        list_locations_request = dp.ListLocationsRequest(location_type_filter=location_type)
        list_locations_response = await client.list_locations(list_locations_request)
        locations = list_locations_response.locations
        location_names = [loc.location_name for loc in locations]
        
        # slect locations
        selected_location_name = st.sidebar.selectbox("Select a Location", location_names, index=0)
        selected_location = next(loc for loc in locations if loc.location_name == selected_location_name)

        # get models
        get_forecasters_request = dp.ListForecastersRequest(latest_versions_only=True)
        get_forecasters_response = await client.list_forecasters(get_forecasters_request)
        forecasters = get_forecasters_response.forecasters
        forecaster_names = [forecaster.forecaster_name for forecaster in forecasters]
        selected_forecaster_name = st.sidebar.multiselect("Select a Forecaster", forecaster_names, default=forecaster_names[0])
        selected_forecasters = [forecaster for forecaster in forecasters if forecaster.forecaster_name in selected_forecaster_name]

        # select start and end date
        start_date = st.sidebar.date_input("Start date:", datetime.now().date() - timedelta(days=30))
        end_date = st.sidebar.date_input("End date:", datetime.now().date() + timedelta(days=3))

        # select forecast type
        st.sidebar.write("TODO Select Forecast Type:")

        # setup page
        st.header("Time Series Plot")
        
        # get generation data
        all_observations_df = await get_all_observations(client, selected_location, start_date, end_date)

        # get forcast all data
        all_forecast_data_df = await get_forecast_data(client, selected_location, start_date, end_date, selected_forecasters)
        st.write(f"Selected Location uuid: {selected_location.location_uuid}. \
                 Fetched {len(all_forecast_data_df)} rows of forecast data")

        # add download button
        csv = all_forecast_data_df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️",
            data=csv,
            file_name=f"site_forecast_{selected_location.location_uuid}_{start_date}_{end_date}.csv",
            mime="text/csv",
        )


        all_forecast_data_df['target_timestamp_utc'] = pd.to_datetime(all_forecast_data_df['initTimestamp']) + pd.to_timedelta(all_forecast_data_df['horizonMins'], unit='m')
        
        # Choose current forecast
        # this is done by selecting the unique target_timestamp_utc with the the lowest horizonMins
        # it should also be unique for each forecasterFullName
        current_forecast_df = all_forecast_data_df.loc[all_forecast_data_df.groupby(['target_timestamp_utc', 'forecasterFullname'])['horizonMins'].idxmin()]

        # plot the results
        fig = go.Figure()
        for forecaster in selected_forecasters:
            name_and_version = f'{forecaster.forecaster_name}:{forecaster.forecaster_version}'
            forecaster_df = current_forecast_df[current_forecast_df['forecasterFullname'] == name_and_version]
            fig.add_trace(go.Scatter(
                x=forecaster_df['target_timestamp_utc'],
                y=forecaster_df['p50Fraction'],
                mode='lines',
                name=forecaster.forecaster_name
            ))

        for observer_name in observer_names:
            obs_df = all_observations_df[all_observations_df['observer_name'] == observer_name]
            fig.add_trace(go.Scatter(
                x=obs_df['timestampUtc'],
                y=obs_df['valueFraction'],
                mode='lines',
                name=observer_name
            ))

        fig.update_layout(
            title='Current Forecast',
            xaxis_title='Time',
            yaxis_title='Generation [%]',
            legend_title='Forecaster'
        )

        st.plotly_chart(fig)



        st.header("Summary Accuracy Graph")

        # take the foecast data, and group by horizonMins, forecasterFullName
        # calculate mean absolute error between p50Fraction and observations valueFraction
        all_observations_df['timestampUtc'] = pd.to_datetime(all_observations_df['timestampUtc'])
        merged_df = pd.merge(all_forecast_data_df, all_observations_df, left_on=['target_timestamp_utc'], right_on=['timestampUtc'], how='inner', suffixes=('_forecast', '_observation'))
        merged_df['absolute_error'] = (merged_df['p50Fraction'] - merged_df['valueFraction']).abs()

        summary_df = merged_df.groupby(['horizonMins', 'forecasterFullname']).agg({'absolute_error': 'mean'}).reset_index()
        summary_df['std'] = merged_df.groupby(['horizonMins', 'forecasterFullname']).agg({'absolute_error': 'std'}).reset_index()['absolute_error']
        summary_df['count'] = merged_df.groupby(['horizonMins', 'forecasterFullname']).agg({'absolute_error': 'count'}).reset_index()['absolute_error']
        summary_df['sem'] = summary_df['std'] / (summary_df['count']**0.5)

        fig2 = go.Figure()
        
        for forecaster in selected_forecasters:
            name_and_version = f'{forecaster.forecaster_name}:{forecaster.forecaster_version}'
            forecaster_df = summary_df[summary_df['forecasterFullname'] == name_and_version]
            fig2.add_trace(go.Scatter(
                x=forecaster_df['horizonMins'],
                y=forecaster_df['absolute_error'],
                mode='lines+markers',
                name=forecaster.forecaster_name
            ))  

            fig2.add_trace(
                go.Scatter(
                    x=forecaster_df['horizonMins'],
                    y=forecaster_df['absolute_error'] - 1.96 * forecaster_df['sem'],
                    mode="lines",
                    # name="p10: " + model,
                    # line=dict(color=get_colour_from_model_name(model), width=0),
                    legendgroup=forecaster.forecaster_name,
                    showlegend=False,
                )
            )

            fig2.add_trace(
                go.Scatter(
                    x=forecaster_df['horizonMins'],
                    y=forecaster_df['absolute_error'] + 1.96 * forecaster_df['sem'],
                    mode="lines",
                    # name="p10: " + model,
                    # line=dict(color=get_colour_from_model_name(model), width=0),
                    legendgroup=forecaster.forecaster_name,
                    showlegend=False,
                    fill="tonexty",
                )
            )


        fig2.update_layout(
            title='Mean Absolute Error by Horizon',
            xaxis_title='Horizon (Minutes)',
            yaxis_title='Mean Absolute Error [%]',
            legend_title='Forecaster'
        )

        st.plotly_chart(fig2)


        csv = summary_df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️",
            data=csv,
            file_name=f"summary_accuracy_{selected_location.location_uuid}_{start_date}_{end_date}.csv",
            mime="text/csv",
        )