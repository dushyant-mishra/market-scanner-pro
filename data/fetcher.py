"""
Market Scanner V2 — Data Fetcher

Handles all yfinance data retrieval with Streamlit caching.  Every public
function is decorated with ``@st.cache_data`` so repeated calls within the
cache TTL window are served from memory.
"""

from __future__ import annotations

import time
from datetime import date, datetime
from typing import Any, Optional

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from config import CACHE_TTL

# 24 hour TTL for financial statements to avoid rate limits
FINANCIALS_TTL = 86400

# =====================================================================
# Helpers
# =====================================================================

def safe_divide(a: Any, b: Any) -> float:
    """Return ``a / b``, or ``np.nan`` when *b* is ``None``, ``0``, or ``NaN``.

    Parameters
    ----------
    a, b : numeric
        Numerator and denominator.

    Returns
    -------
    float
        The quotient, or ``np.nan`` on degenerate input.
    """
    try:
        if b is None or b == 0:
            return np.nan
        if np.isnan(b):
            return np.nan
        return float(a) / float(b)
    except (TypeError, ValueError):
        return np.nan


# =====================================================================
# Price history
# =====================================================================

@st.cache_data(ttl=CACHE_TTL)
def get_price_history(
    ticker: str,
    period: str = "1y",
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """Fetch OHLCV price history for *ticker* from Yahoo Finance.

    Parameters
    ----------
    ticker : str
        Equity or ETF symbol (e.g. ``"AAPL"``).
    period : str, optional
        Look-back window understood by yfinance (default ``"1y"``).
    start : str, optional
        Start date string (YYYY-MM-DD).
    end : str, optional
        End date string (YYYY-MM-DD).

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ``Date, Open, High, Low, Close, Volume``
        (and possibly ``Dividends, Stock Splits``).  Returns an empty
        DataFrame on any failure.
    """
    try:
        tk = yf.Ticker(ticker)
        if start and end:
            df: pd.DataFrame = tk.history(start=start, end=end, auto_adjust=True)
        else:
            df: pd.DataFrame = tk.history(period=period, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        return df
    except Exception:
        return pd.DataFrame()


# =====================================================================
# Fundamentals
# =====================================================================

@st.cache_data(ttl=CACHE_TTL)
def get_fundamentals(ticker: str) -> dict[str, Any]:
    """Return a curated dict of fundamental data for *ticker*.

    All values default to ``np.nan`` (or ``""`` for string fields) when
    the underlying yfinance ``.info`` dict does not contain them.

    Parameters
    ----------
    ticker : str
        Equity or ETF symbol.

    Returns
    -------
    dict[str, Any]
        Keys include identifiers (symbol, shortName, sector, industry),
        valuation metrics, analyst estimates, and growth figures.
    """
    _default: dict[str, Any] = {
        "symbol": ticker,
        "shortName": "",
        "sector": "",
        "industry": "",
        "marketCap": np.nan,
        "trailingPE": np.nan,
        "forwardPE": np.nan,
        "pegRatio": np.nan,
        "beta": np.nan,
        "dividendYield": np.nan,
        "fiftyTwoWeekHigh": np.nan,
        "fiftyTwoWeekLow": np.nan,
        "shortPercentOfFloat": np.nan,
        "averageVolume": np.nan,
        "targetMeanPrice": np.nan,
        "recommendationKey": "",
        "numberOfAnalystOpinions": np.nan,
        "revenueGrowth": np.nan,
        "earningsGrowth": np.nan,
        "profitMargins": np.nan,
        "returnOnEquity": np.nan,
        "operatingMargins": np.nan,
        "freeCashflow": np.nan,
        "debtToEquity": np.nan,
        "currentRatio": np.nan,
        "forwardEps": np.nan,
        "trailingEps": np.nan,
    }

    try:
        info: dict[str, Any] = yf.Ticker(ticker).info
        result: dict[str, Any] = {}
        for key, fallback in _default.items():
            result[key] = info.get(key, fallback)
        return result
    except Exception:
        return _default.copy()

@st.cache_data(ttl=FINANCIALS_TTL)
def get_financials_statements(ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch annual income statement and balance sheet for *ticker*.
    
    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (income_stmt, balance_sheet). Returns empty dataframes on failure.
    """
    try:
        tk = yf.Ticker(ticker)
        inc = tk.income_stmt
        bs = tk.balance_sheet
        if inc is None:
            inc = pd.DataFrame()
        if bs is None:
            bs = pd.DataFrame()
        return inc, bs
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

# =====================================================================
# Options data
# =====================================================================

def _default_options_dict() -> dict[str, Any]:
    """Return the options-data dict with all fields set to safe defaults."""
    return {
        "has_options": False,
        "put_call_volume_ratio": np.nan,
        "put_call_oi_ratio": np.nan,
        "leaps_call_oi": 0,
        "leaps_put_oi": 0,
        "leaps_call_put_oi_ratio": np.nan,
        "avg_call_iv": np.nan,
        "avg_put_iv": np.nan,
        "iv_skew_put_minus_call": np.nan,
        "near_term_iv": np.nan,
        "far_term_iv": np.nan,
        "iv_term_structure": np.nan,
        "options_liquidity_score": np.nan,
        "unusual_volume_count": 0,
    }


@st.cache_data(ttl=CACHE_TTL)
def get_options_data(ticker: str) -> dict[str, Any]:
    """Aggregate options-chain metrics for *ticker*.

    Iterates through up to 12 expiration dates, computing put/call
    ratios, IV skew, LEAPS open-interest, a liquidity score, and
    unusual-volume counts.

    Parameters
    ----------
    ticker : str
        Equity or ETF symbol.

    Returns
    -------
    dict[str, Any]
        See ``_default_options_dict`` for the full key set.
    """
    try:
        tk = yf.Ticker(ticker)
        expirations: tuple[str, ...] = tk.options
        if not expirations:
            return _default_options_dict()

        # Limit to first 12 expirations
        expirations = expirations[:12]

        total_call_vol = 0
        total_put_vol = 0
        total_call_oi = 0
        total_put_oi = 0
        leaps_call_oi = 0
        leaps_put_oi = 0

        call_ivs: list[float] = []
        put_ivs: list[float] = []

        near_term_ivs: list[float] = []   # DTE < 30, ATM
        far_term_ivs: list[float] = []    # 60 <= DTE <= 180, ATM

        liquidity_scores: list[float] = []
        unusual_volume_count = 0

        today = date.today()

        for exp_str in expirations:
            try:
                chain = tk.option_chain(exp_str)
            except Exception:
                time.sleep(0.05)
                continue

            calls: pd.DataFrame = chain.calls
            puts: pd.DataFrame = chain.puts

            # Days to expiration
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            dte = (exp_date - today).days

            # --- Volume & OI aggregation ---
            c_vol = int(calls["volume"].fillna(0).sum())
            p_vol = int(puts["volume"].fillna(0).sum())
            c_oi = int(calls["openInterest"].fillna(0).sum())
            p_oi = int(puts["openInterest"].fillna(0).sum())

            total_call_vol += c_vol
            total_put_vol += p_vol
            total_call_oi += c_oi
            total_put_oi += p_oi

            # LEAPS (DTE >= 180)
            if dte >= 180:
                leaps_call_oi += c_oi
                leaps_put_oi += p_oi

            # --- Implied volatility ---
            if "impliedVolatility" in calls.columns:
                valid_c_iv = calls["impliedVolatility"].dropna()
                if not valid_c_iv.empty:
                    call_ivs.extend(valid_c_iv.tolist())

            if "impliedVolatility" in puts.columns:
                valid_p_iv = puts["impliedVolatility"].dropna()
                if not valid_p_iv.empty:
                    put_ivs.extend(valid_p_iv.tolist())

            # --- ATM IV for term-structure (use options closest to lastPrice) ---
            if "lastPrice" in calls.columns and "impliedVolatility" in calls.columns:
                try:
                    atm_strike = calls.iloc[
                        (calls["inTheMoney"].astype(int).diff().abs()).idxmax()
                    ]["strike"] if "inTheMoney" in calls.columns else None

                    if atm_strike is not None:
                        atm_calls = calls[calls["strike"] == atm_strike]
                        atm_puts = puts[puts["strike"] == atm_strike]

                        atm_iv_vals: list[float] = []
                        if not atm_calls.empty and pd.notna(
                            atm_calls.iloc[0].get("impliedVolatility")
                        ):
                            atm_iv_vals.append(
                                float(atm_calls.iloc[0]["impliedVolatility"])
                            )
                        if not atm_puts.empty and pd.notna(
                            atm_puts.iloc[0].get("impliedVolatility")
                        ):
                            atm_iv_vals.append(
                                float(atm_puts.iloc[0]["impliedVolatility"])
                            )

                        if atm_iv_vals:
                            avg_atm = float(np.mean(atm_iv_vals))
                            if dte < 30:
                                near_term_ivs.append(avg_atm)
                            elif 60 <= dte <= 180:
                                far_term_ivs.append(avg_atm)
                except Exception:
                    pass

            # --- Liquidity score per expiration ---
            for _df in (calls, puts):
                if {"volume", "bid", "ask"}.issubset(_df.columns):
                    mid = (_df["bid"] + _df["ask"]) / 2
                    spread_pct = safe_divide(
                        (_df["ask"] - _df["bid"]).mean(),
                        mid.mean(),
                    )
                    vol_score = min(float(_df["volume"].fillna(0).sum()) / 1000, 50)
                    spread_score = max(0.0, 50.0 - (spread_pct * 500)) if not np.isnan(spread_pct) else 0.0
                    liquidity_scores.append(vol_score + spread_score)

            # --- Unusual volume ---
            for _df in (calls, puts):
                if {"volume", "openInterest"}.issubset(_df.columns):
                    vol = _df["volume"].fillna(0)
                    oi = _df["openInterest"].fillna(0)
                    unusual_volume_count += int(
                        ((vol > 0) & (oi > 0) & (vol > 3 * oi)).sum()
                    )

            time.sleep(0.05)

        # --- Aggregate ---
        avg_call_iv = float(np.mean(call_ivs)) if call_ivs else np.nan
        avg_put_iv = float(np.mean(put_ivs)) if put_ivs else np.nan

        near_term_iv = float(np.mean(near_term_ivs)) if near_term_ivs else np.nan
        far_term_iv = float(np.mean(far_term_ivs)) if far_term_ivs else np.nan

        return {
            "has_options": True,
            "put_call_volume_ratio": safe_divide(total_put_vol, total_call_vol),
            "put_call_oi_ratio": safe_divide(total_put_oi, total_call_oi),
            "leaps_call_oi": leaps_call_oi,
            "leaps_put_oi": leaps_put_oi,
            "leaps_call_put_oi_ratio": safe_divide(leaps_call_oi, leaps_put_oi),
            "avg_call_iv": avg_call_iv,
            "avg_put_iv": avg_put_iv,
            "iv_skew_put_minus_call": (avg_put_iv - avg_call_iv)
            if not (np.isnan(avg_put_iv) or np.isnan(avg_call_iv))
            else np.nan,
            "near_term_iv": near_term_iv,
            "far_term_iv": far_term_iv,
            "iv_term_structure": safe_divide(near_term_iv, far_term_iv),
            "options_liquidity_score": float(
                np.clip(np.mean(liquidity_scores), 0, 100)
            )
            if liquidity_scores
            else np.nan,
            "unusual_volume_count": unusual_volume_count,
        }

    except Exception:
        return _default_options_dict()


# =====================================================================
# Earnings date
# =====================================================================

@st.cache_data(ttl=CACHE_TTL)
def get_earnings_date(ticker: str) -> Optional[date]:
    """Return the next earnings date for *ticker*, or ``None`` if unknown.

    Parameters
    ----------
    ticker : str
        Equity or ETF symbol.

    Returns
    -------
    date or None
        The next scheduled earnings date, if available.
    """
    try:
        tk = yf.Ticker(ticker)
        cal = tk.calendar
        if cal is None:
            return None

        # yfinance returns either a DataFrame or a dict depending on version
        if isinstance(cal, pd.DataFrame):
            if "Earnings Date" in cal.columns:
                raw = cal["Earnings Date"].iloc[0]
            elif "Earnings Date" in cal.index:
                raw = cal.loc["Earnings Date"].iloc[0]
            else:
                return None
        elif isinstance(cal, dict):
            raw = cal.get("Earnings Date")
            if isinstance(raw, list) and raw:
                raw = raw[0]
            if raw is None:
                return None
        else:
            return None

        # Coerce to date
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        if isinstance(raw, pd.Timestamp):
            return raw.date()
        return None
    except Exception:
        return None
