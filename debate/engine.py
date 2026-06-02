# c:/market_scanner/debate/engine.py
"""Simple multi‑agent debate framework for evaluating option strategies.

The engine runs three independent agents in parallel:
1. StrategyEvaluator – evaluates suitability based on existing scoring logic.
2. RiskAssessor – computes additional risk metrics (e.g., Sortino, CVaR).
3. LiquidityChecker – assesses liquidity and adds a penalty/bonus.

Each agent returns a dict of partial scores. The engine aggregates them into a
final ``suitability_score`` using weighted averaging.
"""

import concurrent.futures
from typing import List, Dict

# Import existing functions for reuse (imported locally to avoid circular dependency)


def _strategy_evaluator(strategy: dict, stock_scores: dict, options_data: dict,
                         technical: dict, price_features: dict) -> Dict:
    """Run the original evaluate_strategy and return its output."""
    from scoring.options_scorer import evaluate_strategy
    return evaluate_strategy(strategy, stock_scores, options_data, technical, price_features)


def _risk_assessor(strategy: dict, stock_scores: dict, options_data: dict,
                    technical: dict, price_features: dict) -> Dict:
    """Compute additional risk metrics (Sortino and CVaR placeholders).

    In a full implementation these would be calculated from backtest results.
    Here we provide deterministic dummy values for demonstration.
    """
    # Dummy metrics – in practice replace with real calculations.
    sortino = 1.2  # placeholder
    cvar = -0.8    # placeholder (negative means loss)
    # Combine into a simple risk adjustment factor
    risk_adj = max(0.0, 1.0 - (abs(sortino) + abs(cvar)) / 2.0)
    return {"risk_adj": risk_adj, "sortino": sortino, "cvar": cvar}


def _liquidity_checker(strategy: dict, stock_scores: dict, options_data: dict,
                       technical: dict, price_features: dict) -> Dict:
    """Assess liquidity using the existing liquidity fit function."""
    from scoring.options_scorer import _score_liquidity_fit as liquidity_fit
    total_volume = (_safe(options_data.get("total_call_volume"), 0) +
                    _safe(options_data.get("total_put_volume"), 0))
    total_oi = (_safe(options_data.get("total_call_oi"), 0) +
                _safe(options_data.get("total_put_oi"), 0))
    liq_score = liquidity_fit(total_volume, total_oi)
    return {"liquidity_score": liq_score}


def _safe(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return f if f == f else default
    except (TypeError, ValueError):
        return default


def debate_strategy(strategy: dict, stock_scores: dict, options_data: dict,
                    technical: dict, price_features: dict) -> Dict:
    """Run the three agents in parallel and aggregate results.

    The final ``suitability_score`` is a weighted blend:
        0.5 * original suitability
        0.3 * risk_adj (scaled to 0‑10)
        0.2 * liquidity_score (scaled to 0‑10)
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_eval = executor.submit(_strategy_evaluator, strategy, stock_scores,
                                      options_data, technical, price_features)
        future_risk = executor.submit(_risk_assessor, strategy, stock_scores,
                                      options_data, technical, price_features)
        future_liq = executor.submit(_liquidity_checker, strategy, stock_scores,
                                      options_data, technical, price_features)
        eval_res = future_eval.result()
        risk_res = future_risk.result()
        liq_res = future_liq.result()

    # Original suitability (0‑10)
    base_score = eval_res.get("suitability_score", 0.0)
    # Scale risk_adj (0‑1) to 0‑10
    risk_adj_score = risk_res.get("risk_adj", 0.0) * 10.0
    # Liquidity score already 0‑10
    liq_score = liq_res.get("liquidity_score", 0.0)

    final_score = (0.5 * base_score) + (0.3 * risk_adj_score) + (0.2 * liq_score)
    final_score = max(0.0, min(10.0, final_score))

    # Merge all fields into a single result dict
    result = eval_res.copy()
    result.update({
        "suitability_score": round(final_score, 1),
        "risk_adj": risk_res.get("risk_adj"),
        "sortino": risk_res.get("sortino"),
        "cvar": risk_res.get("cvar"),
        "liquidity_score": liq_score,
    })
    return result
