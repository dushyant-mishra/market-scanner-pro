"""
Market Scanner V2 — Plotly Chart Builders
Dark-themed financial charts for the Streamlit dashboard.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import COLORS


# ------------------------------------------------------------------
# Base layout helper
# ------------------------------------------------------------------

def get_chart_layout() -> dict:
    """Return a base Plotly layout dict shared by all charts."""
    return dict(
        paper_bgcolor=COLORS["bg_primary"],
        plot_bgcolor=COLORS["bg_primary"],
        font=dict(
            color=COLORS["text_primary"],
            family="Inter, sans-serif",
            size=12,
        ),
        margin=dict(l=48, r=24, t=48, b=32),
        xaxis=dict(
            gridcolor=f"rgba(255,255,255,0.1)",
            zerolinecolor=f"rgba(255,255,255,0.1)",
        ),
        yaxis=dict(
            gridcolor=f"rgba(255,255,255,0.1)",
            zerolinecolor=f"rgba(255,255,255,0.1)",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
        hoverlabel=dict(
            bgcolor=COLORS["bg_card"],
            font_size=12,
            font_family="Inter, sans-serif",
        ),
    )


# ------------------------------------------------------------------
# 1. Price chart (candlestick + indicators)
# ------------------------------------------------------------------

def create_price_chart(hist: pd.DataFrame, ticker: str) -> go.Figure:
    """Full interactive price chart with candlestick, volume, RSI, and MACD.

    Parameters
    ----------
    hist : pd.DataFrame
        Must contain Date, Open, High, Low, Close, Volume columns.
        Optionally: RSI, MACD, MACD_Signal, MACD_Hist,
        BB_Upper, BB_Middle, BB_Lower, MA20, MA50, MA200.
    ticker : str
        Stock symbol used in the chart title.
    """
    has_rsi = "RSI" in hist.columns
    has_macd = all(c in hist.columns for c in ("MACD", "MACD_Signal", "MACD_Hist"))
    has_bb = all(c in hist.columns for c in ("BB_Upper", "BB_Lower"))

    # Determine how many subplots we need
    row_specs: list[list[dict]] = []
    row_heights: list[float] = []
    subplot_titles: list[str] = []

    # Row 1 — price (always present)
    row_specs.append([{"type": "xy"}])
    row_heights.append(0.60)
    subplot_titles.append("Price")

    # Row 2 — volume (always present)
    row_specs.append([{"type": "xy"}])
    row_heights.append(0.15)
    subplot_titles.append("Volume")

    # Row 3 — RSI
    if has_rsi:
        row_specs.append([{"type": "xy"}])
        row_heights.append(0.15)
        subplot_titles.append("RSI")

    # Row 4 — MACD
    if has_macd:
        row_specs.append([{"type": "xy"}])
        row_heights.append(0.10)
        subplot_titles.append("MACD")

    n_rows = len(row_specs)

    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
        specs=row_specs,
    )

    dates = hist["Date"] if "Date" in hist.columns else hist.index

    # ── Candlestick ──────────────────────────────────────────────
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            increasing_line_color=COLORS["chart_up"],
            decreasing_line_color=COLORS["chart_down"],
            increasing_fillcolor=COLORS["chart_up"],
            decreasing_fillcolor=COLORS["chart_down"],
            name="Price",
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    # Moving averages
    ma_styles = {
        "MA20": dict(color="#ffa502", width=1),
        "MA50": dict(color="#6366f1", width=1.2),
        "MA200": dict(color="#ff6b35", width=1.5, dash="dot"),
    }
    for ma_name, style in ma_styles.items():
        if ma_name in hist.columns:
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=hist[ma_name],
                    mode="lines",
                    name=ma_name,
                    line=style,
                    opacity=0.8,
                ),
                row=1,
                col=1,
            )

    # Bollinger Bands (shaded)
    if has_bb:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=hist["BB_Upper"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=hist["BB_Lower"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(99,102,241,0.08)",
                name="Bollinger Bands",
            ),
            row=1,
            col=1,
        )

    # ── Volume ───────────────────────────────────────────────────
    vol_colors = [
        COLORS["chart_up"] if c >= o else COLORS["chart_down"]
        for c, o in zip(hist["Close"], hist["Open"])
    ]
    fig.add_trace(
        go.Bar(
            x=dates,
            y=hist["Volume"],
            marker_color=vol_colors,
            marker_line_width=0,
            opacity=0.65,
            name="Volume",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # ── RSI ──────────────────────────────────────────────────────
    rsi_row = 3
    if has_rsi:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=hist["RSI"],
                mode="lines",
                line=dict(color=COLORS["accent"], width=1.4),
                name="RSI",
            ),
            row=rsi_row,
            col=1,
        )
        # Overbought / oversold reference lines & shaded zones
        fig.add_hrect(
            y0=70, y1=100,
            fillcolor="rgba(255,71,87,0.08)",
            line_width=0,
            row=rsi_row,
            col=1,
        )
        fig.add_hrect(
            y0=0, y1=30,
            fillcolor="rgba(0,212,170,0.08)",
            line_width=0,
            row=rsi_row,
            col=1,
        )
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="rgba(255,71,87,0.5)",
            line_width=1,
            row=rsi_row,
            col=1,
        )
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color="rgba(0,212,170,0.5)",
            line_width=1,
            row=rsi_row,
            col=1,
        )
        fig.update_yaxes(range=[0, 100], row=rsi_row, col=1)

    # ── MACD ─────────────────────────────────────────────────────
    if has_macd:
        macd_row = rsi_row + 1 if has_rsi else 3
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=hist["MACD"],
                mode="lines",
                line=dict(color=COLORS["accent"], width=1.2),
                name="MACD",
            ),
            row=macd_row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=hist["MACD_Signal"],
                mode="lines",
                line=dict(color="#ff6b35", width=1.2),
                name="Signal",
            ),
            row=macd_row,
            col=1,
        )
        macd_colors = [
            COLORS["chart_up"] if v >= 0 else COLORS["chart_down"]
            for v in hist["MACD_Hist"]
        ]
        fig.add_trace(
            go.Bar(
                x=dates,
                y=hist["MACD_Hist"],
                marker_color=macd_colors,
                marker_line_width=0,
                opacity=0.55,
                name="Histogram",
                showlegend=False,
            ),
            row=macd_row,
            col=1,
        )

    # ── Layout ───────────────────────────────────────────────────
    base = get_chart_layout()
    base.update(
        margin=dict(l=48, r=24, t=24, b=32),
        height=800,
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color=COLORS["text_secondary"]),
        ),
        hovermode="x unified",
    )
    fig.update_layout(**base)

    # Grid styling for all axes
    for i in range(1, n_rows + 1):
        fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", row=i, col=1)
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", row=i, col=1)

    return fig


# ------------------------------------------------------------------
# 2. Forecast chart
# ------------------------------------------------------------------

def create_forecast_chart(
    current_price: float, forecast: dict, ticker: str
) -> go.Figure:
    """Visual price range forecast with bear/base/bull bands.

    Parameters
    ----------
    current_price : float
    forecast : dict
        Keyed by horizon string (e.g. ``"30"`` or ``"90"``), each value is a
        dict with keys ``bear``, ``base``, ``bull`` (price targets).
    ticker : str
    """
    fig = go.Figure()

    # X positions for each horizon
    horizons = sorted(forecast.keys(), key=lambda h: int(h))
    x_labels = [f"{h}-Day" for h in horizons]

    # Current price line across full width
    fig.add_hline(
        y=current_price,
        line_dash="dash",
        line_color=COLORS["text_secondary"],
        line_width=1.5,
        annotation_text=f"Current ${current_price:,.2f}",
        annotation_position="top left",
        annotation_font_color=COLORS["text_secondary"],
    )

    zone_config = [
        ("bear", "base", "rgba(255,71,87,0.15)", COLORS["bearish"], "Bear"),
        ("base", "bull", "rgba(255,165,2,0.12)", COLORS["neutral"], "Base"),
        ("bull", None, "rgba(0,212,170,0.12)", COLORS["bullish"], "Bull"),
    ]

    for lo_key, hi_key, fill, color, label in zone_config:
        y_lo = [forecast[h][lo_key] for h in horizons]

        if hi_key is not None:
            y_hi = [forecast[h][hi_key] for h in horizons]
        else:
            # Bull top — add ~5 % headroom for visual
            y_hi = [forecast[h][lo_key] * 1.05 for h in horizons]

        fig.add_trace(
            go.Scatter(
                x=x_labels,
                y=y_hi,
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x_labels,
                y=y_lo,
                mode="lines+markers",
                fill="tonexty",
                fillcolor=fill,
                line=dict(color=color, width=1.5),
                marker=dict(size=8, color=color),
                name=f"{label} Target",
                hovertemplate=f"{label}: $%{{y:,.2f}}<extra></extra>",
            )
        )

    base = get_chart_layout()
    base.update(
        margin=dict(l=48, r=24, t=24, b=32),
        height=400,
        yaxis_title="Price ($)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )
    fig.update_layout(**base)

    return fig


# ------------------------------------------------------------------
# 3. Sector heatmap (treemap)
# ------------------------------------------------------------------

def create_sector_heatmap(df: pd.DataFrame) -> go.Figure:
    """Treemap grouped by sector, sized by market cap, colored by bull_score.

    Parameters
    ----------
    df : pd.DataFrame
        Columns: ticker, sector, marketCap, bull_score, last_price.
    """
    import plotly.express as px
    
    # Clean and sanitize the DataFrame to prevent any NaN values from propagating
    df = df.copy()
    
    # Standardize market cap column name if needed
    if "market_cap" in df.columns and "marketCap" not in df.columns:
        df = df.rename(columns={"market_cap": "marketCap"})

    defaults = {"sector": "Other", "ticker": "Unknown", "bull_score": 50.0,
                "marketCap": 1e9, "last_price": 0.0}
    for column, default in defaults.items():
        if column not in df:
            df[column] = default
        
    # Fill missing or invalid values for category columns
    df["sector"] = df["sector"].fillna("Other").astype(str).str.strip()
    df["sector"] = df["sector"].replace({"": "Other", "None": "Other", "nan": "Other", "N/A": "Other"})
    df["ticker"] = df["ticker"].fillna("Unknown").astype(str).str.strip()
    
    # Ensure numeric columns are strictly numeric and contain no NaNs
    df["bull_score"] = pd.to_numeric(df["bull_score"], errors="coerce").replace([float("inf"), float("-inf")], pd.NA).fillna(50.0).clip(0, 100)
    df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce").replace([float("inf"), float("-inf")], pd.NA).fillna(1e9)
    df["last_price"] = pd.to_numeric(df["last_price"], errors="coerce").replace([float("inf"), float("-inf")], pd.NA).fillna(0.0)
    
    # Keep only rows with positive market cap (required by Plotly treemap)
    df = df[df["marketCap"] > 0]
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No valid sector data available", showarrow=False)
        fig.update_layout(**get_chart_layout())
        return fig
    
    # Use px.treemap to automatically generate parent nodes (sectors)
    fig = px.treemap(
        df,
        path=["sector", "ticker"],
        values="marketCap",
        color="bull_score",
        color_continuous_scale=[
            [0.0, COLORS["bearish"]],
            [0.5, COLORS["neutral"]],
            [1.0, COLORS["bullish"]],
        ],
        range_color=[0, 100],
    )
    
    # ------------------------------------------------------------------
    # Fix NaN color values on parent (sector / root) nodes.
    # Plotly treemaps only assign the color column to leaf nodes;
    # intermediate nodes default to NaN.  We replace those with the
    # market-cap-weighted average bull_score of their children.
    # ------------------------------------------------------------------
    for trace in fig.data:
        colors  = list(trace.marker.colors)
        labels  = list(trace.labels)
        parents = list(trace.parents)
        values  = list(trace.values)

        # Build a parent -> children index for quick lookup
        from collections import defaultdict
        children_map = defaultdict(list)
        for idx, par in enumerate(parents):
            children_map[par].append(idx)

        # Bottom-up pass: resolve NaN colors as weighted avg of children
        import math

        def _resolve(i):
            c = colors[i]
            if c is not None and not pd.isna(c):
                return c
            child_indices = children_map.get(labels[i], [])
            child_scores, child_weights = [], []
            for ci in child_indices:
                sc = _resolve(ci)
                if sc is not None and not pd.isna(sc):
                    child_scores.append(sc)
                    child_weights.append(max(values[ci], 1))
            if child_scores:
                avg = sum(s * w for s, w in zip(child_scores, child_weights)) / sum(child_weights)
                colors[i] = avg
                return avg
            colors[i] = 50.0          # fallback
            return 50.0

        for i in range(len(colors)):
            _resolve(i)

        trace.marker.colors = colors
    # ------------------------------------------------------------------

    fig.update_traces(
        marker=dict(line=dict(width=1, color=COLORS["bg_primary"])),
        texttemplate="<b>%{label}</b><br>%{color:.0f}",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Bull Score: %{color:.1f}<br>"
            "Market Cap: $%{value:,.0f}<br>"
            "<extra></extra>"
        )
    )
    
    fig.update_coloraxes(
        colorbar=dict(
            title=dict(
                text="Bull Score",
                font=dict(color=COLORS["text_secondary"])
            ),
            thickness=12,
            len=0.6,
            tickfont=dict(color=COLORS["text_secondary"]),
        )
    )

    base = get_chart_layout()
    base.update(
        height=500,
        margin=dict(l=8, r=8, t=24, b=8),
    )
    fig.update_layout(**base)

    return fig


def create_risk_return_chart(df: pd.DataFrame) -> go.Figure:
    """Bubble chart exposing conviction versus historical downside risk."""
    import plotly.express as px

    clean = df.copy()
    required = {"ticker", "bull_score", "risk_score"}
    if not required.issubset(clean.columns):
        clean = pd.DataFrame(columns=["ticker", "bull_score", "risk_score", "marketCap", "sector"])
    if "market_cap" in clean and "marketCap" not in clean:
        clean = clean.rename(columns={"market_cap": "marketCap"})
    for column, default in (("bull_score", 50.0), ("risk_score", 50.0), ("marketCap", 1e9)):
        if column not in clean:
            clean[column] = default
        clean[column] = pd.to_numeric(clean[column], errors="coerce").replace([float("inf"), float("-inf")], pd.NA).fillna(default)
    clean["bull_score"] = clean["bull_score"].clip(0, 100)
    clean["risk_score"] = clean["risk_score"].clip(0, 100)
    clean.loc[clean["marketCap"] <= 0, "marketCap"] = 1e9
    if "sector" not in clean:
        clean["sector"] = "Other"
    clean["sector"] = clean["sector"].fillna("Other")

    fig = px.scatter(
        clean,
        x="risk_score",
        y="bull_score",
        size="marketCap",
        color="sector",
        hover_name="ticker",
        size_max=45,
        labels={"risk_score": "Risk Score (lower is better)", "bull_score": "Bull Score"},
        title="Risk vs. Conviction",
    )
    fig.add_vline(x=55, line_dash="dot", line_color=COLORS["warning"])
    fig.add_hline(y=60, line_dash="dot", line_color=COLORS["accent"])
    base = get_chart_layout()
    base.update(height=430, margin=dict(l=8, r=8, t=50, b=8))
    fig.update_layout(**base)
    fig.update_xaxes(range=[0, 100])
    fig.update_yaxes(range=[0, 100])
    return fig


# ------------------------------------------------------------------
# 4. Strategy radar chart
# ------------------------------------------------------------------

def create_strategy_radar(strategies: list[dict]) -> go.Figure:
    """Radar/spider chart for top strategies.

    Parameters
    ----------
    strategies : list[dict]
        Each dict has keys: name, direction_fit, volatility_fit,
        time_horizon_fit, liquidity_fit, risk_reward_fit.
        Values are 0–10 scores.
    """
    categories = [
        "Direction Fit",
        "Volatility Fit",
        "Time Horizon",
        "Liquidity",
        "Risk/Reward",
    ]
    cat_keys = [
        "direction_fit",
        "volatility_fit",
        "time_horizon_fit",
        "liquidity_fit",
        "risk_reward_fit",
    ]

    fig = go.Figure()

    # Use at most 5 strategies
    show = strategies[:5]
    opacities = [0.35, 0.28, 0.22, 0.18, 0.14]

    for idx, strat in enumerate(show):
        values = [strat.get(k, 0) for k in cat_keys]
        # Close the polygon
        values.append(values[0])
        cats = categories + [categories[0]]

        opacity = opacities[idx] if idx < len(opacities) else 0.12
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=cats,
                fill="toself",
                fillcolor=f"rgba(0,212,170,{opacity})",
                line=dict(
                    color=COLORS["accent"],
                    width=2 if idx == 0 else 1,
                ),
                name=strat["name"],
                hovertemplate="%{theta}: %{r:.1f}<extra></extra>",
            )
        )

    base = get_chart_layout()
    base.update(
        margin=dict(l=24, r=24, t=24, b=24),
        height=450,
        polar=dict(
            bgcolor=COLORS["bg_primary"],
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                gridcolor="rgba(255,255,255,0.08)",
                tickfont=dict(size=10, color=COLORS["text_muted"]),
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.08)",
                tickfont=dict(size=11, color=COLORS["text_secondary"]),
            ),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
    )
    fig.update_layout(**base)

    return fig


# ------------------------------------------------------------------
# 5. Score gauge
# ------------------------------------------------------------------

def create_score_gauge(
    score: float, label: str, max_val: float = 100
) -> go.Figure:
    """Compact gauge chart for a single score value.

    Parameters
    ----------
    score : float
        Current value.
    label : str
        Title text shown below the gauge.
    max_val : float
        Upper bound of the gauge range.
    """
    if score > 70:
        bar_color = COLORS["bullish"]
    elif score > 40:
        bar_color = COLORS["neutral"]
    else:
        bar_color = COLORS["bearish"]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            title=dict(
                text=label,
                font=dict(size=13, color=COLORS["text_secondary"]),
            ),
            number=dict(font=dict(size=28, color="#ffffff")),
            gauge=dict(
                axis=dict(
                    range=[0, max_val],
                    tickcolor=COLORS["text_muted"],
                    tickwidth=1,
                    tickfont=dict(size=9, color=COLORS["text_muted"]),
                ),
                bar=dict(color=bar_color, thickness=0.75),
                bgcolor=COLORS["bg_card"],
                borderwidth=0,
                steps=[
                    dict(range=[0, 40], color="rgba(255,71,87,0.12)"),
                    dict(range=[40, 70], color="rgba(255,165,2,0.10)"),
                    dict(range=[70, max_val], color="rgba(0,212,170,0.10)"),
                ],
                threshold=dict(
                    line=dict(color="#ffffff", width=2),
                    thickness=0.8,
                    value=score,
                ),
            ),
        )
    )

    base = get_chart_layout()
    base.update(
        height=160,
        margin=dict(l=10, r=10, t=25, b=5),
    )
    fig.update_layout(**base)

    return fig
