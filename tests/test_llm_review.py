import os
import unittest
from unittest.mock import patch

from llm.multi_agent_review import build_review_context, is_available


class LLMReviewTests(unittest.TestCase):
    def test_context_contains_model_evidence_but_not_history_frame(self):
        context = build_review_context(
            "TEST",
            {
                "price_features": {"close": 10.0},
                "scores": {"bull_score": 70, "risk_analysis": {"risk_score": 30}},
                "forecast": {"forecasts": {"90": {"bear": 8, "base": 11, "bull": 14}}},
                "hist": "large object must not enter prompt",
            },
        )
        self.assertEqual(context["ticker"], "TEST")
        self.assertEqual(context["risk_analysis"]["risk_score"], 30)
        self.assertNotIn("hist", context)

    def test_api_key_gate(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_available())


if __name__ == "__main__":
    unittest.main()
