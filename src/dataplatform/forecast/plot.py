import plotly.graph_objects as go

from dataplatform.forecast.constanst import colours


def plot_forecast_time_series(
    all_forecast_data_df,
    all_observations_df,
    forecaster_names,
    observer_names,
    scale_factor,
    units,
    selected_forecast_type,
    selected_forecast_horizon,
):
    if selected_forecast_type == "Current":
        # Choose current forecast
        # this is done by selecting the unique target_timestamp_utc with the the lowest horizonMins
        # it should also be unique for each forecasterFullName
        current_forecast_df = all_forecast_data_df.loc[
            all_forecast_data_df.groupby(["target_timestamp_utc", "forecaster_name"])[
                "horizon_mins"
            ].idxmin()
        ]
    elif selected_forecast_type == "Horizon":
        # Choose horizon forecast
        current_forecast_df = all_forecast_data_df[
            all_forecast_data_df["horizon_mins"] >= selected_forecast_horizon
        ]
        current_forecast_df = current_forecast_df.loc[
            current_forecast_df.groupby(["target_timestamp_utc", "forecaster_name"])[
                "horizon_mins"
            ].idxmin()
        ]
    else:
        pass

    # plot the results
    fig = go.Figure()
    for observer_name in observer_names:
        obs_df = all_observations_df[all_observations_df["observer_name"] == observer_name]

        if observer_name == "pvlive_in_day":
            # dashed white line
            line = dict(color="white", dash="dash")
        elif observer_name == "pvlive_day_after":
            line = dict(color="white")
        else:
            line = dict()

        fig.add_trace(
            go.Scatter(
                x=obs_df["timestamp_utc"],
                y=obs_df["value_watts"] / scale_factor,
                mode="lines",
                name=observer_name,
                line=line,
            ),
        )

    for i, forecaster_name in enumerate(forecaster_names):
        forecaster_df = current_forecast_df[
            current_forecast_df["forecaster_name"] == forecaster_name
        ]
        fig.add_trace(
            go.Scatter(
                x=forecaster_df["target_timestamp_utc"],
                y=forecaster_df["p50_watts"] / scale_factor,
                mode="lines",
                name=forecaster_name,
                line=dict(color=colours[i % len(colours)]),
                legendgroup=forecaster_name,
            ),
        )
        if "p10_watts" in forecaster_df.columns and "p90_watts" in forecaster_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=forecaster_df["target_timestamp_utc"],
                    y=forecaster_df["p10_watts"] / scale_factor,
                    mode="lines",
                    line=dict(color=colours[i % len(colours)], width=0),
                    legendgroup=forecaster_name,
                    showlegend=False,
                ),
            )

            fig.add_trace(
                go.Scatter(
                    x=forecaster_df["target_timestamp_utc"],
                    y=forecaster_df["p90_watts"] / scale_factor,
                    mode="lines",
                    line=dict(color=colours[i % len(colours)], width=0),
                    legendgroup=forecaster_name,
                    showlegend=False,
                    fill="tonexty",
                ),
            )

    fig.update_layout(
        title="Current Forecast",
        xaxis_title="Time",
        yaxis_title=f"Generation [{units}]",
        legend_title="Forecaster",
    )

    return fig


def plot_forecast_metric_vs_horizon_minutes(
    merged_df, forecaster_names, selected_metric, scale_factor, units
):
    # Get the mean observed generation
    mean_observed_generation = merged_df["value_watts"].mean()

    # mean absolute error by horizonMins and forecasterFullName
    summary_df = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg({"absolute_error": "mean"})
        .reset_index()
    )
    summary_df["std"] = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg({"absolute_error": "std"})
        .reset_index()["absolute_error"]
    )
    summary_df["count"] = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg({"absolute_error": "count"})
        .reset_index()["absolute_error"]
    )
    summary_df["sem"] = summary_df["std"] / (summary_df["count"] ** 0.5)

    # ME
    summary_df["ME"] = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg({"error": "mean"})
        .reset_index()["error"]
    )

    # TODO more metrics

    summary_df["effective_capacity_watts_observation"] = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg({"effective_capacity_watts_observation": "mean"})
        .reset_index()["effective_capacity_watts_observation"]
    )

    # rename absolute_error to MAE
    summary_df = summary_df.rename(columns={"absolute_error": "MAE"})
    summary_df["NMAE (by capacity)"] = (
        summary_df["MAE"] / summary_df["effective_capacity_watts_observation"]
    )
    summary_df["NMAE (by mean observed generation)"] = summary_df["MAE"] / mean_observed_generation
    # summary_df["NMAE (by observed generation)"] = summary_df["absolute_error_divided_by_observed"]

    fig2 = go.Figure()

    for i, forecaster_name in enumerate(forecaster_names):
        forecaster_df = summary_df[summary_df["forecaster_name"] == forecaster_name]
        fig2.add_trace(
            go.Scatter(
                x=forecaster_df["horizon_mins"],
                y=forecaster_df[selected_metric] / scale_factor,
                mode="lines+markers",
                name=forecaster_name,
                line=dict(color=colours[i % len(colours)]),
                legendgroup=forecaster_name,
            ),
        )

        fig2.add_trace(
            go.Scatter(
                x=forecaster_df["horizon_mins"],
                y=(forecaster_df[selected_metric] - 1.96 * forecaster_df["sem"]) / scale_factor,
                mode="lines",
                line=dict(color=colours[i % len(colours)], width=0),
                legendgroup=forecaster_name,
                showlegend=False,
            ),
        )

        fig2.add_trace(
            go.Scatter(
                x=forecaster_df["horizon_mins"],
                y=(forecaster_df[selected_metric] + 1.96 * forecaster_df["sem"]) / scale_factor,
                mode="lines",
                line=dict(color=colours[i % len(colours)], width=0),
                legendgroup=forecaster_name,
                showlegend=False,
                fill="tonexty",
            ),
        )

    fig2.update_layout(
        title=f"{selected_metric} by Horizon",
        xaxis_title="Horizon (Minutes)",
        yaxis_title=f"{selected_metric} [{units}]",
        legend_title="Forecaster",
    )

    return fig2, summary_df


def plot_forecast_metric_per_day(
    merged_df, selected_forecasters, selected_metric, scale_factor, units
):
    daily_plots_df = merged_df
    daily_plots_df["date_utc"] = daily_plots_df["timestamp_utc"].dt.date

    # group by forecaster name and date
    daily_metrics_df = (
        daily_plots_df.groupby(["date_utc", "forecaster_name"])
        .agg({"absolute_error": "mean"})
        .reset_index()
    ).rename(columns={"absolute_error": "MAE"})
    # ME
    daily_metrics_df["ME"] = (
        daily_plots_df.groupby(["date_utc", "forecaster_name"])
        .agg({"error": "mean"})
        .reset_index()["error"]
    )

    fig3 = go.Figure()
    for i, forecaster in enumerate(selected_forecasters):
        name_and_version = f"{forecaster.forecaster_name}"
        forecaster_df = daily_metrics_df[daily_metrics_df["forecaster_name"] == name_and_version]
        fig3.add_trace(
            go.Scatter(
                x=forecaster_df["date_utc"],
                y=forecaster_df[selected_metric] / scale_factor,
                # mode="lines+markers",
                name=forecaster.forecaster_name,
                line=dict(color=colours[i % len(colours)]),
            ),
        )

    fig3.update_layout(
        title=f"Daily {selected_metric}",
        xaxis_title="Date",
        yaxis_title=f"{selected_metric} [{units}]",
        legend_title="Forecaster",
    )

    return fig3
