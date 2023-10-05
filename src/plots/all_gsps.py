from plotly import graph_objects as go

from plots.utils import line_color


def make_all_gsps_plots(x_mae_all_gsp, y_mae_all_gsp):
    fig7 = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text="Daily Latest MAE All GSPs"),
            xaxis=go.layout.XAxis(title=go.layout.xaxis.Title(text="Date")),
            yaxis=go.layout.YAxis(title=go.layout.yaxis.Title(text="Error Value (MW)")),
            legend=go.layout.Legend(title=go.layout.legend.Title(text="Chart Legend")),
        )
    )
    fig7.add_traces(
        go.Scatter(
            x=x_mae_all_gsp,
            y=y_mae_all_gsp,
            mode="lines",
            name="Daily Latest MAE All GSPs",
            line=dict(color=line_color[4]),
        ),
    )
    return fig7
