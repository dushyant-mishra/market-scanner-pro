"""
Probabilistic Price Range Forecaster.

Generates bear / base / bull price targets for multiple horizons using
the historical return distribution with adjustments for trend, volatility
regime, and RSI mean-reversion.
"""

from __future__ import annotations

import logging
import math
from typing import Dict

# HMM for regime detection
from hmmlearn.hmm import GaussianHMM
import numpy as np

import numpy as np
import pandas as pd

from config import FORECAST_HORIZONS, FORECAST_PERCENTILES, ML_MODEL

logger = logging.getLogger(__name__)

_ANNUALIZATION = math.sqrt(252)
_MIN_HISTORY = 120  # minimum trading days needed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(val, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    if val is None:
        return default
    try:
        f = float(val)
        return f if f == f else default
    except (TypeError, ValueError):
        return default


class RegimeDetector:
    """Detect market regime using a Gaussian Hidden Markov Model.

    The model is trained on daily returns and categorises the market into
    three volatility‑based states: ``low``, ``medium`` and ``high``.  The
    state with the highest return variance is labelled ``high_volatility``;
    the remaining states are mapped to ``trending_up`` or ``trending_down``
    based on the sign of the mean return.
    """

    def __init__(self, n_states: int = 3):
        self.n_states = n_states
        self.model = GaussianHMM(n_components=n_states, covariance_type="diag", n_iter=1000)
        self.state_labels: list[str] = []

    def fit(self, returns: pd.Series) -> None:
        """Fit the HMM to a series of returns.

        The returns are reshaped to a 2‑D array as required by ``hmmlearn``.
        After fitting we compute a label for each hidden state based on the
        mean and standard deviation of the returns belonging to that state.
        """
        X = returns.values.reshape(-1, 1)
        self.model.fit(X)
        # Infer hidden states for the training data
        hidden_states = self.model.predict(X)
        # Gather statistics per state
        stats = []
        for s in range(self.n_states):
            mask = hidden_states == s
            mean_ret = returns[mask].mean()
            std_ret = returns[mask].std()
            stats.append({"state": s, "mean": mean_ret, "std": std_ret})
        # Sort states by volatility (std) descending
        stats.sort(key=lambda x: x["std"], reverse=True)
        # Assign labels: highest volatility -> high_volatility, then based on mean
        labels = []
        for i, st in enumerate(stats):
            if i == 0:
                labels.append("high_volatility")
            else:
                if st["mean"] >= 0:
                    labels.append("trending_up")
                else:
                    labels.append("trending_down")
        # Preserve original state order for quick lookup
        self.state_labels = ["" for _ in range(self.n_states)]
        for st, label in zip(stats, labels):
            self.state_labels[st["state"]] = label

    def predict(self, returns: pd.Series) -> str:
        """Predict the current regime from recent returns.

        The most recent return value is used to infer its hidden state, and the
        corresponding label is returned.  If the model has not been fitted yet,
        we fall back to the simple heuristic used previously.
        """
        if not self.state_labels:
            # Model not trained – use simple heuristic
            return _simple_regime_heuristic(returns)
        X = returns.values.reshape(-1, 1)
        hidden_states = self.model.predict(X)
        current_state = hidden_states[-1]
        return self.state_labels[current_state]


def _simple_regime_heuristic(daily_returns: pd.Series) -> str:
    """Fallback heuristic used when the HMM cannot be trained.

    Mirrors the original rule‑based logic for a quick default.
    """
    # Trend: price vs 200‑day MA (requires close series – we approximate using returns)
    # Since only returns are available here, we approximate volatility based regime.
    recent_vol = daily_returns.iloc[-60:].std() * _ANNUALIZATION
    long_vol = daily_returns.std() * _ANNUALIZATION
    high_vol = recent_vol > 0.35 or (long_vol > 0 and recent_vol > long_vol * 1.3)
    if high_vol:
        return "high_volatility"
    # Use mean of recent returns to infer direction
    recent_mean = daily_returns.iloc[-60:].mean()
    if recent_mean > 0.001:
        return "trending_up"
    if recent_mean < -0.001:
        return "trending_down"
    return "range_bound"

def _detect_regime(
    close: pd.Series,
    daily_returns: pd.Series,
) -> str:
    """Classify the current market regime using a multi‑state HMM.

    The function trains a temporary ``RegimeDetector`` on the provided
    ``daily_returns`` and returns the label of the most recent hidden state.
    """
    try:
        detector = RegimeDetector(n_states=3)
        detector.fit(daily_returns)
        return detector.predict(daily_returns)
    except Exception as e:
        logger.debug("Regime detection failed: %s", e)
        return _simple_regime_heuristic(daily_returns)



# ---------------------------------------------------------------------------
# Main forecast
# ---------------------------------------------------------------------------

def forecast_price_range(
    hist: pd.DataFrame,
    technical: dict,
) -> Dict[str, object]:
    """Generate forecasts using selected ML model.

    If ``ML_MODEL`` is "custom_nn", the ``ml.nn_model`` predictor is used.
    Other models are placeholders for future implementation.
    """
    """Generate probabilistic price forecasts.

    Parameters
    ----------
    hist : pd.DataFrame
        Price history with at least a ``Close`` column.
    technical : dict
        Output of ``calculate_all_indicators()``.

    Returns
    -------
    dict
        ``current_price``, ``forecasts`` (per horizon), ``model_confidence``,
        ``regime``.  Returns safe defaults on error or insufficient data.
    """
    default: Dict[str, object] = {
        "current_price": 0.0,
        "forecasts": {},
        "model_confidence": "low",
        "regime": "range_bound",
    }

    if hist is None or hist.empty or len(hist) < _MIN_HISTORY:
        return default

    try:
        close = hist["Close"].dropna()
        if len(close) < _MIN_HISTORY:
            return default

        current_price = float(close.iloc[-1])
        if current_price <= 0:
            return default

        daily_returns = close.pct_change().dropna()
        # Model prediction step (if enabled)
        if ML_MODEL == "custom_nn":
            from ml.nn_model import predict as nn_predict
            # Build feature dict for NN (use same price_features as later)
            features = {
                "close": float(close.iloc[-1]),
                "ma20": float(close.rolling(20).mean().iloc[-1]),
                "ma50": float(close.rolling(50).mean().iloc[-1]),
                "ma200": float(close.rolling(200).mean().iloc[-1]),
                "realized_vol_20d": float(daily_returns.rolling(20).std().iloc[-1] * _ANNUALIZATION),
                "realized_vol_60d": float(daily_returns.rolling(60).std().iloc[-1] * _ANNUALIZATION),
                "avg_volume_20d": 0.0,
                "avg_volume_60d": 0.0,
                "rsi": _safe(technical.get("rsi")),
                "atr_pct": _safe(technical.get("atr_pct")),
                "iv": _safe(technical.get("iv")),
                "beta": _safe(technical.get("beta")),
            }
            nn_output = nn_predict(features)
            # Overwrite base multipliers with NN predictions (optional)
            # This is a placeholder – real integration would blend forecasts.
            pass
        if daily_returns.empty:
            return default

        regime = _detect_regime(close, daily_returns)

        # ----- Build per-horizon forecasts ----------------------------
        forecasts: Dict[int, dict] = {}
        bear_pctile = FORECAST_PERCENTILES.get("bear", 20)
        base_pctile = FORECAST_PERCENTILES.get("base", 50)
        bull_pctile = FORECAST_PERCENTILES.get("bull", 80)

        for horizon in FORECAST_HORIZONS:
            horizon_forecast = _forecast_single_horizon(
                close,
                daily_returns,
                current_price,
                horizon,
                bear_pctile,
                base_pctile,
                bull_pctile,
                regime,
                technical,
            )
            if horizon_forecast is not None:
                forecasts[horizon] = horizon_forecast

        # ----- Model confidence ---------------------------------------
        data_length = len(close)
        if data_length >= 500 and len(forecasts) == len(FORECAST_HORIZONS):
            confidence = "high"
        elif data_length >= 250 and len(forecasts) >= 1:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "current_price": round(current_price, 2),
            "forecasts": forecasts,
            "model_confidence": confidence,
            "regime": regime,
        }

    except Exception:
        logger.exception("forecast_price_range failed")
        return default


# ---------------------------------------------------------------------------
# Single-horizon forecast
# ---------------------------------------------------------------------------

def _forecast_single_horizon(
    close: pd.Series,
    daily_returns: pd.Series,
    current_price: float,
    horizon: int,
    bear_pctile: float,
    base_pctile: float,
    bull_pctile: float,
    regime: str,
    technical: dict,
) -> dict | None:
    """Create forecasts for a single horizon, applying optional NN adjustments.

    ``nn_output`` (if present) could be used to adjust the raw pctiles.
    For now we keep the original calculations.
    """
    """Compute bear/base/bull forecast for one horizon."""
    try:
        # Rolling returns at the target horizon
        if len(close) < horizon + 10:
            return None

        rolling_returns = close.pct_change(periods=horizon).dropna()
        if len(rolling_returns) < 20:
            return None

        # Base percentiles from historical distribution
        bear_pct = float(np.percentile(rolling_returns, bear_pctile))
        base_pct = float(np.percentile(rolling_returns, base_pctile))
        bull_pct = float(np.percentile(rolling_returns, bull_pctile))

        # ----- Adjustments -------------------------------------------

        # 1. Trend adjustment: if price > MA200, slight bullish shift
        ma200 = close.rolling(200).mean()
        if not ma200.isna().iloc[-1]:
            if close.iloc[-1] > ma200.iloc[-1]:
                trend_adj = 0.01  # +1% bullish shift
            else:
                trend_adj = -0.01
        else:
            trend_adj = 0.0

        # 2. Volatility regime adjustment: widen range if vol is high
        recent_vol = daily_returns.iloc[-60:].std() * _ANNUALIZATION
        long_vol = daily_returns.std() * _ANNUALIZATION

        if long_vol > 0:
            vol_ratio = recent_vol / long_vol
        else:
            vol_ratio = 1.0

        vol_adj = max(vol_ratio, 0.8)  # don't narrow below 0.8×

        # 3. RSI mean-reversion adjustment
        rsi = _safe(technical.get("rsi")) if technical else 50
        rsi_adj = 0.0
        if rsi > 70:
            rsi_adj = -0.015 * ((rsi - 70) / 30)  # up to -1.5% at RSI=100
        elif rsi < 30:
            rsi_adj = 0.015 * ((30 - rsi) / 30)   # up to +1.5% at RSI=0

        # Apply adjustments
        bear_pct = bear_pct * vol_adj + trend_adj + rsi_adj
        base_pct = base_pct * vol_adj + trend_adj + rsi_adj
        bull_pct = bull_pct * vol_adj + trend_adj + rsi_adj

        # Prices
        bear_price = round(current_price * (1 + bear_pct), 2)
        base_price = round(current_price * (1 + base_pct), 2)
        bull_price = round(current_price * (1 + bull_pct), 2)

        # Probability of being above current price
        # Use simple empirical CDF at return = 0
        prob_above = float((rolling_returns > 0).sum() / len(rolling_returns))
        # Adjust with our bias terms
        prob_above = min(max(prob_above + trend_adj + rsi_adj, 0.05), 0.95)

        return {
            "bear_pct": round(bear_pct, 4),
            "base_pct": round(base_pct, 4),
            "bull_pct": round(bull_pct, 4),
            "bear_price": bear_price,
            "base_price": base_price,
            "bull_price": bull_price,
            "prob_above_current": round(prob_above, 3),
        }

    except Exception:
        logger.debug("_forecast_single_horizon failed for horizon=%d", horizon, exc_info=True)
        return None
