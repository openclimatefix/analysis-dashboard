import pandas as pd
from plotly import graph_objects as go

from main import get_x_y, MAE_LIMIT_DEFAULT
from plots.utils import line_color


def make_mae_by_forecast_horizon(df_mae, forecast_horizon_selection, metric_values_by_forecast_horizon):
    # MAE by forecast horizon adding go.Figure
    fig2 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Quartz Solar MAE by Forecast Horizon (selected in sidebar)"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="MAE (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=df_mae["datetime_utc"],
            y=df_mae["MAE"],
            mode="lines",
            name="Daily Total MAE",
            line=dict(color="#FFD053"),
        )
    )
    for forecast_horizon in forecast_horizon_selection:
        metric_values = metric_values_by_forecast_horizon[forecast_horizon]
        x_mae_horizon, y_mae_horizon = get_x_y(metric_values=metric_values)

        df = pd.DataFrame(
            {
                "MAE": y_mae_horizon,
                "datetime_utc": x_mae_horizon,
            }
        )

        fig2.add_traces(
            [
                go.Scatter(
                    x=df["datetime_utc"],
                    y=df["MAE"],
                    name=f"{forecast_horizon}-minute horizon",
                    mode="lines",
                    line=dict(color=line_color[forecast_horizon_selection.index(forecast_horizon)]),
                )
            ]
        )
    fig2.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT])
    return fig2


def make_mae_forecast_horizon_group_by_forecast_horizon(forecast_horizon_selection, metric_values_by_forecast_horizon):
    fig4 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(
                text="Quartz Solar MAE by Forecast Horizon for Date Range(selected in sidebar)"
            ),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="MAE (MW)")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Forecast Horizon (minutes)")),
        )
    )
    for forecast_horizon in forecast_horizon_selection:
        metric_values = metric_values_by_forecast_horizon[forecast_horizon]
        x_mae_horizon = [value.datetime_interval.start_datetime_utc for value in metric_values]
        y_mae_horizon = [round(float(value.value), 2) for value in metric_values]

        df_mae_horizon = pd.DataFrame(
            {
                "MAE": y_mae_horizon,
                "datetime_utc": x_mae_horizon,
                "forecast_horizon": forecast_horizon,
            }
        )

        fig4.add_traces(
            [
                go.Scatter(
                    x=df_mae_horizon["MAE"],
                    y=df_mae_horizon["forecast_horizon"],
                    name=f"{forecast_horizon}-minute horizon",
                    mode="markers",
                    line=dict(color=line_color[forecast_horizon_selection.index(forecast_horizon)]),
                ),
            ]
        )
        fig4.update_layout(
            xaxis=dict(tickmode="linear", tick0=0, dtick=50),
            yaxis=dict(tickmode="linear", tick0=0, dtick=60),
        )
    return fig4


def make_mae_vs_froecast_horizon_group_by_date(forecast_horizon_selection, metric_values_by_forecast_horizon):
    # add chart with forecast horizons on x-axis and line for each day in the date range
    fig5 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Quartz Solar MAE Forecast Horizon Values by Date"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Forecast Horizon (minutes)")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="MAE (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Date")),
        )
    )
    # make an empty array to capture data for each line
    traces = []
    # make an empty array to capture values for each forecast horizon in the date range
    dfs = []
    # get data for each forecast horizon
    # read database metric values
    for forecast_horizon in forecast_horizon_selection:
        metric_values = metric_values_by_forecast_horizon[forecast_horizon]
        dates = [value.datetime_interval.start_datetime_utc for value in metric_values]
        mae_value = [round(float(value.value), 2) for value in metric_values]
        forecast_horizons = [value.forecast_horizon_minutes for value in metric_values]

        # create dataframe for each date with a value for each forecast horizon
        data = pd.DataFrame(
            {
                "MAE": mae_value,
                "datetime_utc": dates,
                "forecast_horizon": forecast_horizons,
            }
        )

        dfs.append(data)
    # merge dataframes
    all_forecast_horizons_df = pd.concat(dfs, axis=0).sort_values(by=["datetime_utc"], ascending=True)
    # group by date
    result = {result_.index[0]: result_ for _, result_ in all_forecast_horizons_df.groupby("datetime_utc")}
    # loop through each date group in the dictionary and add to traces
    len_colours = len(line_color)
    # loop through each date group in the dictionary and add to traces
    for i in result:
        # sort results by day
        results_for_day = result[i]
        results_for_day = results_for_day.sort_values(by=["forecast_horizon"], ascending=True)
        traces.append(
            go.Scatter(
                x=results_for_day["forecast_horizon"].sort_values(ascending=True),
                y=results_for_day["MAE"],
                name=results_for_day["datetime_utc"].iloc[0].strftime("%Y-%m-%d"),
                mode="lines+markers",
                line=dict(color=line_color[i % len_colours]),
            )
        )
    fig5.add_traces(traces)
    fig5.update_layout(
        xaxis=dict(tickmode="linear", tick0=0, dtick=60),
        yaxis=dict(tickmode="linear", tick0=0, dtick=50),
    )
    fig5.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT])
    return all_forecast_horizons_df, fig5
