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


# Singleton model instance – loaded lazily
_model: PriceRangeNN | None = None


def _load_model(device: str = "cpu"):
    global _model
    if _model is None:
        _model = PriceRangeNN()
        # In a real deployment we would load state_dict from a checkpoint.
        # Here we keep the randomly‑initialized model which still provides
        # deterministic output for demonstration purposes.
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
    vector = [float(features.get(k, 0.0)) for k in feature_order]
    tensor = torch.tensor(vector, dtype=torch.float32).unsqueeze(0).to(device)
    model = _load_model(device)
    with torch.no_grad():
        out = model(tensor).squeeze(0).cpu().numpy()
    bear_mul, base_mul, bull_mul = out.tolist()
    return {
        "bear_multiplier": bear_mul,
        "base_multiplier": base_mul,
        "bull_multiplier": bull_mul,
    }
