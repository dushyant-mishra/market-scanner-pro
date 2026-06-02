"""
Market Scanner V2 — Reusable Streamlit Components
Render cards, tables, and dashboard widgets using custom HTML + CSS classes.
"""

from __future__ import annotations

import html as html_mod
import textwrap
from typing import Any

import streamlit as st
import numpy as np

from config import COLORS, SCORE_THRESHOLDS


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _esc(text: Any) -> str:
    """HTML-escape arbitrary text."""
    return html_mod.escape(str(text))


def _score_badge_class(score: float, invert: bool = False) -> str:
    """Return the CSS class for a score badge.

    Parameters
    ----------
    score : float
    invert : bool
        If True, low values are green and high values are red (for risk).
    """
    if invert:
        if score < SCORE_THRESHOLDS["medium"]:
            return "score-high"
        elif score < SCORE_THRESHOLDS["high"]:
            return "score-medium"
        else:
            return "score-low"
    else:
        if score >= SCORE_THRESHOLDS["high"]:
            return "score-high"
        elif score >= SCORE_THRESHOLDS["medium"]:
            return "score-medium"
        else:
            return "score-low"


def _format_pct(value: float) -> str:
    """Format a percentage with sign and 2 decimals."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def _delta_class(value: float) -> str:
    return "delta-positive" if value >= 0 else "delta-negative"


def _bar_color(score: float) -> str:
    """Return a CSS color string for a progress bar fill."""
    if score >= SCORE_THRESHOLDS["high"]:
        return COLORS["bullish"]
    elif score >= SCORE_THRESHOLDS["medium"]:
        return COLORS["neutral"]
    else:
        return COLORS["bearish"]


def _score_cell_color(value: float, max_val: float = 10) -> str:
    """Return inline color style for a table cell based on score."""
    ratio = value / max_val if max_val else 0
    if ratio >= 0.7:
        return COLORS["bullish"]
    elif ratio >= 0.4:
        return COLORS["neutral"]
    else:
        return COLORS["bearish"]


def _render_html(html_str: str) -> None:
    """Clean the HTML string by stripping each line to prevent Streamlit's
    Markdown parser from misinterpreting indented lines as code blocks,
    then render via st.markdown.
    """
    clean_lines = [line.strip() for line in html_str.splitlines() if line.strip()]
    st.markdown(" ".join(clean_lines), unsafe_allow_html=True)


# ------------------------------------------------------------------
# 1. Header
# ------------------------------------------------------------------

def render_header() -> None:
    """Render the application header block."""
    _render_html(
        """
        <div class="app-header">
            <h1>Market Scanner</h1>
            <p class="app-subtitle">AI-Powered Stock &amp; Options Research Engine</p>
            <p class="app-disclaimer">
                Research tool only — not financial advice. Paper trade and verify all results.
            </p>
        </div>
        """
    )


# ------------------------------------------------------------------
# 2. Score card
# ------------------------------------------------------------------

def render_score_card(
    ticker: str,
    scores: dict,
    price: float,
    change_pct: float,
) -> None:
    """Render a single stock score card.

    Parameters
    ----------
    ticker : str
    scores : dict
        Keys: bull_score, bear_score, risk_score, confidence, reasons, warnings.
    price : float
    change_pct : float
        Percentage change for the day.
    """
    bull = scores.get("bull_score", 0)
    risk = scores.get("risk_score", 0)
    confidence = scores.get("confidence", 0)
    reasons: list[str] = scores.get("reasons", [])[:3]
    bull_cls = _score_badge_class(bull)
    risk_cls = _score_badge_class(risk, invert=True)
    delta_cls = _delta_class(change_pct)
    delta_str = _format_pct(change_pct)

    reasons_html = ""
    if reasons:
        items = "".join(f"<li>{_esc(r)}</li>" for r in reasons)
        reasons_html = f'<ul class="reason-list">{items}</ul>'

    card_html = f"""
    <div class="metric-card">
        <div class="ticker-name">{_esc(ticker)}</div>
        <div class="value">${price:,.2f}
            <span class="{delta_cls}" style="font-size:0.9rem; margin-left:6px;">{delta_str}</span>
        </div>
        <div class="score-row">
            <span class="score-badge {bull_cls}">Bull {bull:.0f}</span>
            <span class="score-badge {risk_cls}">Risk {risk:.0f}</span>
        </div>
        <div style="margin-top:0.3rem; display:flex; align-items:center; gap:6px;">
            <span class="text-secondary" style="font-size:0.8rem;">
                Confidence:
            </span>
            <span style="color:#fff; font-size:0.85rem; font-weight:600;">
                {confidence:.0f}%
            </span>
            <div style="flex-grow:1; max-width:80px; height:6px; background:rgba(45,55,72,0.5); border-radius:3px; overflow:hidden;">
                <div class="confidence-bar" style="width:{confidence}%; height:100%;"></div>
            </div>
        </div>
        {reasons_html}
    </div>
    """
    _render_html(card_html)


# ------------------------------------------------------------------
# 3. Top-5 row
# ------------------------------------------------------------------

def render_top5_cards(df, category: str) -> None:
    """Render five score cards in a horizontal row.

    Parameters
    ----------
    df : pd.DataFrame
        Columns: ticker, last_price, bull_score, risk_score, confidence, reason.
    category : str
        Title above the row (e.g. "🟢 Top 5 Bullish").
    """
    st.subheader(category)
    cols = st.columns(5)
    rows = df.head(5).to_dict("records")

    for idx, (col, row) in enumerate(zip(cols, rows)):
        extra_cls = "top-stock" if idx == 0 else ""
        bull = row.get("bull_score", 0)
        risk = row.get("risk_score", 0)
        conf = row.get("confidence", 0)
        price = row.get("last_price", 0)
        reason = row.get("reason", "")
        bull_cls = _score_badge_class(bull)
        risk_cls = _score_badge_class(risk, invert=True)

        reason_html = ""
        if reason:
            reason_html = f'<div class="text-secondary" style="font-size:0.72rem; margin-top:0.4rem;">{_esc(reason)}</div>'

        card = f"""
        <div class="metric-card top5-card {extra_cls}">
            <div class="ticker-name">{_esc(row.get("ticker", ""))}</div>
            <div class="value" style="font-size:1.3rem;">${price:,.2f}</div>
            <div class="score-row">
                <span class="score-badge {bull_cls}">Bull {bull:.0f}</span>
                <span class="score-badge {risk_cls}">Risk {risk:.0f}</span>
            </div>
            <div class="text-secondary" style="font-size:0.72rem; margin-top:0.3rem;">
                Confidence: {conf:.0f}%
            </div>
            {reason_html}
        </div>
        """
        with col:
            _render_html(card)

# ------------------------------------------------------------------
# 3b. Top-5 Upside row
# ------------------------------------------------------------------

def render_top5_upside_cards(df) -> None:
    """Render five high upside cards in a horizontal row.

    Parameters
    ----------
    df : pd.DataFrame
        Columns: ticker, last_price, bayesian_posterior, bull_pct_90, quality_score, reason.
    """
    st.subheader("Top 5 Highest Upside (Bayesian Conviction)")
    st.markdown("<small style='color:#8892a0;'>Sorted by mathematically modeled 90-day upside and Bayesian probability. *Not a guarantee of future returns.*</small>", unsafe_allow_html=True)
    cols = st.columns(5)
    
    # Sort by bull_pct_90 and bayesian_posterior
    sorted_df = df.sort_values(by=["bull_pct_90", "bayesian_posterior"], ascending=[False, False])
    rows = sorted_df.head(5).to_dict("records")

    for idx, (col, row) in enumerate(zip(cols, rows)):
        extra_cls = "top-stock" if idx == 0 else ""
        price = row.get("last_price", 0)
        bayesian = row.get("bayesian_posterior", 0.0)
        upside = row.get("bull_pct_90", 0.0)
        quality = row.get("quality_score", 0)
        
        bayesian_cls = _score_badge_class(bayesian * 100)

        card = f"""
        <div class="metric-card top5-card {extra_cls}" style="word-break: break-word; white-space: normal;">
            <div class="ticker-name">{_esc(row.get("ticker", ""))}</div>
            <div class="value" style="font-size:1.3rem;">${price:,.2f}</div>
            <div class="score-row">
                <span class="score-badge {bayesian_cls}">Conviction {bayesian*100:.0f}%</span>
            </div>
            <div class="score-row" style="margin-top:2px;">
                <span class="delta-positive" style="font-size: 0.9rem; font-weight:700;">Target: +{upside*100:.1f}%</span>
            </div>
            <div class="text-secondary" style="font-size:0.72rem; margin-top:0.3rem;">
                Quality Score: {quality}%
            </div>
        </div>
        """
        with col:
            _render_html(card)


# ------------------------------------------------------------------
# 4. Strategy table
# ------------------------------------------------------------------

def render_strategy_table(strategies: list[dict]) -> None:
    """Render options strategy ranking as a styled HTML table.

    Parameters
    ----------
    strategies : list[dict]
        Keys per dict: name, score (0-10), direction_fit, volatility_fit,
        risk_reward_fit, risk_warning.
    """
    header = textwrap.dedent(
        """\
        <div class="table-container" style="overflow-x: auto;">
        <table class="strategy-table" style="width: 100%; min-width: 600px;">
            <thead>
                <tr>
                    <th style="width: 10%;">Rank</th>
                    <th style="width: 30%;">Strategy</th>
                    <th style="width: 15%;">Score</th>
                    <th style="width: 45%; min-width: 250px;">Risk Warning</th>
                </tr>
            </thead>
            <tbody>
        """
    )
    rows_html = ""
    for rank, s in enumerate(strategies, start=1):
        score = s.get("score", 0)
        row_cls = "highlight-row" if rank == 1 else ""
        score_color = _score_cell_color(score)
        warn = _esc(s.get("risk_warning", "—"))

        rows_html += textwrap.dedent(
            f"""\
            <tr class="{row_cls}">
                <td style="font-weight:700;">{rank}</td>
                <td>{_esc(s.get("name", ""))}</td>
                <td style="color:{score_color}; font-weight:700;">{score:.1f}</td>
                <td style="color:{COLORS['warning']}; font-size:0.82rem; word-wrap: break-word; padding-right: 15px;">{warn}</td>
            </tr>
            """
        )

    footer = "</tbody></table></div>"
    _render_html(header + rows_html + footer)


# ------------------------------------------------------------------
# 5. Forecast card
# ------------------------------------------------------------------

def render_forecast_card(forecast: dict) -> None:
    """Render price forecast as formatted HTML.

    Parameters
    ----------
    forecast : dict
        Top-level keys: ``"30"``, ``"90"`` (horizon days).
        Each value is a dict with ``bear``, ``base``, ``bull`` price targets
        and optionally ``bear_pct``, ``base_pct``, ``bull_pct``,
        ``prob_above``, ``confidence``, ``regime``.
    """
    horizons = sorted(forecast.keys(), key=lambda h: int(h))
    cols = st.columns(len(horizons))

    for col, h in zip(cols, horizons):
        data = forecast[h]
        bear = data.get("bear", 0)
        base = data.get("base", 0)
        bull = data.get("bull", 0)
        bear_pct = data.get("bear_pct", 0)
        base_pct = data.get("base_pct", 0)
        bull_pct = data.get("bull_pct", 0)
        prob_above = data.get("prob_above", 50)
        confidence = data.get("confidence", 0)
        regime = _esc(data.get("regime", "—"))

        card_html = f"""
        <div class="metric-card forecast-card" style="display:flex; flex-direction:column; gap:8px;">
            <div class="horizon-title" style="margin-bottom:4px;">{h}-Day Forecast</div>

            <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:4px;">
                <span class="forecast-label text-red" style="min-width:60px;">Bear</span>
                <span style="text-align:right;">
                    <span class="forecast-value">${bear:,.2f}</span>
                    <span class="forecast-delta text-red" style="margin-left:4px;">{_format_pct(bear_pct)}</span>
                </span>
            </div>

            <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:4px;">
                <span class="forecast-label text-yellow" style="min-width:60px;">Base</span>
                <span style="text-align:right;">
                    <span class="forecast-value">${base:,.2f}</span>
                    <span class="forecast-delta text-yellow" style="margin-left:4px;">{_format_pct(base_pct)}</span>
                </span>
            </div>

            <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:4px;">
                <span class="forecast-label text-green" style="min-width:60px;">Bull</span>
                <span style="text-align:right;">
                    <span class="forecast-value">${bull:,.2f}</span>
                    <span class="forecast-delta text-green" style="margin-left:4px;">{_format_pct(bull_pct)}</span>
                </span>
            </div>

            <div style="margin-top:0.7rem;">
                <span class="text-secondary" style="font-size:0.78rem;">
                    Prob. above current:
                </span>
                <span style="color:#fff; font-weight:600; font-size:0.85rem;">
                    {prob_above:.0f}%
                </span>
                <div style="width:100%; height:6px; background:rgba(45,55,72,0.5);
                            border-radius:3px; margin-top:4px; overflow:hidden;">
                    <div style="width:{prob_above}%; height:100%;
                                background:linear-gradient(90deg, {COLORS['bearish']}, {COLORS['neutral']}, {COLORS['bullish']});
                                border-radius:3px;">
                    </div>
                </div>
            </div>

            <div style="margin-top:0.5rem; font-size:0.75rem;" class="text-secondary">
                Confidence: <span class="fw-bold" style="color:#fff;">{confidence:.0f}%</span>
                &nbsp;·&nbsp; Regime: <span style="color:#fff;">{regime}</span>
            </div>
        </div>
        """
        with col:
            _render_html(card_html)


# ------------------------------------------------------------------
# 6. Category breakdown bars
# ------------------------------------------------------------------

def render_category_breakdown(category_scores: dict) -> None:
    """Render scoring category breakdown as horizontal bars.

    Parameters
    ----------
    category_scores : dict
        Keys: trend, momentum, options_flow, leaps, fundamentals, sector, volume.
        Values: 0–100 scores.
    """
    label_map = {
        "trend": "Trend",
        "momentum": "Momentum",
        "options_flow": "Options Flow",
        "leaps": "LEAPS",
        "fundamentals": "Fundamentals",
        "sector": "Sector",
        "volume": "Volume",
    }

    bars_html = ""
    for key, label in label_map.items():
        score = category_scores.get(key, 0)
        color = _bar_color(score)
        bars_html += textwrap.dedent(
            f"""\
            <div class="category-bar-container">
                <div class="category-bar-label">
                    <span>{label}</span>
                    <span style="color:#fff; font-weight:600;">{score:.0f}</span>
                </div>
                <div class="category-bar-track">
                    <div class="category-bar-fill"
                         style="width:{score}%; background:{color};">
                    </div>
                </div>
            </div>
            """
        )

    _render_html(bars_html)


# ------------------------------------------------------------------
# 7. Risk warnings
# ------------------------------------------------------------------

def render_risk_warnings(warnings: list[str]) -> None:
    """Render risk warnings as styled amber alert boxes.

    Parameters
    ----------
    warnings : list[str]
        Warning messages to display.
    """
    if not warnings:
        return

    html_parts = []
    for w in warnings:
        html_parts.append(
            f'<div class="risk-warning">Warning: {_esc(w)}</div>'
        )

    _render_html("\n".join(html_parts))


# ------------------------------------------------------------------
# 8. Causal & Fundamental Display
# ------------------------------------------------------------------

def render_fundamental_screen_table(screen_results: dict[str, Any]) -> None:
    """Render the 18 criteria Pass/Fail fundamental screen table."""
    quality_score = screen_results.get("quality_score", 0)
    score_cls = _score_badge_class(quality_score)
    
    header = textwrap.dedent(
        f"""
        <div style="margin-bottom: 1rem;">
            <h3>Fidelity Quality Score: <span class="score-badge {score_cls}">{quality_score}%</span></h3>
        </div>
        <div class="table-container">
        <table class="strategy-table" style="width: 100%;">
            <thead>
                <tr>
                    <th style="width: 25%;">Category</th>
                    <th style="width: 45%;">Criterion</th>
                    <th style="width: 15%;">Value</th>
                    <th style="width: 15%;">Result</th>
                </tr>
            </thead>
            <tbody>
        """
    )

    def row(cat: str, crit: str, val_key: str, pass_key: str, fmt: str = "{}") -> str:
        passed = screen_results.get(pass_key, False)
        icon = "Pass" if passed else "Fail"
        row_class = "delta-positive" if passed else "delta-negative"
        val = screen_results.get(val_key)
        
        # Format the value
        if val is None or pd.isna(val):
            val_str = "N/A"
        else:
            try:
                val_str = fmt.format(val)
            except Exception:
                val_str = str(val)

        return textwrap.dedent(
            f"""
            <tr>
                <td style="font-weight:600; color:#A0AEC0;">{cat}</td>
                <td>{crit}</td>
                <td>{val_str}</td>
                <td class="{row_class}">{icon} {"Pass" if passed else "Fail"}</td>
            </tr>
            """
        )
    
    import pandas as pd # Ensure pandas is available for pd.isna
    
    rows = [
        row("Liquidity & Size", "Market Cap > $2B", "market_cap", "market_cap_pass", "${:,.0f}"),
        row("Liquidity & Size", "Avg Daily Volume > 500k", "avg_vol", "avg_vol_pass", "{:,.0f}"),
        row("Profitability", "ROE > 15%", "roe", "roe_pass", "{:.1%}"),
        row("Profitability", "ROIC > 12%", "roic", "roic_pass", "{:.1%}"),
        row("Profitability", "Positive Op Margin & Sales Growth", "op_margin", "op_margin_pass", "{:.1%}"),
        row("Growth", "EPS Growth > 10%", "eps_growth", "eps_growth_pass", "{:.1%}"),
        row("Growth", "Sales Growth (T12M) > 10%", "sales_growth", "sales_growth_pass", "{:.1%}"),
        row("Growth", "Forward EPS > Trailing EPS", "fwd_eps", "fwd_eps_growth_pass", "${:.2f}"),
        row("Valuation", "Forward P/E < 25", "fwd_pe", "fwd_pe_pass", "{:.1f}"),
        row("Valuation", "PEG Ratio (0.0 to 1.5)", "peg", "peg_pass", "{:.2f}"),
        row("Valuation", "Price-to-FCF < 20", "p_fcf", "p_fcf_pass", "{:.1f}"),
        row("Financial Health", "Debt-to-Equity < 1.0", "dte", "dte_pass", "{:.2f}"),
        row("Financial Health", "Current Ratio > 1.5", "cr", "cr_pass", "{:.2f}"),
        row("Financial Health", "Interest Coverage > 4.0", "icr", "icr_pass", "{:.1f}"),
        row("Momentum", "Price > 200 SMA", "close", "ma200_pass", "${:.2f}"),
        row("Momentum", "Price within 15% of 52W High", "close", "high52_pass", "${:.2f}"),
        row("Momentum", "RSI between 40 and 60", "rsi", "rsi_pass", "{:.1f}"),
    ]
    
    footer = "</tbody></table></div>"
    _render_html(header + "".join(rows) + footer)

def render_causal_analysis_card(causal_results: dict[str, Any], bayesian_results: dict[str, Any] = None, patterns: dict[str, Any] = None) -> None:
    """Render the causal modeling, bayesian, and pattern insights."""
    
    insights = causal_results.get("insights", [])
    
    if not insights and not bayesian_results:
        _render_html('<div class="risk-warning">No causal or bayesian insights available.</div>')
        return

    insights_html = "".join([f"<li>{_esc(msg)}</li>" for msg in insights])
    
    scm = causal_results.get("scm_path", {})
    tme = scm.get("total_market_effect", np.nan)
    d = scm.get("d_vol_to_stock", np.nan)
    
    import pandas as pd
    
    scm_html = ""
    if pd.notna(tme):
        scm_html = textwrap.dedent(f"""
            <div style="margin-top: 1rem; padding: 1rem; background: rgba(255,255,255,0.05); border-radius: 8px;">
                <h4 style="margin-top: 0; color:#e0e6ed;">Structural Path Analysis</h4>
                <div class="score-row">
                    <span class="score-badge {'score-high' if tme > 1.0 else 'score-medium'}">Total Market Beta: {tme:.2f}</span>
                    <span class="score-badge {'score-high' if d > 0 else 'score-low'}">Volume Direct Effect: {d:.4f}</span>
                </div>
            </div>
        """)
        
    bayesian_html = ""
    if bayesian_results:
        prob = bayesian_results.get("posterior_prob", 0.0)
        evidence = bayesian_results.get("evidence_log", [])
        evidence_list = "".join([f"<li>{_esc(msg)}</li>" for msg in evidence])
        
        bayesian_html = textwrap.dedent(f"""
            <div style="margin-top: 1rem; padding: 1rem; background: rgba(0,212,170,0.05); border: 1px solid rgba(0,212,170,0.2); border-radius: 8px;">
                <h4 style="margin-top: 0; color:#00d4aa;">Bayesian Inference Engine</h4>
                <div style="font-size: 2rem; font-weight: 700; color:#fff; margin-bottom: 0.5rem;">
                    {prob*100:.0f}% <span style="font-size:0.9rem; color:#8892a0; font-weight:400;">Conviction Probability</span>
                </div>
                <div class="text-secondary" style="font-size: 0.8rem; margin-bottom: 0.5rem;">Evidence Log:</div>
                <ul class="reason-list" style="margin-bottom: 0; font-family: monospace;">
                    {evidence_list}
                </ul>
            </div>
        """)
        
    patterns_html = ""
    if patterns:
        active_patterns = []
        if patterns.get("trendline_breakout"): active_patterns.append("Trendline Breakout")
        if patterns.get("double_bottom"): active_patterns.append("Double Bottom")
        if patterns.get("flag_breakout"): active_patterns.append("Bull Flag")
        if patterns.get("gap") == "gap_up": active_patterns.append("Breakaway Gap Up")
        if patterns.get("high_volume_event"): active_patterns.append("High Volume Event")
        
        if active_patterns:
            p_list = "".join([f"<span class='score-badge score-medium' style='margin-right: 4px; margin-bottom: 4px;'>{p}</span>" for p in active_patterns])
            patterns_html = f"""
                <div style="margin-top: 1rem;">
                    <div class="text-secondary" style="font-size: 0.8rem; margin-bottom: 0.5rem;">Edwards & Magee Patterns Detected:</div>
                    <div style="display:flex; flex-wrap:wrap;">{p_list}</div>
                </div>
            """

    card_html = textwrap.dedent(f"""
        <div class="metric-card" style="margin-top: 1rem;">
            <h3 style="margin-top:0;">Causal Discovery Insights</h3>
            <ul class="reason-list" style="margin-bottom: 0;">
                {insights_html}
            </ul>
            {scm_html}
            {bayesian_html}
            {patterns_html}
        </div>
    """)
    _render_html(card_html)
