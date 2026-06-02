"""
Options Sentiment Analysis — wraps and extends the raw options data
returned by ``data.fetcher.get_options_data()``.
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _safe_get(d: dict, *keys, default=None):
    """Nested dict lookup that never raises."""
    current = d
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k, default)
    return current


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_options_sentiment(options_data: dict) -> Dict[str, object]:
    """Produce a sentiment analysis dict from raw options data.

    Parameters
    ----------
    options_data : dict
        The dict returned by ``data.fetcher.get_options_data()``.  Expected
        keys (all optional — missing keys degrade gracefully):

        - ``total_call_volume``, ``total_put_volume``
        - ``total_call_oi``, ``total_put_oi``
        - ``avg_call_iv``, ``avg_put_iv``
        - ``leaps_call_oi``, ``leaps_put_oi``
        - ``leaps_call_volume``, ``leaps_put_volume``
        - ``unusual_volume_contracts`` (list)
        - ``near_term_call_iv``, ``near_term_put_iv``
        - ``far_term_call_iv``, ``far_term_put_iv``

    Returns
    -------
    dict
        ``overall_sentiment``, ``sentiment_score`` (-100 to +100),
        ``volume_signal``, ``oi_signal``, ``leaps_signal``, ``iv_signal``,
        ``unusual_activity``.
    """
    default_result: Dict[str, object] = {
        "overall_sentiment": "neutral",
        "sentiment_score": 0,
        "volume_signal": "No options data available",
        "oi_signal": "No options data available",
        "leaps_signal": "No options data available",
        "iv_signal": "No options data available",
        "unusual_activity": False,
    }

    if not options_data or not isinstance(options_data, dict):
        return default_result

    try:
        score = 0.0  # accumulate in [-100, +100]

        # ----- Volume-based signals -----------------------------------
        call_vol = _safe_get(options_data, "total_call_volume", default=0) or 0
        put_vol = _safe_get(options_data, "total_put_volume", default=0) or 0
        total_vol = call_vol + put_vol

        if total_vol > 0:
            pc_ratio_vol = put_vol / max(call_vol, 1)
            if pc_ratio_vol < 0.5:
                vol_signal = "Strong bullish — call volume dominates (P/C ratio {:.2f})".format(pc_ratio_vol)
                score += 25
            elif pc_ratio_vol < 0.7:
                vol_signal = "Mildly bullish — call volume leads (P/C ratio {:.2f})".format(pc_ratio_vol)
                score += 15
            elif pc_ratio_vol <= 1.0:
                vol_signal = "Neutral volume flow (P/C ratio {:.2f})".format(pc_ratio_vol)
            elif pc_ratio_vol <= 1.5:
                vol_signal = "Mildly bearish — put volume leads (P/C ratio {:.2f})".format(pc_ratio_vol)
                score -= 15
            else:
                vol_signal = "Strong bearish — put volume dominates (P/C ratio {:.2f})".format(pc_ratio_vol)
                score -= 25
        else:
            vol_signal = "No meaningful options volume detected"

        # ----- Open interest signals ----------------------------------
        call_oi = _safe_get(options_data, "total_call_oi", default=0) or 0
        put_oi = _safe_get(options_data, "total_put_oi", default=0) or 0
        total_oi = call_oi + put_oi

        if total_oi > 0:
            pc_ratio_oi = put_oi / max(call_oi, 1)
            if pc_ratio_oi < 0.5:
                oi_signal = "Bullish positioning — large call OI (P/C OI ratio {:.2f})".format(pc_ratio_oi)
                score += 20
            elif pc_ratio_oi < 0.8:
                oi_signal = "Leaning bullish — more call OI (P/C OI ratio {:.2f})".format(pc_ratio_oi)
                score += 10
            elif pc_ratio_oi <= 1.2:
                oi_signal = "Balanced open interest (P/C OI ratio {:.2f})".format(pc_ratio_oi)
            elif pc_ratio_oi <= 1.8:
                oi_signal = "Leaning bearish — more put OI (P/C OI ratio {:.2f})".format(pc_ratio_oi)
                score -= 10
            else:
                oi_signal = "Bearish positioning — large put OI (P/C OI ratio {:.2f})".format(pc_ratio_oi)
                score -= 20
        else:
            oi_signal = "No open interest data available"

        # ----- LEAPS signals ------------------------------------------
        leaps_call_oi = _safe_get(options_data, "leaps_call_oi", default=0) or 0
        leaps_put_oi = _safe_get(options_data, "leaps_put_oi", default=0) or 0
        leaps_total = leaps_call_oi + leaps_put_oi

        if leaps_total > 0:
            leaps_ratio = leaps_call_oi / max(leaps_put_oi, 1)
            if leaps_ratio > 2.0:
                leaps_signal = "Strong long-term bullish — LEAPS call OI {:.1f}× put OI".format(leaps_ratio)
                score += 20
            elif leaps_ratio > 1.2:
                leaps_signal = "Mildly bullish long-term outlook — LEAPS call/put ratio {:.2f}".format(leaps_ratio)
                score += 10
            elif leaps_ratio >= 0.8:
                leaps_signal = "Neutral long-term outlook — balanced LEAPS positioning"
            elif leaps_ratio >= 0.5:
                leaps_signal = "Mildly bearish long-term — LEAPS put OI exceeds call OI"
                score -= 10
            else:
                leaps_signal = "Strong long-term bearish — heavy LEAPS put positioning"
                score -= 20
        else:
            leaps_signal = "No LEAPS data available"

        # ----- Implied volatility signals -----------------------------
        avg_call_iv = _safe_get(options_data, "avg_call_iv", default=0) or 0
        avg_put_iv = _safe_get(options_data, "avg_put_iv", default=0) or 0

        if avg_call_iv > 0 or avg_put_iv > 0:
            avg_iv = (avg_call_iv + avg_put_iv) / 2 if (avg_call_iv > 0 and avg_put_iv > 0) else max(avg_call_iv, avg_put_iv)
            skew = avg_put_iv - avg_call_iv  # positive ⇒ puts are pricier ⇒ fear

            if avg_iv > 0.80:
                iv_signal = "Very high IV ({:.0%}) — expensive premiums, potential event risk".format(avg_iv)
                score -= 5  # high IV is ambiguous; slight negative for cost
            elif avg_iv > 0.50:
                iv_signal = "Elevated IV ({:.0%}) — market expects significant movement".format(avg_iv)
            elif avg_iv > 0.20:
                iv_signal = "Normal IV ({:.0%})".format(avg_iv)
            else:
                iv_signal = "Low IV ({:.0%}) — options are cheap, potential for vol expansion".format(avg_iv)

            # Skew adjustment
            if skew > 0.10:
                iv_signal += "; put skew detected (protective demand)"
                score -= 5
            elif skew < -0.10:
                iv_signal += "; call skew detected (speculative demand)"
                score += 5
        else:
            iv_signal = "No IV data available"

        # ----- Unusual activity ---------------------------------------
        unusual_contracts = _safe_get(options_data, "unusual_volume_contracts", default=[]) or []
        unusual_activity = len(unusual_contracts) > 0
        if unusual_activity:
            # Boost / penalise based on dominant side
            unusual_calls = sum(1 for c in unusual_contracts if isinstance(c, dict) and c.get("type", "").lower() == "call")
            unusual_puts = len(unusual_contracts) - unusual_calls
            if unusual_calls > unusual_puts:
                score += 10
            elif unusual_puts > unusual_calls:
                score -= 10

        # ----- Aggregate ----------------------------------------------
        score = _clamp(score, -100, 100)

        if score >= 25:
            sentiment = "bullish"
        elif score <= -25:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        return {
            "overall_sentiment": sentiment,
            "sentiment_score": round(score),
            "volume_signal": vol_signal,
            "oi_signal": oi_signal,
            "leaps_signal": leaps_signal,
            "iv_signal": iv_signal,
            "unusual_activity": unusual_activity,
        }

    except Exception:
        logger.exception("analyze_options_sentiment failed")
        return default_result
