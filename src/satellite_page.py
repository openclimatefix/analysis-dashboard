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
    hash_filename_unzip = hash_filename.replace(".zip", "")

    # file exits open this
    download = True

    if os.path.exists(hash_filename):
        print("Satellite file exists")

        downloaded_datetime = os.path.getmtime(hash_filename)
        downloaded_datetime = datetime.fromtimestamp(downloaded_datetime)
        print(downloaded_datetime)

        if downloaded_datetime < datetime.now() - timedelta(hours=1):
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

    if not os.path.exists(hash_filename):
        print("Unzipping")
        os.system(f"unzip -qq {hash_filename} -d {hash_filename_unzip}")
    ds = xr.open_dataset(hash_filename_unzip)
    print("Loading")

    return ds


def satellite_page():
    """Satellite pge"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Satellite"}</h1>',
        unsafe_allow_html=True,
    )

    default = "s3://nowcasting-sat-development/data/latest/latest.zarr.zip"

    # text input box
    st.write("Enter the zarr file you want to explore")
    zarr_file = st.text_input(
        "Zarr File", default
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
        print(d_one_channel)
        times = d_one_channel.time.values
        times = [str(t) for t in times]
        st.sidebar.write(f"Select the time you want to view")
        time = st.sidebar.selectbox("Step", times, 0)

        d_one_channel_one_time = d_one_channel.sel(time=time)

        values = d_one_channel_one_time.data
        x = d_one_channel_one_time.x_geostationary.values
        y = d_one_channel_one_time.y_geostationary.values
        xaxis_title = "X Geo"
        yaxis_title = "Y Geo"

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
            title=f"Satellite {channels} at {time}",
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

        xaxis_title = "x_geostationary"
        yaxis_title = "y_geostationary"

        # reduce by lat lon
        x = f'{d_one_channel.__getitem__(xaxis_title).min().values},{d_one_channel.__getitem__(xaxis_title).max().values}'
        y = f'{d_one_channel.__getitem__(yaxis_title).min().values},{d_one_channel.__getitem__(yaxis_title).max().values}'
        x = st.text_input(f"{xaxis_title} Limits", x)
        y = st.text_input(f"{yaxis_title} Limits", y)
        x = x.split(",")
        y = y.split(",")

        # swap x limits round if wrong way
        if d_one_channel.__getitem__(xaxis_title).values[0] > d_one_channel.__getitem__(xaxis_title).values[-1]:
            x = x[::-1]
        d_one_channel = d_one_channel.sel({xaxis_title: slice(x[0], x[1]), yaxis_title:slice(y[0], y[1])})

        # mean over x and y
        df = d_one_channel.mean(dim=[xaxis_title, yaxis_title])

        print("Convert to dataframe")
        df = df.to_dataframe()
        df.reset_index(inplace=True)

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
            title=f"Satellite Time Series {channels}",
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
