import pandas as pd
import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class BacktestRunner:
    """Run a full historical backtest across a list of tickers.

    The backtest uses the existing pipeline (fetching data, computing indicators,
    scoring, forecasting) and records equity curve, max drawdown, win rate and
    total P&L.
    """

    def __init__(self, tickers: List[str], start_date: str, end_date: str):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = 100_000.0  # default starting capital
        self.equity_curve: List[float] = []
        self.trades: List[Dict] = []
        self.capital = self.initial_capital

    def _run_single(self, ticker: str) -> Dict:
        """Run the pipeline for a single ticker and return a trade dict.

        This version respects the global RISK_BUDGET from config and uses the
        compute_position_size helper to size the position so that the worst‑case
        loss does not exceed the allowed budget.
        """
        """Run the pipeline for a single ticker and return a trade dict.

        The trade dict contains ``entry_price``, ``exit_price`` (based on the
        forecasted ``bull_price`` for the nearest horizon) and the resulting
        ``pnl``.
        """
        try:
            from data.fetcher import get_price_history, get_options_data, get_fundamentals
            from indicators.technical import calculate_all_indicators, add_indicators_to_df
            from scoring.stock_scorer import score_stock
            from scoring.options_scorer import rank_strategies
            from scoring.forecaster import forecast_price_range

            hist = get_price_history(ticker, start=self.start_date, end=self.end_date)
            if hist.empty:
                return {}
            fundamentals = get_fundamentals(ticker)
            options_data = get_options_data(ticker)
            tech = calculate_all_indicators(hist)
            price_features = {
                "close": float(hist["Close"].iloc[-1]),
                "ma20": float(hist["Close"].rolling(20).mean().iloc[-1]),
                "ma50": float(hist["Close"].rolling(50).mean().iloc[-1]),
                "ma200": float(hist["Close"].rolling(200).mean().iloc[-1]),
            }
            scores = score_stock(price_features, options_data, fundamentals, tech)
            # use the nearest horizon forecast as a proxy for exit price
            forecast = forecast_price_range(hist, tech)
            horizons = sorted(forecast.get("forecasts", {}).keys())
            if not horizons:
                return {}
            nearest = horizons[0]
            exit_price = forecast["forecasts"][nearest]["bull_price"]
            entry_price = price_features["close"]
            # Determine stop price (simple downside assumption)
            stop_price = entry_price * (1 - config.RISK_BUDGET) if config.RISK_BUDGET else entry_price * 0.95
            # Compute position size respecting risk budget
            from backtest.utils import compute_position_size
            position_size = compute_position_size(self.capital, entry_price, stop_price, config.RISK_BUDGET)
            # P&L based on full position (position_size * price change)
            pnl = (exit_price - entry_price) * position_size
            # Record additional fields for later analysis
            trade = {
                "ticker": ticker,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "position_size": position_size,
                "stop_price": stop_price,
                "strategies": rank_strategies(scores, options_data, tech, price_features),
            }
            return trade
            return {
                "ticker": ticker,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "strategies": rank_strategies(scores, options_data, tech, price_features),
            }
        except Exception as e:
            logger.debug("Backtest error for %s: %s", ticker, e)
            return {}

    def run(self) -> Dict:
        """Execute backtest across all tickers and return summary metrics."""
        total_pnl = 0.0
        wins = 0
        trades = []
        equity = self.initial_capital
        for ticker in self.tickers:
            result = self._run_single(ticker)
            if not result:
                continue
            pnl = result["pnl"]
            equity += pnl
            self.equity_curve.append(equity)
            total_pnl += pnl
            trades.append(result)
            if pnl > 0:
                wins += 1
        # Compute max drawdown using utility
        from backtest.utils import calculate_max_drawdown
        max_dd = calculate_max_drawdown(self.equity_curve)
        win_rate = (wins / len(trades) * 100) if trades else 0.0
        return {
            "total_pnl": total_pnl,
            "final_equity": equity,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "trades": trades,
        }
