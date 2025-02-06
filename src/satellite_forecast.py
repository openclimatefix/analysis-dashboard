import os
import fsspec

import numpy as np
import pandas as pd
import xarray as xr

import plotly.graph_objects as go
import streamlit as st

import ocf_blosc2

# Set the frame duration when playing the animation in ms
FRAME_DUR = 150

# Setting for the play button in the figure
PLAY_BUTTON_CONFIG = {
    "type": "buttons",
    "buttons": [
        {
            "args": [None, {"frame": {"duration": FRAME_DUR, "redraw": True}, "fromcurrent": True}],
            "label": "Play", 
            "method": "animate"
        },
        {
            "args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
            "label": "Pause", 
            "method": "animate"
        },
    ],
    "showactive": False,
    "direction": "left",
    "pad": {"r": 10, "t": 74},
    "x": 0.1,
    "xanchor": "right",
    "y": 0,
    "yanchor": "top",
}

SLIDER_CONFIG = {
    "active": 0, 
    "currentvalue": {
        "font": {"size": 20}, 
        "prefix": "Frame: ",
        "visible": True, 
        "xanchor": "right"
    },
    "transition": {"duration": 0, "easing": "linear"},
    "len": 0.9, 
    "pad": {"b": 10, "t": 50}, 
    "x": 0.1, 
    "xanchor": "left",
    "y": 0,  # Align horizontally with buttons
    "yanchor": "top", 
    "steps": None
}



def get_dataset(zarr_file: str) -> xr.Dataset:
    """Open and return a zarr dataset whilst also using a local cache for efficiency.
    
    A local cache is used if the dataset needs to be downloaded from s3
    
    Args:
        zarr_file: Path to the zarr dataset
        
    Returns:
        The opened xarray dataset
    """

    # hash filename
    hash_filename = "./data/" + zarr_file.removeprefix("s3://")

    # Check if the file exists and if its too old
    if os.path.exists(hash_filename):
        downloaded_datetime = pd.Timestamp.fromtimestamp(os.path.getmtime(hash_filename))
        
        # Delete the file if it is too old
        if downloaded_datetime < pd.Timestamp.now() - pd.Timedelta("5min"):
            fs = fsspec.open(hash_filename).fs
            fs.rm(hash_filename, recursive=True)

    # Download the file if needed
    if not os.path.exists(hash_filename):
        print(f"Downloading Satellite file from {zarr_file} to {hash_filename}")
        fs = fsspec.open(zarr_file).fs
        fs.get(zarr_file, hash_filename, recursive=True)

    ds = xr.open_dataset(hash_filename, engine="zarr")
    
    # Rename the variable dimension to channel
    ds = ds.rename({"variable": "channel"})

    return ds


def satellite_forecast_page():
    """Satellite page"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Satellite Forecast"}</h1>',
        unsafe_allow_html=True,
    )

    sat_zarr_path = "s3://nowcasting-sat-development/data/latest/latest_15.zarr.zip"
    sat_forecast_zarr_path = "s3://nowcasting-sat-development/cloudcasting_forecast/latest.zarr"

    # Open the sat and the sat forecast zarrs
    da_sat = get_dataset(sat_zarr_path).data
    da_sat_forecast = get_dataset(sat_forecast_zarr_path).sat_pred
    
    # Scale the satellite data
    da_sat = da_sat / 1023
    
    # Select the channel - defaults to the VIS008 channel
    channels = list(da_sat.channel.values)
    channel = st.sidebar.selectbox("Channel", channels, channels.index("VIS008"))
    
    # Slice the data to the selected channel
    da_sat = da_sat.sel(channel=channel)
    da_sat_forecast = da_sat_forecast.sel(channel=channel)
    
    # The init-time of the satellite forecast
    t0 = pd.Timestamp(da_sat_forecast.init_time.item())
    
    # Only use the true satellite data up to t0
    da_sat = da_sat.sel(time=slice(None, t0))
    
    # Match the spatial coords. We assume that the forecast will always have a smaller spatial
    # extent than the ground truths
    da_sat = da_sat.sel(
        y_geostationary=da_sat_forecast.y_geostationary, 
        x_geostationary=da_sat_forecast.x_geostationary, 
    )
    
    # Eagerly load the datasets
    da_sat = da_sat.compute()
    da_sat_forecast = da_sat_forecast.compute()
    
    print("sat nans: ", np.isnan(da_sat.values).mean())
    print("Sat", da_sat.values.min(), da_sat.values.max())
    print("For", da_sat_forecast.values.min(), da_sat_forecast.values.max())

    # Select the first init time of the forecast
    da_sat_forecast = da_sat_forecast.isel(init_time=0)

    # These are the valid times of the forecast steps
    forecast_valid_times = t0 + pd.to_timedelta(da_sat_forecast.step.values)
    
    # Compile all the satellite/forecast images and titles
    data = []
    titles = []
    for i, time in enumerate(pd.to_datetime(da_sat.time.values)):
        data.append(da_sat.sel(time=time).values)
        titles.append("Real: " + time.strftime("%Y-%m-%d %H:%M"))

    for i, time in enumerate(forecast_valid_times):
        data.append(da_sat_forecast.isel(step=i).values)
        titles.append("Forecast: " + time.strftime("%Y-%m-%d %H:%M"))
        
    # Make the plotly figure
    fig = make_figure(
        data=data, 
        titles=titles, 
        x=da_sat_forecast.x_geostationary, 
        y=da_sat_forecast.y_geostationary
    )
    
    st.plotly_chart(fig, theme="streamlit")



def make_figure(data: list[np.array], titles: list[str], x: np.array, y: np.array) -> go.Figure:
    """Make the satellite forecast animation
    
    Args:
        data: A list of arrays where each array is a satellite image or forecast
        titles: Strings describing each array
        x: The x coords of the images
        y: The y coords of the images
        
    Returns:
        A plotly figure
    """
    
    # Find min and max across all frames
    zmin = np.nanmin(data)
    zmax = np.nanmax(data)
    
    # Construct the frames up front so the slider works faster
    frames = [
        go.Frame(
            data=[go.Heatmap(z=frame, x=x, y=y, colorscale="Viridis", zmin=zmin, zmax=zmax)], 
            name=str(i), 
            layout=go.Layout(title_text=titles[i])
        ) for i, frame in enumerate(data)
    ]

    slider_steps = [
        {"args": [[str(i)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
         "label": str(i), "method": "animate"}
        for i in range(len(data))
    ]
    
    # Update the config with the slider steps
    SLIDER_CONFIG.update({"steps": slider_steps})

    fig = go.Figure(
        data=[frames[0].data[0]],  # Use only the first frame’s data
        layout=go.Layout(
            title_text=titles[0],
            # Add buttons to control the animation
            updatemenus=[PLAY_BUTTON_CONFIG],
            # Add slider so we can scroll through the truth and predictions
            sliders=[SLIDER_CONFIG],
            # Set the size of the figure
            autosize=False, width=700, height=700
        ),
        frames=frames,
    )

    
    return fig

    
