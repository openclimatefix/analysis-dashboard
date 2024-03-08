import plotly.graph_objects as go
import streamlit as st
import xarray as xr

# need this for some zarr files
import ocf_blosc2

@st.cache_data(ttl=3600)
def get_data(zarr_file):
    ds = xr.open_dataset(zarr_file)
    print("Loading")
    ds = ds.load()
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

        # get values
        if "ECMWF_NW-INDIA" in d_one_channel_one_step.variables:
            values = d_one_channel_one_step["ECMWF_NW-INDIA"]
        elif "ECMWF_UK" in d_one_channel_one_step.variables:
            values = d_one_channel_one_step["ECMWF_UK"]
        elif "UKV" in d_one_channel_one_step.variables:
            values = d_one_channel_one_step["UKV"]

        else:
            values = d_one_channel_one_step

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
                x=d_one_channel_one_step.longitude.values,
                y=d_one_channel_one_step.latitude.values,
                colorscale="Viridis",
            )
        )

        # add title
        fig.update_layout(
            title=f"NWP {channels} at {init_time} + {step}",
            xaxis_title="Longitude",
            yaxis_title="Latitude",
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
