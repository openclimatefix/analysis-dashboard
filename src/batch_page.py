import streamlit as st
import torch
import matplotlib.pyplot as plt
import math
import pandas as pd
import fsspec


# Plot helper functions

def plot_image_grid(channels, labels, cols=4, cmap="viridis", size=3):
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
            channel_labels = [f"Channel {i+1}" for i in range(satellite_tensor.shape[1])]

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
