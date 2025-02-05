import plotly.graph_objects as go
import streamlit as st
import xarray as xr
import os, fsspec
from datetime import datetime, timedelta

# need this for some zarr files
import ocf_blosc2


def get_data(zarr_file, unzip=True):

    # hash filename
    hash_filename = f'./data/{zarr_file.replace("/","")}'
    hash_filename_unzip = hash_filename.replace(".zip", "")

    # file exits open this
    download = True

    if os.path.exists(hash_filename):
        print("Satellite file exists")

        downloaded_datetime = os.path.getmtime(hash_filename)
        downloaded_datetime = datetime.fromtimestamp(downloaded_datetime)
        print(downloaded_datetime)

        if downloaded_datetime < datetime.now() - timedelta(minutes=5):
            print("Satellite file is more than 1 hour old")
            download = True

            # remove file
            fs = fsspec.open(hash_filename).fs
            fs.rm(hash_filename, recursive=True)
            fs.rm(hash_filename_unzip, recursive=True)
        else:
            download = False
    else:
        print("Satellite file does not exist")

    if download:

        # download file from zarr_file to hash_filename
        print(f"Downloading Satellite file from {zarr_file} to {hash_filename}")
        fs = fsspec.open(zarr_file).fs
        fs.get(zarr_file, hash_filename, recursive=True)
        print("Downloaded")

    if unzip:

        if not os.path.exists(hash_filename_unzip):
            print("Unzipping")
            os.system(f"unzip -qq {hash_filename} -d {hash_filename_unzip}")
        ds = xr.open_dataset(hash_filename_unzip)
    else:
        ds = xr.open_dataset(hash_filename)
    print("Loading")

    return ds


def satellite_forecast_page():
    """Satellite pge"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Satellite Forecast"}</h1>',
        unsafe_allow_html=True,
    )

    zarr_file = "s3://nowcasting-sat-development/data/latest/latest_15.zarr.zip"
    zarr_forecast_file = "s3://nowcasting-sat-development/cloudcasting_forecast/latest.zarr"

    # open zarr file
    ds = get_data(zarr_file)
    ds_forecast = get_data(zarr_forecast_file, unzip=False)

    # choose channel 'WV_073'
    channel = st.sidebar.selectbox(
        "Channels", list(ds.variable.values), len(list(ds.variable.values)) - 1
    )
    ds_one_channel = ds.sel(variable=channel).data
    ds_forecast_one_channel = ds_forecast.sel(variable=channel).sat_pred

    # for the forecast, select the first init time
    ds_forecast_one_channel = ds_forecast_one_channel.sel(
        init_time=ds_forecast_one_channel.init_time[0]
    )

    # create "time", init_time + step
    time = ds_forecast_one_channel.init_time + ds_forecast_one_channel.step

    # reassign "step" coordiante to time values and rename
    ds_forecast_one_channel = ds_forecast_one_channel.assign_coords(step=time)
    ds_forecast_one_channel = ds_forecast_one_channel.rename({"step": "time"})

    # select smaller region
    ds_one_channel = ds_one_channel.isel(
        y_geostationary=slice(14, 386), x_geostationary=slice(44, 658)
    )

    # format data
    data = []
    titles = []
    for time in ds_one_channel.time.values:
        data.append(
            {
                "z": ds_one_channel.sel(time=time).values / 1023,
                "x": ds_one_channel.x_geostationary.values,
                "y": ds_one_channel.y_geostationary.values,
            }
        )
        titles.append(f"Real: {time}")

    # format data
    for time in ds_forecast_one_channel.time.values:
        data.append(
            {
                "z": ds_forecast_one_channel.sel(time=time).values,
                "x": ds_forecast_one_channel.x_geostationary.values,
                "y": ds_forecast_one_channel.y_geostationary.values,
            }
        )
        titles.append(f"Forecast: {time}")

    st.write("Making video")
    fig = go.Figure(
        data=[
            go.Heatmap(
                z=data[0]["z"], x=data[0]["x"], y=data[0]["y"], colorscale="Viridis", zmax=1, zmin=0
            )
        ],
        layout=go.Layout(
            updatemenus=[
                dict(type="buttons", buttons=[dict(label="Play", method="animate", args=[None])])
            ]
        ),
        frames=[
            go.Frame(
                data=[go.Heatmap(z=k["z"], colorscale="Viridis")],
                layout=go.Layout(title_text=f"{titles[i]}"),
                name=str(i),
            )
            for i, k in enumerate(data)
        ],
    )

    fig.update_layout(autosize=False, width=1000, height=1000)

    st.plotly_chart(fig, theme="streamlit")
