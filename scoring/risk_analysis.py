"""Historical downside-risk analysis for individual securities.

All return values are decimals (0.20 means 20%) unless a key ends in
``_score``.  Risk scores run from 0 (lowest observed risk) to 100 (highest).
The module is deliberately deterministic and does not fetch external data.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def risk_adjusted_conviction(
    bull_score: float, posterior_probability: float, confidence: float, risk_score: float
) -> float:
    """Blend directional evidence, Bayesian odds, data quality, and downside risk."""
    directional = 0.55 * min(max(_finite(bull_score, 50.0) / 100.0, 0.0), 1.0) + 0.45 * min(
        max(_finite(posterior_probability), 0.0), 1.0
    )
    confidence_factor = 0.5 + 0.5 * min(max(_finite(confidence, 50.0) / 100.0, 0.0), 1.0)
    risk_factor = 1.0 - 0.60 * min(max(_finite(risk_score, 50.0) / 100.0, 0.0), 1.0)
    return round(100.0 * directional * confidence_factor * risk_factor, 1)


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _history_frame(hist: pd.DataFrame | None) -> pd.DataFrame:
    if hist is None or not isinstance(hist, pd.DataFrame):
        return pd.DataFrame()
    frame = hist.copy()
    if "Date" in frame.columns:
        dates = pd.to_datetime(frame["Date"], errors="coerce", utc=True)
        frame = frame.loc[dates.notna()].copy()
        frame.index = dates[dates.notna()]
    return frame[~frame.index.duplicated(keep="last")].sort_index()


def _close_series(hist: pd.DataFrame | None) -> pd.Series:
    hist = _history_frame(hist)
    if hist is None or not isinstance(hist, pd.DataFrame) or "Close" not in hist:
        return pd.Series(dtype=float)
    close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
    return close[close > 0]


def _returns(hist: pd.DataFrame | None) -> pd.Series:
    close = _close_series(hist)
    return close.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()


def _beta(asset_returns: pd.Series, benchmark_hist: pd.DataFrame | None, fallback: Any) -> float:
    benchmark = _returns(benchmark_hist)
    if len(benchmark) >= 30:
        joined = pd.concat(
            [asset_returns.rename("asset"), benchmark.rename("market")], axis=1, sort=False
        ).dropna()
        variance = joined["market"].var(ddof=1)
        if len(joined) >= 30 and variance > 0:
            return _finite(joined["asset"].cov(joined["market"]) / variance, 1.0)
    return _finite(fallback, 1.0)


def _risk_score(metrics: dict[str, float]) -> float:
    """Weighted severity score using transparent, conservative thresholds."""
    components = {
        "volatility": min(metrics["annualized_volatility"] / 0.60, 1.0) * 100,
        "drawdown": min(abs(metrics["max_drawdown"]) / 0.60, 1.0) * 100,
        "tail": min(abs(metrics["expected_shortfall_95_daily"]) / 0.08, 1.0) * 100,
        "beta": min(max(metrics["beta"] - 0.5, 0.0) / 1.5, 1.0) * 100,
        "liquidity": (
            min(max(5_000_000 - metrics["avg_dollar_volume"], 0.0) / 5_000_000, 1.0) * 100
            if math.isfinite(metrics["avg_dollar_volume"]) else 50.0
        ),
    }
    score = (
        components["volatility"] * 0.25
        + components["drawdown"] * 0.30
        + components["tail"] * 0.20
        + components["beta"] * 0.15
        + components["liquidity"] * 0.10
    )
    return round(min(max(score, 0.0), 100.0), 1)


def analyze_risk(
    hist: pd.DataFrame | None,
    fundamentals: dict | None = None,
    benchmark_hist: pd.DataFrame | None = None,
    risk_free_rate: float = 0.04,
    risk_budget: float = 0.02,
) -> dict[str, Any]:
    """Calculate historical risk, stress tests, and a position-size guideline."""
    fundamentals = fundamentals or {}
    returns = _returns(hist)
    close = _close_series(hist)
    if len(returns) < 30:
        return {
            "available": False,
            "observations": int(len(returns)),
            "risk_score": 50.0,
            "risk_level": "Unknown",
            "warnings": ["At least 30 daily returns are required for historical risk analysis."],
        }

    annual_return = _finite((1.0 + returns).prod() ** (TRADING_DAYS / len(returns)) - 1.0)
    volatility = _finite(returns.std(ddof=1) * math.sqrt(TRADING_DAYS))
    daily_rf = risk_free_rate / TRADING_DAYS
    downside_returns = np.minimum(returns - daily_rf, 0.0)
    downside_vol = _finite(math.sqrt(float(np.mean(np.square(downside_returns)))) * math.sqrt(TRADING_DAYS))
    wealth = (1.0 + returns).cumprod()
    drawdowns = wealth / wealth.cummax() - 1.0
    max_drawdown = _finite(drawdowns.min())
    var_95 = _finite(returns.quantile(0.05))
    tail = returns[returns <= var_95]
    expected_shortfall = _finite(tail.mean(), var_95)
    excess = returns - daily_rf
    sharpe = _finite(excess.mean() / returns.std(ddof=1) * math.sqrt(TRADING_DAYS)) if volatility > 0 else 0.0
    sortino = _finite(excess.mean() * TRADING_DAYS / downside_vol) if downside_vol > 0 else 0.0
    calmar = _finite(annual_return / abs(max_drawdown)) if max_drawdown < 0 else 0.0

    normalized_hist = _history_frame(hist)
    volume = pd.to_numeric(normalized_hist.get("Volume"), errors="coerce") if "Volume" in normalized_hist else pd.Series(dtype=float)
    avg_dollar_volume = float((close * volume.reindex(close.index)).tail(20).mean()) if not volume.empty else float("nan")
    beta = _beta(returns, benchmark_hist, fundamentals.get("beta"))
    latest_price = _finite(close.iloc[-1])
    volatility_buffer_pct = max(volatility / math.sqrt(TRADING_DAYS) * 2.0, abs(expected_shortfall), 0.01)

    metrics = {
        "annualized_return": annual_return,
        "annualized_volatility": volatility,
        "downside_deviation": downside_vol,
        "max_drawdown": max_drawdown,
        "var_95_daily": var_95,
        "expected_shortfall_95_daily": expected_shortfall,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "beta": beta,
        "avg_dollar_volume": avg_dollar_volume,
    }
    score = _risk_score(metrics)
    level = "Low" if score < 30 else "Moderate" if score < 55 else "High" if score < 75 else "Very High"
    warnings = []
    if abs(max_drawdown) >= 0.30:
        warnings.append(f"Historical maximum drawdown reached {abs(max_drawdown):.1%}.")
    if volatility >= 0.45:
        warnings.append(f"Annualized volatility is elevated at {volatility:.1%}.")
    if expected_shortfall <= -0.05:
        warnings.append(f"Worst 5% of sessions averaged a {abs(expected_shortfall):.1%} loss.")
    if not math.isfinite(avg_dollar_volume):
        warnings.append("Dollar-volume liquidity could not be measured from the available history.")
    elif avg_dollar_volume < 5_000_000:
        warnings.append("Low dollar volume can increase slippage and exit risk.")
    if beta >= 1.5:
        warnings.append(f"High beta ({beta:.2f}) implies amplified market sensitivity.")

    return {
        "available": True,
        "observations": int(len(returns)),
        "risk_score": score,
        "risk_level": level,
        **{key: round(value, 6) for key, value in metrics.items()},
        "stress_tests": {
            "market_correction_10pct": round(-0.10 * beta, 6),
            "market_bear_20pct": round(-0.20 * beta, 6),
            "volatility_shock_2sigma_daily": round(-2.0 * volatility / math.sqrt(TRADING_DAYS), 6),
        },
        "position_sizing": {
            "risk_budget_pct": risk_budget,
            "volatility_buffer_pct": round(volatility_buffer_pct, 6),
            "max_portfolio_weight": round(min(risk_budget / volatility_buffer_pct, 0.25), 6),
            "shares_per_100k": int((100_000 * min(risk_budget / volatility_buffer_pct, 0.25)) / latest_price) if latest_price else 0,
        },
        "warnings": warnings,
    }
