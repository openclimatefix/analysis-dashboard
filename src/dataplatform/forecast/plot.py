"""Plotting functions for forecast analysis."""

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

from dataplatform.forecast.constant import colours


def make_time_series_trace(
    fig: go.Figure,
    forecaster_df: pd.DataFrame,
    forecaster_name: str,
    scale_factor: float,
    i: int,
    show_probabilistic: bool = True,
) -> go.Figure:
    """Make time series trace for a forecaster.

    Include p10 and p90 shading if show_probabilistic is True.
    """
    fig.add_trace(
        go.Scatter(
            x=forecaster_df["target_timestamp_utc"],
            y=forecaster_df["p50_watts"] / scale_factor,
            mode="lines",
            name=forecaster_name,
            line={"color": colours[i % len(colours)]},
            legendgroup=forecaster_name,
        ),
    )
    if (
        show_probabilistic
        and "p10_watts" in forecaster_df.columns
        and "p90_watts" in forecaster_df.columns
    ):
        fig.add_trace(
            go.Scatter(
                x=forecaster_df["target_timestamp_utc"],
                y=forecaster_df["p10_watts"] / scale_factor,
                mode="lines",
                line={"color": colours[i % len(colours)], "width": 0},
                legendgroup=forecaster_name,
                showlegend=False,
            ),
        )

        fig.add_trace(
            go.Scatter(
                x=forecaster_df["target_timestamp_utc"],
                y=forecaster_df["p90_watts"] / scale_factor,
                mode="lines",
                line={"color": colours[i % len(colours)], "width": 0},
                legendgroup=forecaster_name,
                showlegend=False,
                fill="tonexty",
            ),
        )

    return fig


def plot_forecast_time_series(
    all_forecast_data_df: pd.DataFrame,
    all_observations_df: pd.DataFrame,
    forecaster_names: list[str],
    observer_names: list[str],
    scale_factor: float,
    units: str,
    selected_forecast_type: str,
    selected_forecast_horizon: int,
    selected_t0s: list[datetime],
    show_probabilistic: bool = True,
) -> go.Figure:
    """Plot forecast time series.

    This make a plot of the raw forecasts and observations, for mulitple forecast.
    """
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
    elif selected_forecast_type == "t0":
        current_forecast_df = all_forecast_data_df[
            all_forecast_data_df["init_timestamp"].isin(selected_t0s)
        ]

    # plot the results
    fig = go.Figure()
    for observer_name in observer_names:
        obs_df = all_observations_df[all_observations_df["observer_name"] == observer_name]

        if observer_name == "pvlive_in_day":
            # dashed white line
            line = {"color": "white", "dash": "dash"}
        elif observer_name == "pvlive_day_after":
            line = {"color": "white"}
        else:
            line = {}

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
        if selected_forecast_type in ["Current", "Horizon"]:
            fig = make_time_series_trace(
                fig,
                forecaster_df,
                forecaster_name,
                scale_factor,
                i,
                show_probabilistic,
            )
        elif selected_forecast_type == "t0":
            for _, t0 in enumerate(selected_t0s):
                forecaster_with_t0_df = forecaster_df[forecaster_df["init_timestamp"] == t0]
                forecaster_name_wth_t0 = f"{forecaster_name} | t0: {t0}"
                fig = make_time_series_trace(
                    fig,
                    forecaster_with_t0_df,
                    forecaster_name_wth_t0,
                    scale_factor,
                    i,
                    show_probabilistic,
                )

    fig.update_layout(
        title="Current Forecast",
        xaxis_title="Time",
        yaxis_title=f"Generation [{units}]",
        legend_title="Forecaster",
    )

    return fig


def plot_forecast_metric_vs_horizon_minutes(
    summary_df: pd.DataFrame,
    forecaster_names: list[str],
    selected_metric: str,
    scale_factor: float,
    units: str,
    show_sem: bool,
) -> go.Figure:
    """Plot forecast metric vs horizon minutes."""
    fig2 = go.Figure()

    for i, forecaster_name in enumerate(forecaster_names):
        forecaster_df = summary_df[summary_df["forecaster_name"] == forecaster_name]
        fig2.add_trace(
            go.Scatter(
                x=forecaster_df["horizon_mins"],
                y=forecaster_df[selected_metric] / scale_factor,
                mode="lines+markers",
                name=forecaster_name,
                line={"color": colours[i % len(colours)]},
                legendgroup=forecaster_name,
            ),
        )

        if show_sem:
            fig2.add_trace(
                go.Scatter(
                    x=forecaster_df["horizon_mins"],
                    y=(forecaster_df[selected_metric] - 1.96 * forecaster_df["sem"]) / scale_factor,
                    mode="lines",
                    line={"color": colours[i % len(colours)], "width": 0},
                    legendgroup=forecaster_name,
                    showlegend=False,
                ),
            )

            fig2.add_trace(
                go.Scatter(
                    x=forecaster_df["horizon_mins"],
                    y=(forecaster_df[selected_metric] + 1.96 * forecaster_df["sem"]) / scale_factor,
                    mode="lines",
                    line={"color": colours[i % len(colours)], "width": 0},
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

    if selected_metric == "MAE":
        fig2.update_yaxes(range=[0, None])

    return fig2


def plot_forecast_metric_per_day(
    merged_df: pd.DataFrame,
    forecaster_names: list,
    selected_metric: str,
    scale_factor: float,
    units: str,
) -> go.Figure:
    """Plot forecast metric per day."""
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
    for i, forecaster_name in enumerate(forecaster_names):
        name_and_version = f"{forecaster_name}"
        forecaster_df = daily_metrics_df[daily_metrics_df["forecaster_name"] == name_and_version]
        fig3.add_trace(
            go.Scatter(
                x=forecaster_df["date_utc"],
                y=forecaster_df[selected_metric] / scale_factor,
                name=forecaster_name,
                line={"color": colours[i % len(colours)]},
            ),
        )

    fig3.update_layout(
        title=f"Daily {selected_metric}",
        xaxis_title="Date",
        yaxis_title=f"{selected_metric} [{units}]",
        legend_title="Forecaster",
    )

    if selected_metric == "MAE":
        fig3.update_yaxes(range=[0, None])

    return fig3
