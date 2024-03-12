import plotly.graph_objects as go
import streamlit as st
import xarray as xr
import os, fsspec
from datetime import datetime, timedelta

# need this for some zarr files
import ocf_blosc2


def get_data(zarr_file):

    # hash filename
    hash_filename = f'./data/{zarr_file.replace("/","")}'

    # file exits open this
    download = True

    if os.path.exists(hash_filename):
        print("NWP file exists")

        downloaded_datetime = os.path.getmtime(hash_filename)
        downloaded_datetime = datetime.fromtimestamp(downloaded_datetime)
        print(downloaded_datetime)

        if downloaded_datetime < datetime.now() - timedelta(hours=1):
            print("NWP file is more than 1 hour old")
            download = True

            # remove file
            fs = fsspec.open(hash_filename).fs
            fs.rm(hash_filename, recursive=True)
        else:
            download = False
    else:
        print("NWP file does not exist")

    if download:

        # download file from zarr_file to hash_filename
        print(f"Downloading NWP file from {zarr_file} to {hash_filename}")
        fs = fsspec.open(zarr_file).fs
        fs.get(zarr_file, hash_filename, recursive=True)
        print("Downloaded")

    ds = xr.open_dataset(hash_filename)
    print("Loading")

    return ds


def nwp_page():
    """Main page for pvsite forecast"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"NWP"}</h1>',
        unsafe_allow_html=True,
    )

    # text input box
    st.write("Enter the zarr file you want to explore")
    zarr_file = st.text_input(
        "Zarr File", "s3://nowcasting-nwp-development/data-national/latest.zarr"
    )

    # open zarr file
    ds = get_data(zarr_file)
    st.write(f"Data variables are {list(ds.variables)}")

    # option if to image or time series plot
    st.sidebar.write("Select the type of plot you want to view")
    plot_type = st.sidebar.selectbox("Plot Type", ["Image", "Time Series"])

    # select the channel you want to view
    st.sidebar.write("Select the channel you want to view")
    if plot_type == "Image":

        # select one item from a list
        channels = st.sidebar.selectbox("Channels", list(ds.variable.values), 0)
    else:
        channels = st.sidebar.multiselect(
            "Channels", list(ds.variable.values), list(ds.variable.values)[0]
        )

    d_one_channel = ds.sel(variable=channels)

    variable_name = list(d_one_channel.variables)[0]

    if plot_type == "Image":

        # select which step you want
        init_time = d_one_channel.init_time.values
        st.sidebar.write(f"Select the step you want to view, the init time is {init_time}")
        steps = list(d_one_channel.step.values)
        step_idx = st.sidebar.selectbox("Step", range(0, len(steps)), 0)

        step = steps[step_idx]
        d_one_channel_one_step = d_one_channel.sel(step=step)

        # change nanoseconds to hours
        step = step.astype("timedelta64[h]").astype(int)

        # get values
        if "ECMWF_NW-INDIA" in d_one_channel_one_step.variables:
            values = d_one_channel_one_step["ECMWF_NW-INDIA"]
            x = d_one_channel_one_step.longitude.values
            y = d_one_channel_one_step.latitude.values
            xaxis_title = "Longitude"
            yaxis_title = "Latitude"
        elif "ECMWF_UK" in d_one_channel_one_step.variables:
            values = d_one_channel_one_step["ECMWF_UK"]
            x = d_one_channel_one_step.longitude.values
            y = d_one_channel_one_step.latitude.values
            xaxis_title = "Longitude"
            yaxis_title = "Latitude"
        elif "UKV" in d_one_channel_one_step.variables:
            values = d_one_channel_one_step["UKV"]
            x = d_one_channel_one_step.x.values
            y = d_one_channel_one_step.y.values
            xaxis_title = "x_osgb"
            yaxis_title = "y_osgb"

        else:
            values = d_one_channel_one_step
            x = d_one_channel_one_step.longitude.values
            y = d_one_channel_one_step.latitude.values
            xaxis_title = "Longitude"
            yaxis_title = "Latitude"

        # reduce dimensions
        if len(values.shape) == 3:
            values = values[0, :, :].values
        elif len(values.shape) == 4:
            values = values[0, 0, :, :].values

        # create heat map / image
        print("Making heat map")
        fig = go.Figure(
            data=go.Heatmap(
                z=values,
                x=x,
                y=y,
                colorscale="Viridis",
            )
        )

        # add title
        fig.update_layout(
            title=f"NWP {channels} at {init_time} + {step} hours",
            xaxis_title=xaxis_title,
            yaxis_title=yaxis_title,
        )
        # make figure bigger
        fig.update_layout(
            autosize=False,
            width=1000,
            height=1000,
        )
        st.plotly_chart(fig, theme="streamlit", height=2000)

    else:
        print("Average over latitude and longitude")

        # reduce by lat lon
        lon = st.text_input("Longitude Limits", "73,79")
        lat = st.text_input("Latitude Limits", "24,28")
        lon = lon.split(",")
        lat = lat.split(",")

        # swap lat limits round if wrong way
        if d_one_channel.latitude.values[0] > d_one_channel.latitude.values[-1]:
            lat = lat[::-1]
        d_one_channel = d_one_channel.sel({'latitude':slice(lat[0], lat[1]), 'longitude':slice(lon[0], lon[1])})

        if "latitude" in d_one_channel.dims and "longitude" in d_one_channel.dims:
            df = d_one_channel.mean(dim=["latitude", "longitude"])
        else:
            df = d_one_channel.mean(dim=["x", "y"])

        print("Convert to dataframe")
        df = df.to_dataframe()
        df.reset_index(inplace=True)

        print("Creat time index")
        df["time"] = df["init_time"] + df["step"]
        print(df)
        df = df[["time", "variable", variable_name]]

        print("pivot on time")
        df = df.pivot("time", columns="variable")
        df.columns = [c[1] for c in df.columns]

        print("Making plot")
        fig = go.Figure()
        for c in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[c], name=c))
        # add title
        fig.update_layout(
            title=f"NWP Time Series {channels}",
            xaxis_title="Time",
            yaxis_title="Value",
        )
        # make figure bigger
        fig.update_layout(
            autosize=False,
            width=1000,
            height=500,
        )
        st.plotly_chart(fig, theme="streamlit", height=800)
