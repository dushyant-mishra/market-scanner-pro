# c:/market_scanner/backtest/utils.py
"""Utility helpers for the backtest engine.

- Position sizing respecting a user‑defined risk budget (max loss as a proportion of capital).
- Simple risk metrics: max drawdown, win rate, total P&L.
"""

import math
from typing import Dict, List


def compute_position_size(capital: float, entry_price: float, stop_price: float, risk_budget: float) -> int:
    """Calculate the number of shares/contracts to trade.

    ``risk_budget`` is the maximum allowable loss as a fraction of ``capital``.
    The function caps the position so that the worst‑case loss (entry‑price minus stop‑price)
    does not exceed ``capital * risk_budget``.
    Returns an integer number of units (rounded down).
    """
    max_loss_allowed = capital * risk_budget
    per_share_loss = max(entry_price - stop_price, 0.000001)  # avoid division by zero
    size = math.floor(max_loss_allowed / per_share_loss)
    return max(size, 0)


def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """Return max drawdown as a percentage of the peak equity.
    """
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        drawdown = (peak - val) / peak if peak != 0 else 0.0
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd * 100.0


def compute_sortino(pnl_series: List[float], target_return: float = 0.0) -> float:
    """Calculate the Sortino ratio.

    Args:
        pnl_series: List of profit/loss values for each trade.
        target_return: Minimum acceptable return (default 0).
    Returns:
        Sortino ratio (annualized assuming daily trades, simplified).
    """
    if not pnl_series:
        return 0.0
    # Calculate downside deviation
    downside_diffs = [min(0, r - target_return) for r in pnl_series]
    downside_squared = [d ** 2 for d in downside_diffs]
    downside_dev = math.sqrt(sum(downside_squared) / len(pnl_series))
    # Average return
    avg_return = sum(pnl_series) / len(pnl_series)
    if downside_dev == 0:
        return float('inf')
    return avg_return / downside_dev

def compute_cvar(pnl_series: List[float], alpha: float = 0.05) -> float:
    """Compute Conditional Value at Risk (CVaR) at the given confidence level.

    Args:
        pnl_series: List of profit/loss values.
        alpha: Tail probability (e.g., 0.05 for 95% confidence).
    Returns:
        CVaR value (average of worst alpha% losses).
    """
    if not pnl_series:
        return 0.0
    sorted_losses = sorted(pnl_series)
    cutoff_index = int(math.ceil(alpha * len(sorted_losses)))
    worst_losses = sorted_losses[:max(1, cutoff_index)]
    return sum(worst_losses) / len(worst_losses) if worst_losses else 0.0


def summarize_trades(trades: List[Dict]) -> Dict:
    """Aggregate trade results into a summary dict.
    """
    total_pnl = sum(t.get("pnl", 0.0) for t in trades)
    wins = sum(1 for t in trades if t.get("pnl", 0.0) > 0)
    win_rate = (wins / len(trades) * 100.0) if trades else 0.0
    return {
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "trades": trades,
    }
