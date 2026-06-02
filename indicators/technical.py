"""
Technical Indicators — pure pandas / numpy calculations.

All functions accept Series or DataFrame inputs and return Series, tuples of
Series, or dicts of scalar values.  No external data fetching happens here.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from config import (
    RSI_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    BB_PERIOD,
    BB_STD,
    ATR_PERIOD,
    STOCH_K,
    STOCH_D,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_MIN_ROWS_FOR_INDICATORS = 50


def _safe_float(val: object) -> float:
    """Convert *val* to a plain Python float, returning NaN on failure."""
    try:
        f = float(val)
        return f if np.isfinite(f) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


# ---------------------------------------------------------------------------
# RSI (Wilder's smoothed)
# ---------------------------------------------------------------------------

def calculate_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Compute Wilder's smoothed RSI.

    Uses ``ewm(com=period-1, adjust=False)`` which is equivalent to
    Wilder's exponential smoothing with α = 1/period.

    Parameters
    ----------
    close : pd.Series
        Closing prices.
    period : int
        Look-back period (default from config).

    Returns
    -------
    pd.Series
        RSI values in [0, 100].  Early values will be NaN until enough
        data exists.
    """
    if close.empty or len(close) < period + 1:
        return pd.Series(dtype=float, index=close.index)

    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    return rsi


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

def calculate_macd(
    close: pd.Series,
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Standard MACD: fast EMA − slow EMA, signal EMA of MACD line, histogram.

    Returns
    -------
    (macd_line, signal_line, histogram)
    """
    if close.empty or len(close) < slow + signal:
        empty = pd.Series(dtype=float, index=close.index)
        return empty, empty.copy(), empty.copy()

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------

def calculate_bollinger_bands(
    close: pd.Series,
    period: int = BB_PERIOD,
    std_dev: float = BB_STD,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: middle = SMA, upper/lower = middle ± std_dev × σ.

    Returns
    -------
    (upper, middle, lower)
    """
    if close.empty or len(close) < period:
        empty = pd.Series(dtype=float, index=close.index)
        return empty, empty.copy(), empty.copy()

    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std(ddof=0)

    upper = middle + std_dev * std
    lower = middle - std_dev * std

    return upper, middle, lower


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------

def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = ATR_PERIOD,
) -> pd.Series:
    """Average True Range using Wilder's smoothing.

    Parameters
    ----------
    high, low, close : pd.Series
        Price series (must share the same index).
    period : int
        Look-back window.
    """
    if close.empty or len(close) < period + 1:
        return pd.Series(dtype=float, index=close.index)

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    return atr


# ---------------------------------------------------------------------------
# Stochastic Oscillator
# ---------------------------------------------------------------------------

def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = STOCH_K,
    d_period: int = STOCH_D,
) -> Tuple[pd.Series, pd.Series]:
    """Stochastic %K and %D.

    %K = (close − lowest low) / (highest high − lowest low) × 100
    %D = SMA(%K, d_period)

    Returns
    -------
    (k_line, d_line)
    """
    if close.empty or len(close) < k_period:
        empty = pd.Series(dtype=float, index=close.index)
        return empty, empty.copy()

    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    denom = highest_high - lowest_low
    denom = denom.replace(0, np.nan)

    k_line = 100.0 * (close - lowest_low) / denom
    d_line = k_line.rolling(window=d_period).mean()

    return k_line, d_line


# ---------------------------------------------------------------------------
# RSI Divergence Detection
# ---------------------------------------------------------------------------

def detect_rsi_divergence(
    close: pd.Series,
    rsi: pd.Series,
    lookback: int = 20,
) -> str:
    """Detect bullish or bearish RSI divergence over *lookback* bars.

    Bullish divergence : price makes a **lower low** but RSI makes a
                         **higher low**.
    Bearish divergence : price makes a **higher high** but RSI makes a
                         **lower high**.

    Returns
    -------
    str
        ``'bullish_divergence'``, ``'bearish_divergence'``, or ``'none'``.
    """
    if close.empty or rsi.empty or len(close) < lookback + 2:
        return "none"

    try:
        window_close = close.iloc[-lookback:]
        window_rsi = rsi.iloc[-lookback:]

        # Drop NaN rows in RSI (early period)
        valid_mask = window_rsi.notna()
        if valid_mask.sum() < 5:
            return "none"

        window_close = window_close[valid_mask]
        window_rsi = window_rsi[valid_mask]

        # Split window into halves for "two troughs / two peaks" comparison
        mid = len(window_close) // 2

        first_close = window_close.iloc[:mid]
        second_close = window_close.iloc[mid:]
        first_rsi = window_rsi.iloc[:mid]
        second_rsi = window_rsi.iloc[mid:]

        # --- Bullish divergence (lower low in price, higher low in RSI) ---
        price_low_first = first_close.min()
        price_low_second = second_close.min()
        rsi_low_first = first_rsi.min()
        rsi_low_second = second_rsi.min()

        if price_low_second < price_low_first and rsi_low_second > rsi_low_first:
            return "bullish_divergence"

        # --- Bearish divergence (higher high in price, lower high in RSI) ---
        price_high_first = first_close.max()
        price_high_second = second_close.max()
        rsi_high_first = first_rsi.max()
        rsi_high_second = second_rsi.max()

        if price_high_second > price_high_first and rsi_high_second < rsi_high_first:
            return "bearish_divergence"

    except Exception:
        logger.debug("RSI divergence detection failed", exc_info=True)

    return "none"


# ---------------------------------------------------------------------------
# Composite: calculate all indicators for latest bar
# ---------------------------------------------------------------------------

def calculate_all_indicators(hist: pd.DataFrame) -> Dict[str, object]:
    """Compute all indicators and return latest scalar values.

    Parameters
    ----------
    hist : pd.DataFrame
        Must contain columns ``Close``, ``High``, ``Low``, ``Volume``.
        Optionally ``Date`` / ``Open``.

    Returns
    -------
    dict
        Indicator name → latest value.  Returns ``{}`` if *hist* is
        empty or has fewer than ``_MIN_ROWS_FOR_INDICATORS`` rows.
    """
    if hist is None or hist.empty or len(hist) < _MIN_ROWS_FOR_INDICATORS:
        return {}

    try:
        close = hist["Close"]
        high = hist["High"]
        low = hist["Low"]

        rsi = calculate_rsi(close)
        macd_line, signal_line, histogram = calculate_macd(close)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close)
        atr = calculate_atr(high, low, close)
        stoch_k, stoch_d = calculate_stochastic(high, low, close)

        divergence = detect_rsi_divergence(close, rsi)

        latest_close = _safe_float(close.iloc[-1])
        latest_bb_upper = _safe_float(bb_upper.iloc[-1])
        latest_bb_lower = _safe_float(bb_lower.iloc[-1])
        bb_range = latest_bb_upper - latest_bb_lower
        bb_pct_b = (
            (latest_close - latest_bb_lower) / bb_range
            if bb_range > 0
            else float("nan")
        )

        latest_atr = _safe_float(atr.iloc[-1])
        atr_pct = (
            (latest_atr / latest_close) * 100.0
            if latest_close > 0
            else float("nan")
        )

        return {
            "rsi": _safe_float(rsi.iloc[-1]),
            "macd": _safe_float(macd_line.iloc[-1]),
            "macd_signal": _safe_float(signal_line.iloc[-1]),
            "macd_histogram": _safe_float(histogram.iloc[-1]),
            "bb_upper": latest_bb_upper,
            "bb_middle": _safe_float(bb_middle.iloc[-1]),
            "bb_lower": latest_bb_lower,
            "bb_pct_b": _safe_float(bb_pct_b),
            "atr": latest_atr,
            "atr_pct": _safe_float(atr_pct),
            "stoch_k": _safe_float(stoch_k.iloc[-1]),
            "stoch_d": _safe_float(stoch_d.iloc[-1]),
            "rsi_divergence": divergence,
        }

    except Exception:
        logger.exception("calculate_all_indicators failed")
        return {}


# ---------------------------------------------------------------------------
# Add indicator columns to DataFrame (for charting)
# ---------------------------------------------------------------------------

def add_indicators_to_df(hist: pd.DataFrame) -> pd.DataFrame:
    """Return *hist* with indicator columns appended.

    Added columns: ``RSI``, ``MACD``, ``MACD_Signal``, ``MACD_Hist``,
    ``BB_Upper``, ``BB_Middle``, ``BB_Lower``, ``ATR``, ``Stoch_K``,
    ``Stoch_D``.

    If the input is too short for a given indicator the column will be
    all-NaN rather than missing.
    """
    if hist is None or hist.empty:
        return hist if hist is not None else pd.DataFrame()

    df = hist.copy()

    try:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        df["RSI"] = calculate_rsi(close)

        macd_line, signal_line, histogram = calculate_macd(close)
        df["MACD"] = macd_line
        df["MACD_Signal"] = signal_line
        df["MACD_Hist"] = histogram

        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close)
        df["BB_Upper"] = bb_upper
        df["BB_Middle"] = bb_middle
        df["BB_Lower"] = bb_lower

        df["ATR"] = calculate_atr(high, low, close)

        stoch_k, stoch_d = calculate_stochastic(high, low, close)
        df["Stoch_K"] = stoch_k
        df["Stoch_D"] = stoch_d

    except Exception:
        logger.exception("add_indicators_to_df failed — returning original df")

    return df
