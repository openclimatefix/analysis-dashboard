import os
import fsspec

import numpy as np
import pandas as pd
import xarray as xr
import zarr

import plotly.graph_objects as go
import streamlit as st

from data_paths import all_satellite_paths, cloudcasting_path


sat_rss_path = all_satellite_paths["uk"]["rss"]
sat_0deg_path = all_satellite_paths["uk"]["0-deg"]

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

    # Download the file if needed and if available
    if not os.path.exists(hash_filename):
        fs = fsspec.open(zarr_file).fs
        if fs.exists(zarr_file):
            fs.get(zarr_file, hash_filename, recursive=True)

    if os.path.exists(hash_filename):
        if hash_filename.endswith(".zip"):
            with zarr.storage.ZipStore(hash_filename, mode='r') as store:
                ds = xr.open_zarr(store)
        else:
            ds = xr.open_zarr(hash_filename)

        for coord in ["x_geostationary", "y_geostationary"]:
            if ds[coord][0] > ds[coord][-1]:
                ds = ds.isel({coord: slice(None, None, -1)})

        return ds.rename({"variable": "channel"})
    else:
        return None


def cloudcasting_page():
    """Satellite forecast page"""

    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Satellite Forecast"}</h1>',
        unsafe_allow_html=True,
    )

    # Open the sat and the sat forecast zarrs
    da_sat_5 = get_dataset(sat_rss_path)
    da_sat_15 = get_dataset(sat_0deg_path)
    da_sat_forecast = get_dataset(cloudcasting_path)

    if da_sat_forecast is None:
        raise ValueError("Could not load the satellite forecast")
    
    if da_sat_5 is None and da_sat_15 is None:
        raise ValueError("Could not load either 5- or 15-minutely satellite data")
    
    # Select the most recent available satellite data

    if da_sat_5 is not None and da_sat_15 is not None:
        use_5_min_sat = (da_sat_5.time.max() > da_sat_15.time.max()) 
    elif da_sat_5 is not None:
        use_5_min_sat = True
    elif da_sat_15 is not None:
        use_5_min_sat = False
    else:
        raise Exception("Neither the 5 or 15-min sat is available")
    
    da_sat = da_sat_5 if use_5_min_sat else da_sat_15
    
    # Filter to 15 minutely timestamps regardless of the source
    da_sat = da_sat.sel(time=(da_sat.time.dt.minute%15 == 0))
    # Filter to last hour before the forecast
    t0 = pd.Timestamp(da_sat_forecast.init_time.item())
    da_sat = da_sat.sel(time=slice(t0 - pd.Timedelta("1h"), t0))
    
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
    
    # Match the spatial coords between the satellite and the satelite forecast. We assume 
    # that the forecast will always have a smaller spatial extent than the ground truths.

    # For 5-minutely data to match the coords explicitly
    if use_5_min_sat:
        da_sat = da_sat.sel(
            y_geostationary=da_sat_forecast.y_geostationary, 
            x_geostationary=da_sat_forecast.x_geostationary, 
        )
    
    # For 15-minutely data just match the bottom left hand corner(ish) and the shape
    else:
        da_sat = (
            da_sat.sel(
                y_geostationary=slice(da_sat_forecast.y_geostationary.min(), None),
                x_geostationary=slice(da_sat_forecast.x_geostationary.min(), None)
            )
            .isel(
                y_geostationary=slice(0, len(da_sat_forecast.y_geostationary)),
                x_geostationary=slice(0, len(da_sat_forecast.x_geostationary))
            )
        )
        
    # Eagerly load the datasets
    da_sat = da_sat.compute()
    da_sat_forecast = da_sat_forecast.compute()

    # Select the first init time of the forecast
    da_sat_forecast = da_sat_forecast.isel(init_time=0)

    # These are the valid times of the forecast steps
    forecast_valid_times = t0 + pd.to_timedelta(da_sat_forecast.step.values)
    
    # Compile all the satellite/forecast images and titles
    data = []
    titles = []
    for i, time in enumerate(pd.to_datetime(da_sat.time.values)):
        data.append(da_sat.data.sel(time=time).values)
        titles.append("Real: " + time.strftime("%Y-%m-%d %H:%M"))

    for i, time in enumerate(forecast_valid_times):
        data.append(da_sat_forecast.sat_pred.isel(step=i).values)
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

    
