# c:/market_scanner/ml/nn_model.py
"""
Simple custom neural network model for probabilistic price range forecasts.
The model is a lightweight feed‑forward net that takes a set of technical
features (close, moving averages, volatility, volume, RSI, etc.) and outputs
three values: bear, base and bull price multipliers relative to the current
price.

Training data can be generated from historical price series. For the
purpose of this project we provide a ``predict`` method that can be called
directly from ``scoring.forecaster`` when ``config.ML_MODEL`` == "custom_nn".
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class PriceRangeNN(nn.Module):
    """Feed‑forward network producing three price multipliers.

    Input dimension is the number of features supplied by the caller.
    The network outputs three positive scalars representing the
    relative change for bear, base and bull scenarios.
    """

    def __init__(self, input_dim: int = 12):
        super().__init__()
        hidden = 64
        self.fc1 = nn.Linear(input_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.out = nn.Linear(hidden, 3)  # bear, base, bull
        # Initialize weights for stable training
        nn.init.kaiming_uniform_(self.fc1.weight, nonlinearity="relu")
        nn.init.kaiming_uniform_(self.fc2.weight, nonlinearity="relu")
        nn.init.xavier_uniform_(self.out.weight)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        # Exponential to ensure positivity
        return torch.exp(self.out(x))


import os

# Singleton model instance – loaded lazily
_model: PriceRangeNN | None = None
_model_stats = {"X_mean": None, "X_std": None}

def _load_model(device: str = "cpu"):
    global _model, _model_stats
    if _model is None:
        _model = PriceRangeNN()
        
        # Try to load trained weights
        weights_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "nn_weights.pt")
        if os.path.exists(weights_path):
            try:
                checkpoint = torch.load(weights_path, map_location=device)
                if 'model_state_dict' in checkpoint:
                    _model.load_state_dict(checkpoint['model_state_dict'])
                    _model_stats['X_mean'] = checkpoint.get('X_mean')
                    _model_stats['X_std'] = checkpoint.get('X_std')
                else:
                    _model.load_state_dict(checkpoint) # fallback for old formats
            except Exception as e:
                print(f"Error loading model weights: {e}")
                
        _model.to(device)
        _model.eval()
    return _model


def predict(features: dict, device: str = "cpu") -> dict:
    """Predict bear / base / bull price multipliers.

    ``features`` is a mapping of numeric feature names to values. The
    function extracts the values in a deterministic order, converts them to a
    torch tensor, runs the model and returns a dictionary with keys
    ``bear_multiplier``, ``base_multiplier`` and ``bull_multiplier``.
    """
    # Define the ordering of features expected by the model. Missing keys are
    # filled with 0.0 so that the tensor has a fixed size.
    feature_order = [
        "close",
        "ma20",
        "ma50",
        "ma200",
        "realized_vol_20d",
        "realized_vol_60d",
        "avg_volume_20d",
        "avg_volume_60d",
        "rsi",
        "atr_pct",
        "iv",
        "beta",
    ]
    vector = []
    for key in feature_order:
        try:
            value = float(features.get(key, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        vector.append(value if math.isfinite(value) else 0.0)
    tensor = torch.tensor(vector, dtype=torch.float32).unsqueeze(0).to(device)
    model = _load_model(device)
    
    # Scale inputs if stats exist
    if _model_stats['X_mean'] is not None and _model_stats['X_std'] is not None:
        mean = _model_stats['X_mean'].to(device)
        std = _model_stats['X_std'].to(device)
        # Constant/near-constant training columns (currently IV and beta) do
        # not contain enough information to standardize. Dividing them by an
        # epsilon-sized std can turn an ordinary inference value into 1e8 and
        # overflow the model's exponential output.
        safe_std = torch.where(torch.abs(std) < 1e-6, torch.ones_like(std), std)
        tensor = (tensor - mean) / safe_std
        
    with torch.no_grad():
        out = model(tensor).squeeze(0).cpu().numpy()
    bear_mul, base_mul, bull_mul = out.tolist()
    multipliers = (bear_mul, base_mul, bull_mul)
    if (
        not all(math.isfinite(value) for value in multipliers)
        or not (0.05 <= bear_mul <= base_mul <= bull_mul <= 5.0)
    ):
        raise ValueError(f"Invalid neural forecast multipliers: {multipliers!r}")
    return {
        "bear_multiplier": bear_mul,
        "base_multiplier": base_mul,
        "bull_multiplier": bull_mul,
    }
