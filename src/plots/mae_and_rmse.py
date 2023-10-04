from plotly import graph_objects as go, express as px

from plots.utils import line_color, MAE_LIMIT_DEFAULT_HORIZON_0, MAE_LIMIT_DEFAULT


def make_rmse_and_mae_plot(df_mae, df_rmse, x_plive_mae, x_plive_rmse, y_plive_mae, y_plive_rmse):
    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Quartz Solar and PVlive MAE with RMSE for Comparison"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Error Value (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )
    fig.add_traces(
        [
            go.Scatter(
                x=df_mae["datetime_utc"],
                y=df_mae["MAE"],
                name="MAE",
                mode="lines",
                line=dict(color=line_color[0]),
            ),
            go.Scatter(
                x=df_rmse["datetime_utc"],
                y=df_rmse["RMSE"],
                name="RMSE",
                mode="lines",
                line=dict(color=line_color[1]),
            ),
            go.Scatter(
                x=x_plive_mae,
                y=y_plive_mae,
                name="MAE PVLive",
                mode="lines",
                line=dict(color=line_color[0], dash="dash"),
            ),
            go.Scatter(
                x=x_plive_rmse,
                y=y_plive_rmse,
                name="RMSE PVLive",
                mode="lines",
                line=dict(color=line_color[1], dash="dash"),
            ),
        ]
    )
    fig.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT])
    return fig


def make_mae_plot(df_mae):
    fig = px.bar(
        df_mae,
        x="datetime_utc",
        y="MAE",
        title="Quartz Solar MAE",
        hover_data=["MAE", "datetime_utc"],
        color_discrete_sequence=["#FFAC5F"],
    )
    fig.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT_HORIZON_0])
    return fig
