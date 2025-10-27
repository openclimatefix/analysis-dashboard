from plotly import graph_objects as go, express as px

from plots.utils import get_colour_from_model_name, MAE_LIMIT_DEFAULT_HORIZON_0, MAE_LIMIT_DEFAULT


def make_rmse_and_mae_plot(df_mae, df_rmse, x_plive_mae, x_plive_rmse, y_plive_mae, y_plive_rmse):
    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Quartz Solar and PVlive MAE with RMSE for Comparison"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Error Value (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )

    mae_color = get_colour_from_model_name("MAE")
    rmse_color = get_colour_from_model_name("RMSE")

    fig.add_traces(
        [
            go.Scatter(
                x=df_mae["datetime_utc"],
                y=df_mae["MAE"],
                name="MAE",
                mode="lines",
                line=dict(color=mae_color),
            ),
            go.Scatter(
                x=df_rmse["datetime_utc"],
                y=df_rmse["RMSE"],
                name="RMSE",
                mode="lines",
                line=dict(color=rmse_color),
            ),
            go.Scatter(
                x=x_plive_mae,
                y=y_plive_mae,
                name="MAE PVLive",
                mode="lines",
                line=dict(color=mae_color, dash="dash"),
            ),
            go.Scatter(
                x=x_plive_rmse,
                y=y_plive_rmse,
                name="RMSE PVLive",
                mode="lines",
                line=dict(color=rmse_color, dash="dash"),
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
        title="Quartz Solar MAE - 0 forecast horizon* "
              "<br><sup>Its actually the MAE for the last forecast made, which is normally the same as the "
              "0 minute forecast horizon</sup>",
        hover_data=["MAE", "datetime_utc"],
        color_discrete_sequence=[get_colour_from_model_name("MAE_bar")],
    )
    fig.update_layout(yaxis_range=[0, MAE_LIMIT_DEFAULT_HORIZON_0])
    return fig
