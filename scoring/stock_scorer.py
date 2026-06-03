"""
Stock Scorer — multi-factor weighted scoring system.

Combines trend, momentum, options-flow, LEAPS, fundamentals, sector, and
volume signals into a composite bull / bear / risk score.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from config import SCORING_WEIGHTS, SCORE_THRESHOLDS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _safe(val, default: float = 0.0) -> float:
    """Return *val* as float, or *default* if None / NaN / non-numeric."""
    if val is None:
        return default
    try:
        f = float(val)
        return f if f == f else default  # NaN check
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Individual category scorers (each returns 0-100)
# ---------------------------------------------------------------------------

def calculate_trend_score(price_features: dict) -> float:
    """Score based on moving-average alignment.

    Looks at:
    - price vs MA20, MA50, MA200
    - golden / death cross (MA50 vs MA200)
    """
    if not price_features:
        return 50.0  # neutral default

    try:
        score = 50.0
        price = _safe(price_features.get("close"))
        ma20 = _safe(price_features.get("ma20"))
        ma50 = _safe(price_features.get("ma50"))
        ma200 = _safe(price_features.get("ma200"))

        if price <= 0:
            return 50.0

        # Price relative to MAs (each worth up to ±10 pts)
        if ma20 > 0:
            score += 10.0 if price > ma20 else -10.0
        if ma50 > 0:
            score += 10.0 if price > ma50 else -10.0
        if ma200 > 0:
            score += 12.0 if price > ma200 else -12.0

        # MA alignment bonus (perfect alignment: MA20 > MA50 > MA200)
        if ma20 > 0 and ma50 > 0 and ma200 > 0:
            if ma20 > ma50 > ma200:
                score += 10.0  # bullish alignment
            elif ma20 < ma50 < ma200:
                score -= 10.0  # bearish alignment

        # Golden / death cross
        if ma50 > 0 and ma200 > 0:
            if ma50 > ma200:
                score += 8.0  # golden cross territory
            else:
                score -= 8.0  # death cross territory

        return _clamp(score)

    except Exception:
        logger.debug("calculate_trend_score failed", exc_info=True)
        return 50.0


def calculate_momentum_score(price_features: dict, technical: dict) -> float:
    """Score based on returns and momentum indicators.

    Inputs:
    - ``price_features`` keys: ``return_20d``, ``return_60d``, ``return_120d``
    - ``technical`` keys: ``rsi``, ``macd_histogram``
    """
    if not price_features and not technical:
        return 50.0

    try:
        score = 50.0

        # Return contributions (up to ±8 each)
        for key, weight in [("return_20d", 8), ("return_60d", 6), ("return_120d", 4)]:
            ret = _safe(price_features.get(key)) if price_features else 0.0
            if ret > 0.10:
                score += weight
            elif ret > 0.03:
                score += weight * 0.5
            elif ret < -0.10:
                score -= weight
            elif ret < -0.03:
                score -= weight * 0.5

        # RSI (mean-reversion aware)
        rsi = _safe(technical.get("rsi")) if technical else 0.0
        if 0 < rsi <= 30:
            score += 6  # oversold → contrarian bullish
        elif 30 < rsi <= 45:
            score += 3
        elif 55 <= rsi < 70:
            score += 5  # healthy momentum
        elif rsi >= 70:
            score -= 4  # overbought → caution

        # MACD histogram direction
        macd_hist = _safe(technical.get("macd_histogram")) if technical else 0.0
        if macd_hist > 0:
            score += 6
        elif macd_hist < 0:
            score -= 6

        return _clamp(score)

    except Exception:
        logger.debug("calculate_momentum_score failed", exc_info=True)
        return 50.0


def calculate_options_flow_score(options_data: dict) -> float:
    """Score based on put/call ratios and unusual activity."""
    if not options_data:
        return 50.0

    try:
        score = 50.0

        call_vol = _safe(options_data.get("total_call_volume"))
        put_vol = _safe(options_data.get("total_put_volume"))
        total = call_vol + put_vol

        if total > 0:
            pc_ratio = put_vol / max(call_vol, 1)
            if pc_ratio < 0.5:
                score += 25
            elif pc_ratio < 0.7:
                score += 15
            elif pc_ratio < 1.0:
                score += 5
            elif pc_ratio < 1.5:
                score -= 10
            else:
                score -= 25

        # OI tilt
        call_oi = _safe(options_data.get("total_call_oi"))
        put_oi = _safe(options_data.get("total_put_oi"))
        oi_total = call_oi + put_oi
        if oi_total > 0:
            oi_ratio = put_oi / max(call_oi, 1)
            if oi_ratio < 0.6:
                score += 10
            elif oi_ratio > 1.5:
                score -= 10

        # Unusual activity
        unusual = options_data.get("unusual_volume_contracts") or []
        if unusual:
            unusual_calls = sum(
                1 for c in unusual
                if isinstance(c, dict) and c.get("type", "").lower() == "call"
            )
            unusual_puts = len(unusual) - unusual_calls
            if unusual_calls > unusual_puts:
                score += 8
            elif unusual_puts > unusual_calls:
                score -= 8

        return _clamp(score)

    except Exception:
        logger.debug("calculate_options_flow_score failed", exc_info=True)
        return 50.0


def calculate_leaps_score(options_data: dict) -> float:
    """Score based on LEAPS call/put OI ratio and sentiment."""
    if not options_data:
        return 50.0

    try:
        score = 50.0
        leaps_call_oi = _safe(options_data.get("leaps_call_oi"))
        leaps_put_oi = _safe(options_data.get("leaps_put_oi"))
        total = leaps_call_oi + leaps_put_oi

        if total > 0:
            ratio = leaps_call_oi / max(leaps_put_oi, 1)
            if ratio > 3.0:
                score += 30
            elif ratio > 2.0:
                score += 20
            elif ratio > 1.2:
                score += 10
            elif ratio < 0.5:
                score -= 25
            elif ratio < 0.8:
                score -= 10

        # LEAPS volume activity
        leaps_call_vol = _safe(options_data.get("leaps_call_volume"))
        leaps_put_vol = _safe(options_data.get("leaps_put_volume"))
        leaps_vol_total = leaps_call_vol + leaps_put_vol
        if leaps_vol_total > 100:
            vol_ratio = leaps_call_vol / max(leaps_put_vol, 1)
            if vol_ratio > 2.0:
                score += 10
            elif vol_ratio < 0.5:
                score -= 10

        return _clamp(score)

    except Exception:
        logger.debug("calculate_leaps_score failed", exc_info=True)
        return 50.0


def calculate_fundamentals_score(fundamentals: dict) -> float:
    """Score based on P/E relative, revenue growth, margins, analyst consensus.

    ``fundamentals`` expected keys:
    - ``pe_ratio``
    - ``revenue_growth`` (e.g. 0.15 = 15 %)
    - ``profit_margin`` (e.g. 0.20 = 20 %)
    - ``analyst_rating`` ('buy'|'hold'|'sell' or 1.0-5.0 scale)
    - ``forward_pe``
    """
    PE_BENCHMARK = 20.0

    if not fundamentals:
        return 50.0

    try:
        score = 50.0

        # P/E relative to benchmark
        pe = _safe(fundamentals.get("pe_ratio"))
        if pe > 0:
            if pe < PE_BENCHMARK * 0.6:
                score += 12  # significantly undervalued
            elif pe < PE_BENCHMARK:
                score += 6
            elif pe > PE_BENCHMARK * 2:
                score -= 10
            elif pe > PE_BENCHMARK * 1.5:
                score -= 5

        # Revenue growth
        rev_growth = _safe(fundamentals.get("revenue_growth"))
        if rev_growth > 0.30:
            score += 12
        elif rev_growth > 0.15:
            score += 8
        elif rev_growth > 0.05:
            score += 4
        elif rev_growth < -0.05:
            score -= 8
        elif rev_growth < 0:
            score -= 4

        # Profit margins
        margin = _safe(fundamentals.get("profit_margin"))
        if margin > 0.25:
            score += 8
        elif margin > 0.10:
            score += 4
        elif margin < 0:
            score -= 8
        elif margin < 0.05:
            score -= 4

        # Analyst consensus
        rating = fundamentals.get("analyst_rating")
        if isinstance(rating, str):
            rating_map = {"strong_buy": 12, "buy": 8, "outperform": 6,
                          "hold": 0, "underperform": -6, "sell": -10,
                          "strong_sell": -12}
            score += rating_map.get(rating.lower(), 0)
        elif rating is not None:
            r = _safe(rating)
            if 0 < r <= 2.0:
                score += 10
            elif r <= 2.5:
                score += 5
            elif r >= 4.0:
                score -= 10
            elif r >= 3.5:
                score -= 5

        return _clamp(score)

    except Exception:
        logger.debug("calculate_fundamentals_score failed", exc_info=True)
        return 50.0


def calculate_sector_score(fundamentals: dict) -> float:
    """Placeholder for sector relative strength.  Always returns 50 (neutral)."""
    # Future: compare sector ETF momentum vs SPY
    return 50.0


def calculate_volume_score(price_features: dict) -> float:
    """Score based on volume trend: 20-day avg vs 60-day avg."""
    if not price_features:
        return 50.0

    try:
        score = 50.0
        vol_20 = _safe(price_features.get("avg_volume_20d"))
        vol_60 = _safe(price_features.get("avg_volume_60d"))

        if vol_60 > 0 and vol_20 > 0:
            ratio = vol_20 / vol_60
            if ratio > 1.5:
                score += 20  # surging volume
            elif ratio > 1.2:
                score += 12
            elif ratio > 1.0:
                score += 5
            elif ratio < 0.6:
                score -= 15  # declining interest
            elif ratio < 0.8:
                score -= 8

        return _clamp(score)

    except Exception:
        logger.debug("calculate_volume_score failed", exc_info=True)
        return 50.0


# ---------------------------------------------------------------------------
# Main composite scorer
# ---------------------------------------------------------------------------

def score_stock(
    price_features: dict,
    options_data: dict,
    fundamentals: dict,
    technical: dict,
) -> Dict[str, object]:
    """Compute weighted bull / bear / risk scores with explanations.

    Parameters
    ----------
    price_features : dict
        Keys such as ``close``, ``ma20``, ``ma50``, ``ma200``,
        ``return_20d``, ``return_60d``, ``return_120d``,
        ``avg_volume_20d``, ``avg_volume_60d``.
    options_data : dict
        Raw options data from fetcher.
    fundamentals : dict
        Company fundamentals from fetcher.
    technical : dict
        Output of ``calculate_all_indicators()``.

    Returns
    -------
    dict
        Composite scores, category breakdowns, reasons, and warnings.
    """
    # Ensure dicts are not None
    price_features = price_features or {}
    options_data = options_data or {}
    fundamentals = fundamentals or {}
    technical = technical or {}

    try:
        # Category scores
        category_scores = {
            "trend": calculate_trend_score(price_features),
            "momentum": calculate_momentum_score(price_features, technical),
            "options_flow": calculate_options_flow_score(options_data),
            "leaps": calculate_leaps_score(options_data),
            "fundamentals": calculate_fundamentals_score(fundamentals),
            "sector": calculate_sector_score(fundamentals),
            "volume": calculate_volume_score(price_features),
        }

        # Weighted bull score
        bull_score = sum(
            category_scores[cat] * SCORING_WEIGHTS.get(cat, 0)
            for cat in category_scores
        )
        bull_score = _clamp(bull_score)

        # Bear score: inverse of bullish signals
        bear_score = _clamp(100.0 - bull_score)

        # Risk score: high when signals are mixed or extreme
        risk_score = _compute_risk_score(category_scores, technical, price_features)

        # Confidence
        confidence = _compute_confidence(price_features, options_data, fundamentals, technical)

        # Reasons & warnings
        reasons = _generate_reasons(category_scores, technical, price_features, options_data)
        warnings = _generate_warnings(category_scores, technical, price_features, options_data, risk_score)

        return {
            "bull_score": round(bull_score, 1),
            "bear_score": round(bear_score, 1),
            "risk_score": round(risk_score, 1),
            "confidence": confidence,
            "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
            "reasons": reasons[:5],
            "warnings": warnings[:5],
        }

    except Exception:
        logger.exception("score_stock failed")
        return {
            "bull_score": 50.0,
            "bear_score": 50.0,
            "risk_score": 50.0,
            "confidence": "low",
            "category_scores": {k: 50.0 for k in SCORING_WEIGHTS},
            "reasons": [],
            "warnings": ["Scoring encountered an error — results are defaults"],
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_risk_score(
    cat_scores: dict,
    technical: dict,
    price_features: dict,
) -> float:
    """Risk = divergence across categories + volatility + RSI extremes."""
    scores = list(cat_scores.values())
    if not scores:
        return 50.0

    risk = 30.0  # baseline

    # Category divergence: high std ⇒ mixed signals ⇒ risky
    import statistics
    if len(scores) >= 2:
        std = statistics.stdev(scores)
        risk += min(std * 0.5, 20)  # cap contribution at 20

    # ATR-based volatility
    atr_pct = _safe(technical.get("atr_pct"))
    if atr_pct > 5.0:
        risk += 15
    elif atr_pct > 3.0:
        risk += 8
    elif atr_pct > 2.0:
        risk += 3

    # RSI extremes
    rsi = _safe(technical.get("rsi"))
    if rsi > 80 or rsi < 20:
        risk += 10
    elif rsi > 70 or rsi < 30:
        risk += 5

    return _clamp(risk)


def _compute_confidence(
    price_features: dict,
    options_data: dict,
    fundamentals: dict,
    technical: dict,
) -> float:
    """Confidence = percentage of available data features + volume liquidity bonus."""
    total_features = 0
    valid_features = 0

    # Check key fundamentals
    fund_keys = ["pe_ratio", "forward_pe", "revenue_growth", "profit_margin", "analyst_rating"]
    if fundamentals:
        for k in fund_keys:
            total_features += 1
            if fundamentals.get(k) is not None and str(fundamentals.get(k)).lower() != "nan":
                valid_features += 1
    else:
        total_features += len(fund_keys)

    # Check options data
    opt_keys = ["put_call_volume_ratio", "total_call_oi", "avg_call_iv", "leaps_call_oi"]
    if options_data:
        for k in opt_keys:
            total_features += 1
            if options_data.get(k) is not None and str(options_data.get(k)).lower() != "nan":
                valid_features += 1
    else:
        total_features += len(opt_keys)
        
    # Check technicals
    tech_keys = ["rsi", "macd", "bb_pct_b", "atr_pct"]
    if technical:
        for k in tech_keys:
            total_features += 1
            if technical.get(k) is not None and str(technical.get(k)).lower() != "nan":
                valid_features += 1
    else:
        total_features += len(tech_keys)
        
    # Base confidence is data completeness
    base_confidence = (valid_features / max(total_features, 1)) * 100.0
    
    # Adjust confidence slightly based on average daily volume (more liquidity = higher confidence)
    volume = price_features.get("avg_volume_20d") if price_features else 0
    if volume is not None and str(volume).lower() != "nan":
        if volume > 5_000_000:
            base_confidence = min(100.0, base_confidence + 10)
        elif volume < 500_000:
            base_confidence = max(0.0, base_confidence - 10)
            
    return _clamp(base_confidence)


def _generate_reasons(
    cat_scores: dict,
    technical: dict,
    price_features: dict,
    options_data: dict,
) -> List[str]:
    """Generate top bullish reasons sorted by strength."""
    reasons: List[str] = []

    t = cat_scores.get("trend", 50)
    if t >= 70:
        reasons.append(("Strong uptrend — price above key moving averages", t))
    elif t >= 60:
        reasons.append(("Positive trend — price above most moving averages", t))

    m = cat_scores.get("momentum", 50)
    if m >= 70:
        reasons.append(("Strong momentum — positive returns and MACD", m))
    elif m >= 60:
        reasons.append(("Decent momentum — returns trending positive", m))

    o = cat_scores.get("options_flow", 50)
    if o >= 70:
        reasons.append(("Bullish options flow — call volume dominates", o))
    elif o >= 60:
        reasons.append(("Options flow leaning bullish", o))

    lp = cat_scores.get("leaps", 50)
    if lp >= 70:
        reasons.append(("Strong LEAPS bullish positioning — institutional conviction", lp))
    elif lp >= 60:
        reasons.append(("LEAPS positioning favors calls", lp))

    f = cat_scores.get("fundamentals", 50)
    if f >= 70:
        reasons.append(("Strong fundamentals — good growth and margins", f))
    elif f >= 60:
        reasons.append(("Decent fundamentals supporting valuation", f))

    v = cat_scores.get("volume", 50)
    if v >= 65:
        reasons.append(("Rising volume confirms interest", v))

    rsi = _safe(technical.get("rsi"))
    if 0 < rsi <= 35:
        reasons.append(("RSI oversold ({:.0f}) — potential bounce".format(rsi), 65))

    div = technical.get("rsi_divergence", "none") if technical else "none"
    if div == "bullish_divergence":
        reasons.append(("Bullish RSI divergence detected", 68))

    # Sort by score descending, return only text
    reasons.sort(key=lambda x: x[1] if isinstance(x, tuple) else 0, reverse=True)
    return [r[0] if isinstance(r, tuple) else r for r in reasons]


def _generate_warnings(
    cat_scores: dict,
    technical: dict,
    price_features: dict,
    options_data: dict,
    risk_score: float,
) -> List[str]:
    """Generate risk warnings."""
    warnings: List[str] = []

    if risk_score >= 70:
        warnings.append("High overall risk score ({:.0f})".format(risk_score))

    t = cat_scores.get("trend", 50)
    if t <= 30:
        warnings.append("Strong downtrend — price below key moving averages")

    rsi = _safe(technical.get("rsi"))
    if rsi >= 75:
        warnings.append("RSI overbought ({:.0f}) — potential pullback".format(rsi))

    atr_pct = _safe(technical.get("atr_pct"))
    if atr_pct > 4.0:
        warnings.append("High volatility — ATR is {:.1f}% of price".format(atr_pct))

    m = cat_scores.get("momentum", 50)
    if m <= 30:
        warnings.append("Weak momentum — negative returns across timeframes")

    o = cat_scores.get("options_flow", 50)
    if o <= 30:
        warnings.append("Bearish options flow — put volume dominates")

    div = technical.get("rsi_divergence", "none") if technical else "none"
    if div == "bearish_divergence":
        warnings.append("Bearish RSI divergence detected")

    avg_iv = _safe(options_data.get("avg_call_iv")) if options_data else 0
    if avg_iv > 0.80:
        warnings.append("Very high implied volatility ({:.0%}) — expensive options".format(avg_iv))

    return warnings
