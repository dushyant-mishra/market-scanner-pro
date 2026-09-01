"""Fund-specific quality overlay for mutual funds and ETFs."""

from __future__ import annotations

import math


def _number(value, default=None):
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def analyze_fund(fundamentals: dict, risk: dict, asset_type: str) -> dict:
    """Score cost, longer-term performance, and risk-adjusted behavior."""
    score = 50.0
    criteria = []
    # Yahoo's annualReportExpenseRatio is inconsistent for some Fidelity funds;
    # only score a ratio explicitly verified by a Fidelity catalog/export.
    expense = _number(fundamentals.get("verifiedExpenseRatio"))
    if expense is not None:
        if expense <= 0.0015:
            score += 20
            criteria.append({"name": "Low expense ratio", "passed": True, "value": expense})
        elif expense <= 0.005:
            score += 10
            criteria.append({"name": "Competitive expense ratio", "passed": True, "value": expense})
        elif expense >= 0.01:
            score -= 20
            criteria.append({"name": "High expense ratio", "passed": False, "value": expense})

    three_year = _number(fundamentals.get("threeYearAverageReturn"))
    five_year = _number(fundamentals.get("fiveYearAverageReturn"))
    three_year = three_year / 100 if three_year is not None and abs(three_year) > 2 else three_year
    five_year = five_year / 100 if five_year is not None and abs(five_year) > 2 else five_year
    for label, value in (("Three-year average return", three_year), ("Five-year average return", five_year)):
        if value is not None:
            score += 8 if value > 0.08 else 3 if value > 0 else -8
            criteria.append({"name": label, "passed": value > 0, "value": value})

    sharpe = _number(risk.get("sharpe_ratio"))
    drawdown = _number(risk.get("max_drawdown"))
    if sharpe is not None:
        score += 10 if sharpe >= 1 else 5 if sharpe >= 0.5 else -5 if sharpe < 0 else 0
    if drawdown is not None and drawdown <= -0.35:
        score -= 10

    return {
        "quality_score": round(min(max(score, 0.0), 100.0), 1),
        "asset_type": asset_type,
        "expense_ratio": expense,
        "fund_family": fundamentals.get("fundFamily", ""),
        "fund_category": fundamentals.get("category", ""),
        "criteria": criteria,
        "note": "Fund quality emphasizes cost and risk-adjusted history; company financial ratios do not apply.",
        "expense_ratio_note": "Expense ratio is scored only when verified from Fidelity metadata.",
    }
