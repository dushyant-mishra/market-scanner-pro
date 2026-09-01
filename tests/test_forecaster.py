import math
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import torch

from ml import nn_model
from scoring.forecaster import _forecast_single_horizon


class NeuralForecastSafetyTests(unittest.TestCase):
    def setUp(self):
        close = pd.Series(np.linspace(80.0, 120.0, 260))
        self.close = close
        self.returns = close.pct_change().dropna()

    def test_invalid_neural_output_falls_back_to_empirical_forecast(self):
        result = _forecast_single_horizon(
            self.close,
            self.returns,
            120.0,
            90,
            20,
            50,
            80,
            "trending_up",
            {"rsi": 50},
            {
                "bear_multiplier": 0.3,
                "base_multiplier": float("inf"),
                "bull_multiplier": 0.2,
            },
        )
        self.assertIsNotNone(result)
        values = [result[f"{name}_pct"] for name in ("bear", "base", "bull")]
        self.assertTrue(all(math.isfinite(value) for value in values))
        self.assertLessEqual(values[0], values[1])
        self.assertLessEqual(values[1], values[2])

    def test_constant_feature_std_is_not_divided_by_epsilon(self):
        class CaptureModel:
            def __call__(self, tensor):
                self.tensor = tensor.detach().clone()
                return torch.tensor([[0.8, 1.0, 1.2]])

        model = CaptureModel()
        old_stats = nn_model._model_stats
        nn_model._model_stats = {
            "X_mean": torch.zeros((1, 12)),
            "X_std": torch.tensor([[1.0] * 10 + [1e-8, 1e-8]]),
        }
        try:
            with patch.object(nn_model, "_load_model", return_value=model):
                result = nn_model.predict({"iv": 0.4, "beta": 1.2})
        finally:
            nn_model._model_stats = old_stats

        self.assertEqual(result["base_multiplier"], 1.0)
        self.assertLess(float(model.tensor.abs().max()), 2.0)

    def test_predict_rejects_unordered_or_nonfinite_scenarios(self):
        class InvalidModel:
            def __call__(self, tensor):
                return torch.tensor([[0.8, float("inf"), 0.7]])

        old_stats = nn_model._model_stats
        nn_model._model_stats = {"X_mean": None, "X_std": None}
        try:
            with patch.object(nn_model, "_load_model", return_value=InvalidModel()):
                with self.assertRaisesRegex(ValueError, "Invalid neural forecast"):
                    nn_model.predict({})
        finally:
            nn_model._model_stats = old_stats


if __name__ == "__main__":
    unittest.main()
