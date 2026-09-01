import unittest

import numpy as np
import pandas as pd

from scoring.risk_analysis import analyze_risk, risk_adjusted_conviction


def history(returns, start=100.0, volume=1_000_000):
    prices = start * np.cumprod(1.0 + np.asarray(returns, dtype=float))
    index = pd.date_range("2024-01-01", periods=len(prices), freq="B")
    return pd.DataFrame({"Close": prices, "Volume": volume}, index=index)


class RiskAnalysisTests(unittest.TestCase):
    def test_stable_asset_has_lower_risk_than_volatile_asset(self):
        rng = np.random.default_rng(7)
        stable = history(rng.normal(0.0005, 0.006, 300))
        volatile = history(rng.normal(0.0005, 0.035, 300))
        stable_risk = analyze_risk(stable, {"beta": 0.8})
        volatile_risk = analyze_risk(volatile, {"beta": 1.6})
        self.assertTrue(stable_risk["available"])
        self.assertLess(stable_risk["risk_score"], volatile_risk["risk_score"])
        self.assertLess(stable_risk["annualized_volatility"], volatile_risk["annualized_volatility"])

    def test_drawdown_and_tail_loss_are_negative(self):
        returns = [0.002] * 60 + [-0.10, -0.08, -0.06] + [0.001] * 60
        result = analyze_risk(history(returns))
        self.assertLess(result["max_drawdown"], -0.20)
        self.assertLess(result["expected_shortfall_95_daily"], 0)
        self.assertIn("market_bear_20pct", result["stress_tests"])

    def test_insufficient_history_is_explicit(self):
        result = analyze_risk(history([0.01] * 15))
        self.assertFalse(result["available"])
        self.assertEqual(result["risk_level"], "Unknown")

    def test_risk_adjusted_conviction_penalizes_risk(self):
        low = risk_adjusted_conviction(75, 0.60, 90, 20)
        high = risk_adjusted_conviction(75, 0.60, 90, 80)
        self.assertGreater(low, high)

    def test_beta_aligns_on_dates_not_row_positions(self):
        dates = pd.date_range("2024-01-01", periods=80, freq="B")
        market_returns = np.linspace(-0.01, 0.01, 79)
        market = history(market_returns)
        market["Date"] = dates[:79]
        asset = history(market_returns[10:] * 2.0)
        asset["Date"] = dates[10:79]
        result = analyze_risk(asset, benchmark_hist=market)
        self.assertAlmostEqual(result["beta"], 2.0, places=2)

    def test_constant_losses_have_nonzero_downside_deviation(self):
        result = analyze_risk(history([-0.01] * 80))
        self.assertGreater(result["downside_deviation"], 0)

    def test_missing_volume_is_disclosed(self):
        frame = history([0.001, -0.001] * 40).drop(columns="Volume")
        result = analyze_risk(frame)
        self.assertTrue(any("liquidity" in warning.lower() for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
