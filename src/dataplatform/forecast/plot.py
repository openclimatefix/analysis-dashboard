"""Plotting functions for forecast analysis."""

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dataplatform.forecast.constant import (
    colours,
    theme_background,
    theme_text,
)


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
    strict_horizon_filtering: bool = False,
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
        if strict_horizon_filtering:
            current_forecast_df = all_forecast_data_df[
                all_forecast_data_df["horizon_mins"] == selected_forecast_horizon
            ]
        else:
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
            all_forecast_data_df["initialization_timestamp_utc"].isin(selected_t0s)
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
                x=obs_df["target_timestamp_utc"],
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
                forecaster_with_t0_df = forecaster_df[forecaster_df["initialization_timestamp_utc"] == t0]
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


def _hex_to_rgba(hex_colour: str, alpha: float) -> str:
    """Convert a '#RRGGBB' colour to an 'rgba(r, g, b, alpha)' string."""
    hex_colour = hex_colour.lstrip("#")
    r, g, b = (int(hex_colour[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def _padded_range(values: pd.Series, include_zero: bool = False) -> list[float]:
    """Min/max of a series with 5% padding, optionally forced to include zero."""
    if values.empty:
        return [-1.0, 1.0]
    low = float(values.min())
    high = float(values.max())
    if include_zero:
        low = min(low, 0.0)
        high = max(high, 0.0)
    padding = (high - low) * 0.05 or 1.0
    return [low - padding, high + padding]


# Faded trail recency bands: earlier t0s are bucketed into a fixed number of opacity bands so
# more recent ones show brighter and older ones fade out — while keeping a constant number of
# traces per frame (a Plotly animation requirement), regardless of how many t0s are selected.
TRAIL_BANDS = 5
TRAIL_ALPHAS = [0.45, 0.35, 0.15, 0.08, 0.06]  # most-recent band first


def plot_forecast_time_series_by_t0(
    all_forecast_data_df: pd.DataFrame,
    all_observations_df: pd.DataFrame,
    forecaster_names: list[str],
    observer_names: list[str],
    scale_factor: float,
    units: str,
    selected_t0s: list[datetime],
    show_probabilistic: bool = True,
    show_trail: bool = True,
) -> go.Figure:
    """Plot forecasts one t0 at a time, with a slider to step through t0s.

    Every t0 is rendered as an animation frame, so scrubbing is client side and needs no
    refetch. Below the main plot we show two panels: the change in p50 against the previous
    t0 (which makes a large revision obvious), and — when a forecaster has an `_adjust`
    counterpart selected — the effect of the adjuster (adjusted minus base). The latest t0's
    p50 is kept as a bold static reference in every frame (the "best guess" that persists in
    history), so you can compare each snapshot against it.
    """
    t0s = sorted(selected_t0s)
    forecast_df = all_forecast_data_df[
        all_forecast_data_df["initialization_timestamp_utc"].isin(t0s)
    ]

    has_probabilistic = (
        show_probabilistic
        and "p10_watts" in forecast_df.columns
        and "p90_watts" in forecast_df.columns
    )

    # Pair each base forecaster with its `_adjust` counterpart, where both are selected, so
    # we can show how much the adjuster moves the forecast up/down.
    forecaster_set = set(forecaster_names)
    adjust_pairs = [
        (base, f"{base}_adjust")
        for base in forecaster_names
        if f"{base}_adjust" in forecaster_set
    ]
    has_adjust = len(adjust_pairs) > 0

    # Pre-slice into [forecaster][t0] so frame building is a lookup rather than a filter.
    # Also build the "persisted" best-guess per forecaster: the lowest-horizon value at each
    # target time across all selected t0s (i.e. the most recently-initialised forecast for
    # each target — what actually persisted in history). This spans the whole target range,
    # unlike any single t0 which only covers forward of its own init time.
    by_forecaster: dict[str, dict[datetime, pd.DataFrame]] = {}
    persisted: dict[str, pd.DataFrame] = {}
    for forecaster_name in forecaster_names:
        single_forecaster_df = forecast_df[forecast_df["forecaster_name"] == forecaster_name]
        by_forecaster[forecaster_name] = {
            t0: single_forecaster_df[
                single_forecaster_df["initialization_timestamp_utc"] == t0
            ].sort_values("target_timestamp_utc")
            for t0 in t0s
        }
        if "horizon_mins" in single_forecaster_df.columns and not single_forecaster_df.empty:
            lowest_horizon = single_forecaster_df.groupby("target_timestamp_utc")[
                "horizon_mins"
            ].idxmin()
            persisted[forecaster_name] = single_forecaster_df.loc[
                lowest_horizon
            ].sort_values("target_timestamp_utc")
        else:
            # Fall back to the latest t0's trajectory if horizon isn't available.
            persisted[forecaster_name] = by_forecaster[forecaster_name][t0s[-1]]

    def diff_xy(left_df: pd.DataFrame, right_df: pd.DataFrame):
        """Target timestamps and (p50 of left minus p50 of right), aligned and scaled."""
        merged = left_df.merge(
            right_df[["target_timestamp_utc", "p50_watts"]],
            on="target_timestamp_utc",
            suffixes=("", "_other"),
        )
        return (
            merged["target_timestamp_utc"],
            (merged["p50_watts"] - merged["p50_watts_other"]) / scale_factor,
        )

    def merged_diff(left_df: pd.DataFrame, right_df: pd.DataFrame) -> pd.Series:
        """p50 of left minus p50 of right, aligned on target timestamp (scaled)."""
        return diff_xy(left_df, right_df)[1]

    def delta_for(forecaster_name: str, index: int):
        """(targets, Δp50 vs previous t0) for a forecaster at a given t0 index."""
        current = by_forecaster[forecaster_name][t0s[index]]
        previous = (
            by_forecaster[forecaster_name][t0s[index - 1]]
            if index > 0
            else current.iloc[0:0]
        )
        return diff_xy(current, previous)

    def adjust_for(base: str, adjusted: str, index: int):
        """(targets, adjusted minus base) for an adjuster pair at a given t0 index."""
        return diff_xy(by_forecaster[adjusted][t0s[index]], by_forecaster[base][t0s[index]])

    def _trail_xy(per_index):
        """Concatenate (x, y) from earlier t0 indices into one gapped trace."""
        xs: list = []
        ys: list = []
        for x_series, y_series in per_index:
            xs.extend(x_series.tolist())
            ys.extend(y_series.tolist())
            xs.append(None)
            ys.append(None)
        return xs, ys

    # Persisted delta / adjuster: the delta and adjuster values along the persisted best-guess
    # line, so the subplots show the history for the bold persisted line rather than only the
    # current t0. Computed once here (static), then revealed up to the selected t0 per frame.
    t0_index_of = {t0: index for index, t0 in enumerate(t0s)}

    def _persisted_delta(forecaster_name: str) -> pd.DataFrame:
        """Δ vs previous t0 along the persisted stitch: for each target, the revision the
        forecast that persisted made relative to the t0 before it."""
        persisted_df = persisted[forecaster_name]
        parts = []
        if "initialization_timestamp_utc" in persisted_df.columns:
            for source_t0, group in persisted_df.groupby("initialization_timestamp_utc"):
                index = t0_index_of.get(source_t0)
                if not index:  # None, or 0 (the first t0 has no previous)
                    continue
                x_series, y_series = diff_xy(group, by_forecaster[forecaster_name][t0s[index - 1]])
                parts.append(
                    pd.DataFrame(
                        {
                            "target_timestamp_utc": x_series.reset_index(drop=True),
                            "value": y_series.reset_index(drop=True),
                        }
                    )
                )
        if not parts:
            return pd.DataFrame({"target_timestamp_utc": [], "value": []})
        return pd.concat(parts).sort_values("target_timestamp_utc")

    def _persisted_adjust(base: str, adjusted: str) -> pd.DataFrame:
        """Adjusted minus base along the persisted stitch of each."""
        x_series, y_series = diff_xy(persisted[adjusted], persisted[base])
        return pd.DataFrame(
            {
                "target_timestamp_utc": x_series.reset_index(drop=True),
                "value": y_series.reset_index(drop=True),
            }
        ).sort_values("target_timestamp_utc")

    persisted_delta = {name: _persisted_delta(name) for name in forecaster_names}
    persisted_adjust = {pair: _persisted_adjust(*pair) for pair in adjust_pairs}

    def _splice_at_t0(persisted_df: pd.DataFrame, current_x, current_y, t0):
        """One line: the persisted 'final' values up to t0, then the selected t0's own
        forecast beyond it. Continuous at the marker (there the freshest forecast is t0)."""
        left = persisted_df[persisted_df["target_timestamp_utc"] <= t0]
        future = current_x > t0
        combined = pd.DataFrame(
            {
                "x": list(left["target_timestamp_utc"]) + list(current_x[future]),
                "y": list(left["value"]) + list(current_y[future]),
            }
        ).sort_values("x")
        return combined["x"], combined["y"]

    # Lock the x range across all frames too, so the timeline doesn't shift as the persisted
    # line reveals or the current-t0 line changes. Use the full target span of all the data.
    x_targets = [forecast_df["target_timestamp_utc"]]
    if not all_observations_df.empty:
        x_targets.append(all_observations_df["target_timestamp_utc"])
    all_x_values = pd.concat(x_targets)
    x_range = [all_x_values.min(), all_x_values.max()] if not all_x_values.empty else None

    # Lock the main y range across all frames, otherwise Plotly rescales per frame and a big
    # revision can look deceptively small as you scrub.
    y_columns = ["p50_watts"] + (["p10_watts", "p90_watts"] if has_probabilistic else [])
    y_candidates = [forecast_df[column] for column in y_columns if column in forecast_df]
    if not all_observations_df.empty:
        y_candidates.append(all_observations_df["value_watts"])
    all_y_values = pd.concat(y_candidates) / scale_factor if y_candidates else pd.Series([0.0])
    y_range = _padded_range(all_y_values)

    # Delta panel range: computed up front across every t0 so no frame gets clipped — the
    # big revisions are exactly the ones that were being cut off.
    delta_values = [
        merged_diff(by_forecaster[name][t0s[i]], by_forecaster[name][t0s[i - 1]])
        for name in forecaster_names
        for i in range(1, len(t0s))
    ]
    delta_series = pd.concat(delta_values) if delta_values else pd.Series([0.0])
    delta_range = _padded_range(delta_series, include_zero=True)

    # Adjuster panel range, likewise fixed across all frames.
    if has_adjust:
        adjust_values = [
            merged_diff(by_forecaster[adjusted][t0], by_forecaster[base][t0])
            for base, adjusted in adjust_pairs
            for t0 in t0s
        ]
        adjust_series = pd.concat(adjust_values) if adjust_values else pd.Series([0.0])
        adjust_range = _padded_range(adjust_series, include_zero=True)

    def trail_band_traces(value_fn, count: int, colour: str, group: str) -> list[go.Scatter]:
        """Emit TRAIL_BANDS faded traces for earlier t0s, brighter for more recent ones.

        value_fn(j) returns the (x, y) for earlier t0 index j. Earlier t0s are bucketed by
        recency into fixed bands so the trace count stays constant across frames. The traces
        join the model's own legend group, so toggling a model in the legend also hides its
        faded trails.
        """
        buckets: list[list] = [[] for _ in range(TRAIL_BANDS)]
        for j in range(count):
            recency = (count - 1) - j  # 0 = most recent earlier t0
            band = min(TRAIL_BANDS - 1, recency * TRAIL_BANDS // count) if count else 0
            buckets[band].append(value_fn(j))
        return [
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name=f"{group} (earlier t0s)",
                line={"color": _hex_to_rgba(colour, TRAIL_ALPHAS[band]), "width": 1},
                legendgroup=group,
                showlegend=False,
                hoverinfo="skip",
            )
            for band, (xs, ys) in enumerate(_trail_xy(bucket) for bucket in buckets)
        ]

    def dynamic_traces(t0_index: int) -> list[go.Scatter]:
        """Build the per-t0 traces, in a fixed order that every frame must match."""
        t0 = t0s[t0_index]
        traces: list[go.Scatter] = []

        trail_count = t0_index if show_trail else 0

        for i, forecaster_name in enumerate(forecaster_names):
            colour = colours[i % len(colours)]
            current_df = by_forecaster[forecaster_name][t0]

            # Faded trail of every earlier t0, brighter for more recent t0s. All faded trails
            # (here and on the subplots) share one legend group with a single entry, so they can
            # be toggled on/off by clicking the legend — client-side, with no Streamlit rerun.
            def main_trail_value(j, name=forecaster_name):
                earlier_df = by_forecaster[name][t0s[j]]
                return earlier_df["target_timestamp_utc"], earlier_df["p50_watts"] / scale_factor

            traces.extend(
                trail_band_traces(main_trail_value, trail_count, colour, group=forecaster_name)
            )

            # p10/p90 band. Kept as traces even when probabilistic is off (just empty) so
            # the trace count stays constant across frames.
            traces.append(
                go.Scatter(
                    x=current_df["target_timestamp_utc"] if has_probabilistic else [],
                    y=current_df["p10_watts"] / scale_factor if has_probabilistic else [],
                    mode="lines",
                    line={"color": colour, "width": 0},
                    legendgroup=forecaster_name,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            traces.append(
                go.Scatter(
                    x=current_df["target_timestamp_utc"] if has_probabilistic else [],
                    y=current_df["p90_watts"] / scale_factor if has_probabilistic else [],
                    mode="lines",
                    line={"color": colour, "width": 0},
                    fill="tonexty" if has_probabilistic else None,
                    fillcolor=_hex_to_rgba(colour, 0.2),
                    legendgroup=forecaster_name,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            traces.append(
                go.Scatter(
                    x=current_df["target_timestamp_utc"],
                    y=current_df["p50_watts"] / scale_factor,
                    mode="lines",
                    name=forecaster_name,
                    line={"color": colour, "width": 2},
                    legendgroup=forecaster_name,
                )
            )

        # Persisted best-guess, revealed only up to the selected t0. Because the persisted
        # value at each target time is the most recent forecast for it, target times at or
        # before the t0 marker never change as you scrub further forward — so the left of the
        # marker stays static (locked-in history) while the future is shown by the current-t0
        # line.
        for i, forecaster_name in enumerate(forecaster_names):
            colour = colours[i % len(colours)]
            persisted_df = persisted[forecaster_name]
            revealed = persisted_df[persisted_df["target_timestamp_utc"] <= t0]
            traces.append(
                go.Scatter(
                    x=revealed["target_timestamp_utc"],
                    y=revealed["p50_watts"] / scale_factor,
                    mode="lines",
                    name=f"{forecaster_name} (persisted)",
                    line={"color": colour, "width": 2},
                    legendgroup=forecaster_name,
                    showlegend=False,
                )
            )

        # Vertical marker at the current t0, separating hindcast from true forecast horizon.
        traces.append(
            go.Scatter(
                x=[t0, t0],
                y=y_range,
                mode="lines",
                name="t0",
                line={"color": "white", "width": 1, "dash": "dot"},
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Delta panel: a faded trail of earlier t0s' deltas (toggleable), plus a single solid
        # line tracking the delta along the persisted best-guess, revealed up to the t0 marker
        # so it mirrors the bold persisted line in the main chart.
        for i, forecaster_name in enumerate(forecaster_names):
            colour = colours[i % len(colours)]
            traces.extend(
                trail_band_traces(
                    lambda j, name=forecaster_name: delta_for(name, j),
                    trail_count,
                    colour,
                    group=forecaster_name,
                )
            )
            delta_x, delta_y = delta_for(forecaster_name, t0_index)
            splice_x, splice_y = _splice_at_t0(
                persisted_delta[forecaster_name], delta_x, delta_y, t0
            )
            traces.append(
                go.Scatter(
                    x=splice_x,
                    y=splice_y,
                    mode="lines",
                    name=f"{forecaster_name} Δ",
                    line={"color": colour, "width": 2},
                    legendgroup=forecaster_name,
                    showlegend=False,
                )
            )

        # Adjuster panel: same shape — faded trail (toggleable) plus a single solid line
        # tracking the adjuster effect along the persisted best-guess, revealed up to the t0.
        if has_adjust:
            for base, adjusted in adjust_pairs:
                colour = colours[forecaster_names.index(base) % len(colours)]
                traces.extend(
                    trail_band_traces(
                        lambda j, b=base, a=adjusted: adjust_for(b, a, j),
                        trail_count,
                        colour,
                        group=base,
                    )
                )
                adjust_x, adjust_y = adjust_for(base, adjusted, t0_index)
                splice_x, splice_y = _splice_at_t0(
                    persisted_adjust[(base, adjusted)], adjust_x, adjust_y, t0
                )
                traces.append(
                    go.Scatter(
                        x=splice_x,
                        y=splice_y,
                        mode="lines",
                        name=f"{adjusted} − {base}",
                        line={"color": colour, "width": 2},
                        legendgroup=base,
                        showlegend=False,
                    )
                )

        return traces

    lower_panels = 1 + (1 if has_adjust else 0)
    subplot_titles = ["Forecast at selected t0", "Change in p50 vs previous t0"]
    if has_adjust:
        subplot_titles.append("Adjuster effect (adjusted − base)")

    # Panel proportions: with the adjuster panel it's 50 / 25 / 25; without it, the main
    # plot keeps two thirds. The absolute height is set client-side from the screen size (see
    # render_animated_chart), so here we only fix the relative split.
    row_heights = [0.5, 0.25, 0.25] if has_adjust else [0.66, 0.34]

    fig = make_subplots(
        rows=1 + lower_panels,
        cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.06,
        subplot_titles=subplot_titles,
    )

    # Static observation traces are added first, so the dynamic traces the frames replace
    # start at a known, stable offset.
    for observer_name in observer_names:
        obs_df = all_observations_df[all_observations_df["observer_name"] == observer_name]
        if obs_df.empty:
            continue
        if observer_name == "pvlive_in_day":
            line = {"color": "white", "dash": "dash"}
        elif observer_name == "pvlive_day_after":
            line = {"color": "white"}
        else:
            line = {}
        fig.add_trace(
            go.Scatter(
                x=obs_df["target_timestamp_utc"],
                y=obs_df["value_watts"] / scale_factor,
                mode="lines",
                name=observer_name,
                line=line,
            ),
            row=1,
            col=1,
        )

    static_trace_count = len(fig.data)
    # each lower panel: TRAIL_BANDS faded trail traces + the current line, per forecaster / pair
    delta_trace_count = len(forecaster_names) * (TRAIL_BANDS + 1)
    adjust_trace_count = len(adjust_pairs) * (TRAIL_BANDS + 1)
    # per forecaster: TRAIL_BANDS trail bands, p10, p90, p50, persisted; plus one t0 marker line
    main_trace_count = len(forecaster_names) * (TRAIL_BANDS + 4) + 1

    def row_for_offset(offset: int) -> int:
        if offset < main_trace_count:
            return 1
        if offset < main_trace_count + delta_trace_count:
            return 2
        return 3

    initial_traces = dynamic_traces(0)
    for offset, trace in enumerate(initial_traces):
        fig.add_trace(trace, row=row_for_offset(offset), col=1)

    dynamic_indices = list(
        range(
            static_trace_count,
            static_trace_count + main_trace_count + delta_trace_count + adjust_trace_count,
        )
    )

    fig.frames = [
        go.Frame(
            name=t0s[t0_index].strftime("%Y-%m-%d %H:%M"),
            data=dynamic_traces(t0_index),
            traces=dynamic_indices,
        )
        for t0_index in range(len(t0s))
    ]

    steps = [
        {
            "label": t0.strftime("%H:%M"),
            "method": "animate",
            "args": [
                [t0.strftime("%Y-%m-%d %H:%M")],
                {
                    "mode": "immediate",
                    "frame": {"duration": 0, "redraw": True},
                    "transition": {"duration": 0},
                },
            ],
        }
        for t0 in t0s
    ]

    # Zero reference lines on the difference panels.
    fig.add_hline(y=0, line={"color": "grey", "width": 1}, row=2, col=1)
    if has_adjust:
        fig.add_hline(y=0, line={"color": "grey", "width": 1}, row=3, col=1)

    # "Now" marker (current wall-clock time), so it's obvious where we are in time. Static,
    # spanning all panels; only drawn if it falls within the plotted target range. The label
    # is added separately because Plotly's add_vline annotation path can't handle a datetime x.
    now = datetime.now(timezone.utc)
    all_targets = forecast_df["target_timestamp_utc"]
    if not all_targets.empty and all_targets.min() <= now <= all_targets.max():
        fig.add_vline(
            x=now,
            line={"color": "#FF4901", "width": 1.5},
            row="all",
            col=1,
        )
        fig.add_annotation(
            x=now,
            xref="x",
            y=1.0,
            yref="y domain",
            text="now",
            showarrow=False,
            yanchor="bottom",
            bgcolor="#000000",
            font={"color": "#FF4901"},
        )

    fig.update_layout(
        title="Forecast evolution by t0",
        # Rendered standalone in an iframe rather than via st.plotly_chart (which drops
        # animation frames on fullscreen), so the app theme has to be restated here.
        template="plotly_dark",
        paper_bgcolor=theme_background,
        plot_bgcolor=theme_background,
        font={"color": theme_text},
        # No fixed height: the container script sizes the chart to the viewer's screen.
        autosize=True,
        margin={"t": 60, "b": 90, "l": 60, "r": 30},
        legend_title="Forecaster",
        # Clicking a model in the legend toggles its whole group, including its faded trails.
        legend={"groupclick": "togglegroup"},
        hovermode="x unified",
        sliders=[
            {
                "active": 0,
                "currentvalue": {"prefix": "t0: "},
                "pad": {"t": 50},
                "steps": steps,
            }
        ],
    )
    fig.update_yaxes(title_text=f"Generation [{units}]", range=y_range, autorange=False, row=1, col=1)
    fig.update_yaxes(title_text=f"Δ [{units}]", range=delta_range, autorange=False, row=2, col=1)
    if has_adjust:
        fig.update_yaxes(title_text=f"Adj [{units}]", range=adjust_range, autorange=False, row=3, col=1)
    fig.update_xaxes(title_text="Time", row=1 + lower_panels, col=1)
    # Fix the x range on every panel so the timeline stays constant across frames.
    # autorange=False is required: with animation frames Plotly otherwise re-autoranges on
    # load to the (narrow) first frame, so the chart opens zoomed in until "reset axes".
    if x_range is not None:
        for row in range(1, 2 + lower_panels):
            fig.update_xaxes(range=x_range, autorange=False, row=row, col=1)

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
    daily_plots_df["date_utc"] = daily_plots_df["target_timestamp_utc"].dt.date

    # group by forecaster name and date
    daily_metrics_df = (
        daily_plots_df.groupby(["date_utc", "forecaster_name"])
        .agg({"absolute_error": "mean", "error": "mean"})
        .reset_index()
    )

    daily_metrics_df = daily_metrics_df.rename(columns={"absolute_error": "MAE", "error": "ME"})

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

def make_summary_data(
    merged_df: pd.DataFrame,
    min_horizon: int,
    max_horizon: int,
    scale_factor: float,
    units: str,
) -> pd.DataFrame:
    """Make summary data table for given min and max horizon mins."""
    # Reduce by horizon mins
    summary_table_df = merged_df[
        (merged_df["horizon_mins"] >= min_horizon)
        & (merged_df["horizon_mins"] <= max_horizon)
    ]

    capacity_watts_col = "effective_capacity_watts_observation"

    value_columns = [
        "error",
        "absolute_error",
        "value_watts",
        capacity_watts_col,
    ]
    plevels = [10, 25, 50, 75, 90]
    plevel_metrics = []
    for plevel in plevels:
        if f"p{plevel}_below" in summary_table_df.columns:
            plevel_metrics.append(f"p{plevel}_below")
            value_columns.append(f"p{plevel}_below")
    summary_table_df = summary_table_df[["forecaster_name", *value_columns]]

    summary_table_df = summary_table_df.groupby("forecaster_name").mean()

    # Scale by units
    non_plevel_columns = [
        col for col in summary_table_df.columns if col not in plevel_metrics
    ]
    summary_table_df[non_plevel_columns] = (
        summary_table_df[non_plevel_columns] / scale_factor
    )
    summary_table_df[plevel_metrics] = summary_table_df[plevel_metrics] * 100
    summary_table_df = summary_table_df.rename(
        {
            col: f"{col} [{units}]"
            for col in summary_table_df.columns
            if col not in plevel_metrics
        },
        axis=1,
    )
    summary_table_df = summary_table_df.rename(
        {
            col: f"{col} [%]"
            for col in summary_table_df.columns
            if col in plevel_metrics
        },
        axis=1,
    )

    # Pivot table, so forecaster_name is columns
    summary_table_df = summary_table_df.pivot_table(
        columns=summary_table_df.index,
        values=summary_table_df.columns.tolist(),
    )

    # Rename
    summary_table_df = summary_table_df.rename(
        columns={
            "error": "ME",
            "absolute_error": "MAE",
            capacity_watts_col: "Mean Capacity",
            "value_watts": "Mean Observed Generation",
        },
    )

    return summary_table_df


def make_summary_data_metric_vs_horizon_minutes(
    merged_df: pd.DataFrame,
) -> pd.DataFrame:
    """Make summary data for forecast metric vs horizon minutes."""
    # Get the mean observed generation
    mean_observed_generation = merged_df["value_watts"].mean()

    summary_df = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg(
            {
                "absolute_error": ["mean", "std", "count"],
                "error": "mean",
            },
        )
        .reset_index()
    )

    summary_df.columns = ["_".join(col).strip() for col in summary_df.columns.values]
    summary_df.columns = [
        col[:-1] if col.endswith("_") else col for col in summary_df.columns
    ]

    # Calculate sem of MAE
    summary_df["sem"] = summary_df["absolute_error_std"] / (
        summary_df["absolute_error_count"] ** 0.5
    )

    summary_df["effective_capacity_watts_observation"] = (
        merged_df.groupby(["horizon_mins", "forecaster_name"])
        .agg({"effective_capacity_watts_observation": "mean"})
        .reset_index()["effective_capacity_watts_observation"]
    )

    summary_df = summary_df.rename(
        columns={"absolute_error_mean": "MAE", "error_mean": "ME"}
    )
    summary_df["NMAE (by capacity)"] = (
        summary_df["MAE"] / summary_df["effective_capacity_watts_observation"]
    )
    summary_df["NMAE (by mean observed generation)"] = (
        summary_df["MAE"] / mean_observed_generation
    )

    return summary_df

def plot_quantile_plot(
        merged_df: pd.DataFrame,
        forecaster_names: list):

    quantiles_probs = {}
    for forecaster_name in forecaster_names:

        forecaster_df = merged_df[merged_df["forecaster_name"] == forecaster_name]
        # get rid of night time zeros
        forecaster_df = forecaster_df[forecaster_df["value_watts"] != 0]
        quantiles_probs[forecaster_name] = {}

        values = []
        for plevel in [10,50,90]:
            if f'p{plevel}_watts' in forecaster_df.columns:
                v = (forecaster_df[f'p{plevel}_watts'] >= forecaster_df['value_watts']).mean()
                values.append({'plevel': plevel/100, 'value': v})

        quantiles_probs[forecaster_name] = pd.DataFrame(data=values)


    fig = go.Figure()
    for i, forecaster_name in enumerate(forecaster_names):
        forecaster_df = quantiles_probs[forecaster_name]
        fig.add_trace(
            go.Scatter(
                x=forecaster_df["plevel"],
                y=forecaster_df["value"],
                name=forecaster_name,
                line={"color": colours[i % len(colours)]},
            ),
        )
    
    # lets also put a straight line on from 0,0 to 1,1 and colour it white
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            name="Perfect Forecast",
            line={"color": "white", "dash": "dash"},
        )
    )

    fig.update_layout(
        title="Quantile plot",
        xaxis_title="Quantile",
        yaxis_title="Fraction below (forecast < observed)",
    )

    # update the range of the y and x axis to 0 and 1
    fig.update_xaxes(range=[0, 1])
    fig.update_yaxes(range=[0, 1])

    return fig

    

