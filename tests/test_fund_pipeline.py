import io
import unittest

from data.universe import (
    FIDELITY_ETFS,
    FIDELITY_MUTUAL_FUNDS,
    ASOX_TICKERS,
    get_asset_type,
    get_universe,
    get_index_memberships,
    parse_fidelity_fund_screener_csv,
)
from scoring.fund_analysis import analyze_fund


class FundPipelineTests(unittest.TestCase):
    def test_builtin_fidelity_universes_are_unique_and_classified(self):
        self.assertEqual(len(FIDELITY_MUTUAL_FUNDS), len(set(FIDELITY_MUTUAL_FUNDS)))
        self.assertEqual(len(FIDELITY_ETFS), len(set(FIDELITY_ETFS)))
        self.assertEqual(get_asset_type("FXAIX"), "mutual_fund")
        self.assertEqual(get_asset_type("FTEC"), "etf")
        self.assertIn("FXAIX", get_universe("fidelity_mutual_funds"))

    def test_screener_parser_supports_symbol_column_and_names(self):
        payload = io.BytesIO(b"Symbol,Name\nFXAIX,Fidelity 500 Index\n,Other Fund (FSKAX)\n")
        self.assertEqual(parse_fidelity_fund_screener_csv(payload), ["FSKAX", "FXAIX"])

    def test_asox_universe_is_explicit_and_tagged(self):
        self.assertEqual(len(ASOX_TICKERS), len(set(ASOX_TICKERS)))
        self.assertIn("NVDA", get_universe("asox"))
        self.assertIn("PHLX US AI Semiconductor (ASOX)", get_index_memberships("NVDA"))
        self.assertEqual(get_index_memberships("KO"), [])

    def test_fund_quality_rewards_low_cost_and_risk_adjusted_return(self):
        result = analyze_fund(
            {"verifiedExpenseRatio": 0.00015, "threeYearAverageReturn": 0.10, "fundFamily": "Fidelity"},
            {"sharpe_ratio": 1.2, "max_drawdown": -0.15},
            "mutual_fund",
        )
        self.assertGreater(result["quality_score"], 70)
        self.assertEqual(result["asset_type"], "mutual_fund")


if __name__ == "__main__":
    unittest.main()
