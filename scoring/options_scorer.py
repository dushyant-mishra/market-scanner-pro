"""
Options Strategy Scorer — evaluate and rank option strategies for a stock.

Each of the 10 strategies from config.STRATEGIES is scored on multiple
dimensions (direction fit, volatility fit, time horizon, liquidity,
risk/reward) producing a composite suitability score.
"""

from __future__ import annotations

import logging
from debate.engine import debate_strategy
from typing import Dict, List

from config import STRATEGIES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _safe(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return f if f == f else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Strategy-specific evaluation
# ---------------------------------------------------------------------------

def evaluate_strategy(
    strategy: dict,
    stock_scores: dict,
    options_data: dict,
    technical: dict,
    price_features: dict,
) -> Dict[str, object]:
    """Evaluate how suitable a specific strategy is for a given stock.

    Parameters
    ----------
    strategy : dict
        One item from ``config.STRATEGIES``.
    stock_scores : dict
        Output of ``stock_scorer.score_stock()``.
    options_data : dict
        Raw options data.
    technical : dict
        Output of ``calculate_all_indicators()``.
    price_features : dict
        Price / MA / volume features.

    Returns
    -------
    dict
        Evaluation across multiple fit dimensions.
    """
    name = strategy.get("name", "Unknown")
    direction = strategy.get("direction", "neutral")
    min_dte = strategy.get("min_dte", 30)

    # Safe accessors
    bull = _safe(stock_scores.get("bull_score")) if stock_scores else 50
    bear = _safe(stock_scores.get("bear_score")) if stock_scores else 50
    risk = _safe(stock_scores.get("risk_score")) if stock_scores else 50

    avg_call_iv = _safe(options_data.get("avg_call_iv")) if options_data else 0
    avg_put_iv = _safe(options_data.get("avg_put_iv")) if options_data else 0
    avg_iv = ((avg_call_iv + avg_put_iv) / 2) if (avg_call_iv > 0 and avg_put_iv > 0) else max(avg_call_iv, avg_put_iv)

    total_call_vol = _safe(options_data.get("total_call_volume")) if options_data else 0
    total_put_vol = _safe(options_data.get("total_put_volume")) if options_data else 0
    total_oi = (_safe(options_data.get("total_call_oi")) + _safe(options_data.get("total_put_oi"))) if options_data else 0

    rsi = _safe(technical.get("rsi")) if technical else 50
    atr_pct = _safe(technical.get("atr_pct")) if technical else 2.0

    # ------------------------------------------------------------------
    # Dimension scorers (each 0-10)
    # ------------------------------------------------------------------

    direction_fit = _score_direction_fit(name, direction, bull, bear)
    volatility_fit = _score_volatility_fit(name, avg_iv, atr_pct)
    time_horizon_fit = _score_time_horizon_fit(name, min_dte)
    liquidity_fit = _score_liquidity_fit(total_call_vol + total_put_vol, total_oi)
    risk_reward_fit = _score_risk_reward_fit(name, bull, bear, risk, rsi)

    # Event risk penalty (0 - 5)
    event_risk_penalty = 0.0
    if avg_iv > 0.70:
        event_risk_penalty += 2.0
    if atr_pct > 4.0:
        event_risk_penalty += 1.5
    if risk > 70:
        event_risk_penalty += 1.5
    event_risk_penalty = _clamp(event_risk_penalty, 0, 5)

    # Composite suitability (weighted average minus penalty)
    suitability = (
        direction_fit * 0.30
        + volatility_fit * 0.20
        + time_horizon_fit * 0.10
        + liquidity_fit * 0.15
        + risk_reward_fit * 0.25
    ) - event_risk_penalty * 0.5  # penalty scales down

    suitability = _clamp(suitability, 0, 10)

    # DTE recommendation & risk warning
    dte_range = _recommend_dte(name, min_dte)
    risk_warning = _risk_warning(name, avg_iv, risk, atr_pct)

    return {
        "name": name,
        "suitability_score": round(suitability, 1),
        "direction_fit": round(direction_fit, 1),
        "volatility_fit": round(volatility_fit, 1),
        "time_horizon_fit": round(time_horizon_fit, 1),
        "liquidity_fit": round(liquidity_fit, 1),
        "risk_reward_fit": round(risk_reward_fit, 1),
        "event_risk_penalty": round(event_risk_penalty, 1),
        "description": strategy.get("description", ""),
        "risk_warning": risk_warning,
        "recommended_dte_range": dte_range,
        "sortino": 0.0,
        "cvar": 0.0,
    }


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------

def _score_direction_fit(name: str, direction: str, bull: float, bear: float) -> float:
    """How well does the stock's outlook match the strategy direction?"""
    score = 5.0  # neutral baseline

    if direction == "bullish":
        if bull >= 70:
            score = 9.0
        elif bull >= 60:
            score = 7.5
        elif bull >= 50:
            score = 5.5
        elif bull >= 40:
            score = 3.0
        else:
            score = 1.5

    elif direction == "bearish":
        if bear >= 70:
            score = 9.0
        elif bear >= 60:
            score = 7.5
        elif bear >= 50:
            score = 5.5
        elif bear >= 40:
            score = 3.0
        else:
            score = 1.5

    elif "neutral" in direction:
        # Neutral strategies like when bull and bear are close to 50
        divergence = abs(bull - 50)
        if divergence < 10:
            score = 8.5  # very range-bound
        elif divergence < 20:
            score = 6.5
        elif divergence < 30:
            score = 4.0
        else:
            score = 2.0

        # neutral_bullish gets a bump if slightly bullish
        if direction == "neutral_bullish" and 50 <= bull <= 65:
            score = min(score + 1.5, 10)

    elif direction == "protective":
        # Collar: good when you own shares and are worried
        if bear >= 55:
            score = 8.0  # want protection
        elif bear >= 45:
            score = 6.0
        else:
            score = 3.5  # market is fine, less need

    return _clamp(score, 0, 10)


def _score_volatility_fit(name: str, avg_iv: float, atr_pct: float) -> float:
    """How well does the volatility environment suit this strategy?"""
    score = 5.0

    # Strategies that WANT high IV (selling premium)
    high_iv_strategies = {"Covered Call", "Cash-Secured Put", "Iron Condor"}
    # Strategies that WANT low IV (buying premium)
    low_iv_strategies = {"LEAPS Call", "LEAPS Put", "Call Debit Spread", "Put Debit Spread"}
    # Neutral on IV
    neutral_iv_strategies = {"Calendar Spread", "Double Calendar", "Collar"}

    if name in high_iv_strategies:
        if avg_iv > 0.50:
            score = 9.0
        elif avg_iv > 0.35:
            score = 7.5
        elif avg_iv > 0.20:
            score = 5.0
        else:
            score = 3.0

    elif name in low_iv_strategies:
        if avg_iv < 0.25:
            score = 8.5
        elif avg_iv < 0.35:
            score = 7.0
        elif avg_iv < 0.50:
            score = 5.0
        elif avg_iv < 0.70:
            score = 3.0
        else:
            score = 1.5  # extremely expensive

    elif name in neutral_iv_strategies:
        # Calendar spreads benefit from IV term structure in contango
        if 0.20 < avg_iv < 0.50:
            score = 7.5
        elif avg_iv <= 0.20:
            score = 5.0
        else:
            score = 4.0

    # ATR bonus/penalty
    if atr_pct > 5.0 and name in {"Iron Condor", "Double Calendar"}:
        score -= 2.0  # high realized vol hurts range-bound strategies

    return _clamp(score, 0, 10)


def _score_time_horizon_fit(name: str, min_dte: int) -> float:
    """Score based on strategy time horizon characteristics.

    LEAPS need long dated; short-term strategies are always available.
    """
    if min_dte >= 180:
        return 7.0  # LEAPS are specialized but valid when conditions fit
    else:
        return 7.5  # shorter-term strategies have more flexibility


def _score_liquidity_fit(total_volume: float, total_oi: float) -> float:
    """Score based on options liquidity."""
    score = 5.0

    if total_volume >= 10_000 and total_oi >= 50_000:
        score = 9.5
    elif total_volume >= 5_000 and total_oi >= 20_000:
        score = 8.0
    elif total_volume >= 1_000 and total_oi >= 5_000:
        score = 6.5
    elif total_volume >= 500:
        score = 5.0
    elif total_volume > 0:
        score = 3.0
    else:
        score = 1.0  # no liquidity data at all

    return _clamp(score, 0, 10)


def _score_risk_reward_fit(
    name: str,
    bull: float,
    bear: float,
    risk: float,
    rsi: float,
) -> float:
    """Strategy-specific risk/reward scoring."""
    score = 5.0

    if name == "LEAPS Call":
        if bull > 60 and risk < 60:
            score = 8.5
        elif bull > 55:
            score = 6.5
        else:
            score = 3.5

    elif name == "LEAPS Put":
        if bear > 60 and risk < 60:
            score = 8.5
        elif bear > 55:
            score = 6.5
        else:
            score = 3.5

    elif name == "Call Debit Spread":
        # Good for mildly bullish — limited risk
        if 55 <= bull <= 75:
            score = 8.0
        elif bull > 50:
            score = 6.0
        else:
            score = 3.0

    elif name == "Put Debit Spread":
        if 55 <= bear <= 75:
            score = 8.0
        elif bear > 50:
            score = 6.0
        else:
            score = 3.0

    elif name == "Covered Call":
        # Want mildly bullish, collect premium
        if 45 <= bull <= 65 and rsi < 70:
            score = 8.0
        elif bull >= 40:
            score = 6.0
        else:
            score = 3.5

    elif name == "Cash-Secured Put":
        # Want to enter or collect — mildly bullish
        if 50 <= bull <= 70 and rsi < 70:
            score = 8.0
        elif bull >= 45:
            score = 6.0
        else:
            score = 3.0

    elif name == "Calendar Spread":
        # Neutral, want time decay
        if abs(bull - 50) < 15:
            score = 8.0
        elif abs(bull - 50) < 25:
            score = 5.5
        else:
            score = 3.0

    elif name == "Double Calendar":
        # Range-bound
        if abs(bull - 50) < 12:
            score = 8.5
        elif abs(bull - 50) < 20:
            score = 6.0
        else:
            score = 3.0

    elif name == "Iron Condor":
        # Neutral, high IV, range-bound
        if abs(bull - 50) < 15 and risk < 55:
            score = 8.5
        elif abs(bull - 50) < 20:
            score = 6.0
        else:
            score = 2.5

    elif name == "Collar":
        # Protective — good when holding and worried
        if bear > 50 and risk > 50:
            score = 8.0
        elif bear > 45:
            score = 5.5
        else:
            score = 3.5

    return _clamp(score, 0, 10)


# ---------------------------------------------------------------------------
# DTE recommendation
# ---------------------------------------------------------------------------

def _recommend_dte(name: str, min_dte: int) -> str:
    dte_map = {
        "LEAPS Call": "180+ DTE (9-18 months ideal)",
        "LEAPS Put": "180+ DTE (9-18 months ideal)",
        "Call Debit Spread": "30-60 DTE",
        "Put Debit Spread": "30-60 DTE",
        "Covered Call": "30-45 DTE",
        "Cash-Secured Put": "30-45 DTE",
        "Calendar Spread": "Front: 30 DTE / Back: 60+ DTE",
        "Double Calendar": "Front: 30 DTE / Back: 60+ DTE",
        "Iron Condor": "30-45 DTE",
        "Collar": "60-90 DTE",
    }
    return dte_map.get(name, f"{min_dte}+ DTE")


# ---------------------------------------------------------------------------
# Risk warning
# ---------------------------------------------------------------------------

def _risk_warning(name: str, avg_iv: float, risk: float, atr_pct: float) -> str:
    warnings: List[str] = []

    if avg_iv > 0.60:
        warnings.append("IV is elevated — premium cost/decay may be significant")
    if risk > 70:
        warnings.append("High overall risk score — consider smaller position size")
    if atr_pct > 4.0:
        warnings.append("High realized volatility — wider strikes recommended")

    if name in {"Iron Condor", "Double Calendar"} and atr_pct > 3.5:
        warnings.append("Range-bound strategy in a volatile market — risk of breach")

    if name in {"LEAPS Call", "LEAPS Put"} and avg_iv > 0.50:
        warnings.append("Buying expensive long-dated options — IV crush risk")

    return "; ".join(warnings) if warnings else "Standard risk applies"


# ---------------------------------------------------------------------------
# Rank all strategies
# ---------------------------------------------------------------------------

def rank_strategies(
    stock_scores: dict,
    options_data: dict,
    technical: dict,
    price_features: dict,
) -> List[Dict[str, object]]:
    """Evaluate all 10 strategies and return sorted by suitability descending.

    Parameters
    ----------
    stock_scores, options_data, technical, price_features :
        Same as ``evaluate_strategy`` inputs.

    Returns
    -------
    list[dict]
        Sorted strategy evaluations, best first.
    """
    stock_scores = stock_scores or {}
    options_data = options_data or {}
    technical = technical or {}
    price_features = price_features or {}

    results: List[Dict[str, object]] = []

    for strategy in STRATEGIES:
        try:
            evaluation = debate_strategy(
                strategy, stock_scores, options_data, technical, price_features,
            )
            results.append(evaluation)
        except Exception:
            logger.debug("Failed to evaluate strategy %s", strategy.get("name"), exc_info=True)
            results.append({
                "name": strategy.get("name", "Unknown"),
                "suitability_score": 0.0,
                "direction_fit": 0.0,
                "volatility_fit": 0.0,
                "time_horizon_fit": 0.0,
                "liquidity_fit": 0.0,
                "risk_reward_fit": 0.0,
                "event_risk_penalty": 5.0,
                "description": strategy.get("description", ""),
                "risk_warning": "Evaluation failed",
                "recommended_dte_range": "N/A",
            })

    results.sort(key=lambda r: r.get("suitability_score", 0), reverse=True)
    return results
