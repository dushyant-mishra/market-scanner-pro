"""Fail-closed integrity checks for market price histories."""

from __future__ import annotations

import pandas as pd


def price_history_issues(hist: pd.DataFrame | None) -> list[str]:
    """Return reasons a history is unsafe for risk or forecast calculations."""
    if hist is None or not isinstance(hist, pd.DataFrame) or hist.empty or "Close" not in hist:
        return ["Price history is missing."]
    close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
    if len(close) < 30 or (close <= 0).any():
        return ["Price history has insufficient or non-positive close values."]
    returns = close.pct_change(fill_method=None).dropna()
    issues = []
    extreme = returns.abs() > 0.75
    split_like = returns.abs() > 0.40
    if extreme.any():
        issues.append(f"Detected {int(extreme.sum())} daily move(s) above 75%; corporate-action adjustment may be corrupt.")
    if int(split_like.sum()) >= 2:
        issues.append(f"Detected {int(split_like.sum())} repeated daily moves above 40%; split adjustment may be corrupt.")
    return issues
