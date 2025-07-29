import streamlit as st
import torch
import matplotlib.pyplot as plt
import math
import pandas as pd
import fsspec


# Plot helper functions

def plot_image_grid(channels, labels, cols=4, cmap="viridis", size=3):
    """
    Plots a grid of images with corresponding labels and colorbars.
    Args:
        channels (list or array-like): A list or array of image tensors or arrays to display. Each element should be a 2D array (single channel image).
        labels (list of str): List of labels for each image. Must be the same length as `channels`.
        cols (int, optional): Number of columns in the grid. Default is 4.
        cmap (str, optional): Colormap to use for displaying the images. Default is "viridis".
        size (int or float, optional): Size multiplier for each subplot (in inches). Default is 3.
    Returns:
        matplotlib.figure.Figure: The matplotlib Figure object containing the image grid.
    """
    num_channels = len(labels)
    rows = math.ceil(num_channels / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * size, rows * size))
    axes_list = axes.flatten()
    for i, label in enumerate(labels):
        image = channels[i].cpu().numpy()
        heatmap = axes_list[i].imshow(image, cmap=cmap)
        axes_list[i].set_title(label, fontsize=9)
        axes_list[i].axis('off')
        fig.colorbar(heatmap, ax=axes_list[i], fraction=0.046, pad=0.04)
    for extra_axis in axes_list[num_channels:]:
        extra_axis.axis('off')
    plt.tight_layout()
    return fig

def plot_line_chart(x_values, y_series, labels, x_label, y_label, size=(6, 3), legend_columns=1):
    """
    Plots a line chart for one or more series.
    Args:
        x_values (array-like): X-axis values.
        y_series (array-like): 2D array of shape (n_points, n_series) or 1D array.
        labels (list of str): Labels for each series.
        x_label (str): Label for x-axis.
        y_label (str): Label for y-axis.
        size (tuple, optional): Figure size in inches. Default is (6, 3).
        legend_columns (int, optional): Number of columns in legend. Default is 1.
    Returns:
        matplotlib.figure.Figure: The matplotlib Figure object.
    """
    fig, axis = plt.subplots(figsize=size)
    if y_series.ndim == 1:
        y_series = y_series.reshape(-1, 1)

    for series, label in zip(y_series.T, labels):
        axis.plot(x_values, series, marker='o', label=label)

    axis.set(xlabel=x_label, ylabel=y_label)
    axis.tick_params(labelsize=6)

    # Move legend to right of plot
    axis.legend(loc='center left', bbox_to_anchor=(1.01, 0.5), fontsize=6, ncol=legend_columns)
    plt.tight_layout()
    return fig


def batch_page():
    st.markdown(
        f'<h1 style="color:#63BCAF;font-size:48px;">{"Inference Batch Data Viewer"}</h1>',
        unsafe_allow_html=True,
    )

    # S3 path input, TODO dropdown box with filled in values for filepaths
    s3_path = st.text_input("Enter S3 path to .pt/.pth batch file (e.g., s3://example-bucket/example-path.pt)")
    if not s3_path:
        st.info("Please enter an S3 path to a `.pt` or `.pth` file.")
        st.stop()

    try:
        with fsspec.open(s3_path, mode='rb') as f:
            tensor_batch = torch.load(f, weights_only=False)

        # Satellite plots
        if all(key in tensor_batch for key in ("satellite_actual", "satellite_time_utc")):
            satellite_tensor = tensor_batch["satellite_actual"][0]  # [time, channels, H, W]
            satellite_times = [pd.to_datetime(ts) for ts in tensor_batch["satellite_time_utc"][0]]
            # This is the assumed order of channels as we normally list them
            channel_labels = [
                "IR_016", "IR_039", "IR_087", "IR_097", "IR_108", "IR_120", "IR_134", "VIS006",
                "VIS008", "WV_062", "WV_073"
            ]

            # Latest timestep image grid
            st.subheader(f"Satellite Channels at latest UTC time in batch {satellite_times[-1]}")
            latest_images = satellite_tensor[-1]
            st.pyplot(plot_image_grid(latest_images, channel_labels))

            # Mean over time image grid
            number_of_satellite_times = satellite_tensor.shape[0]
            st.subheader(f"Satellite Channels averaged over all timesteps ({number_of_satellite_times} timesteps)")
            mean_images = satellite_tensor.mean(dim=0)
            st.pyplot(plot_image_grid(mean_images, channel_labels))

            # Time series of mean values
            st.subheader("Satellite Mean Value per Channel Over Time")
            mean_time_series = satellite_tensor.mean(dim=(-2, -1)).cpu().numpy()  # [time, channels]
            st.pyplot(plot_line_chart(
                satellite_times,
                mean_time_series,
                channel_labels,
                x_label="Time (UTC)",
                y_label="Mean Pixel Value"
            ))
        else:
            missing = [k for k in ("satellite_actual", "satellite_time_utc") if k not in tensor_batch]
            st.info(f"Satellite data not present in batch. Missing keys: {missing}")

        # NWP plots
        if "nwp" in tensor_batch:
            for set_name, nwp_entry in tensor_batch["nwp"].items():
                st.subheader(f"NWP: {set_name} average values over forecast steps")
                nwp_steps = nwp_entry["nwp_step"].flatten()
                channel_names = nwp_entry["nwp_channel_names"]
                nwp_tensor = nwp_entry["nwp"][0]  # [time, channels, H, W]

                # Spatial-averaged time series
                mean_time_series = nwp_tensor.mean(dim=(-2, -1)).cpu().numpy()
                st.pyplot(plot_line_chart(
                    nwp_steps,
                    mean_time_series,
                    channel_names,
                    x_label="Step",
                    y_label="Value"
                ))

                # Spatial plot at first timestep
                st.subheader(f"NWP: {set_name} spatial slice, channel values at first step")
                first_step_images = nwp_tensor[0]
                st.pyplot(plot_image_grid(
                    first_step_images,
                    channel_names,
                ))
        else:
            st.info("Key 'nwp' not found in batch.")

        # Site time series
        if all(key in tensor_batch for key in ("site", "site_time_utc")):
            st.subheader("Site Time Series")
            site_times = [pd.to_datetime(ts) for ts in tensor_batch["site_time_utc"][0]]
            site_values = tensor_batch["site"].flatten()
            st.pyplot(plot_line_chart(
                site_times,
                site_values,
                ["Site"],
                x_label="Time (UTC)",
                y_label="Site Value",
                legend_columns=1
            ))
        else:
            missing = [k for k in ("site", "site_time_utc") if k not in tensor_batch]
            st.info(f"Missing keys for site plot: {missing}")

    except Exception as error:
        st.error(f"Error processing batch: {error}")
