import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.nn_model import PriceRangeNN
from data.universe import get_universe
from data.fetcher import get_price_history
from indicators.technical import calculate_all_indicators

def generate_training_data(tickers, lookback_years=3, horizon_days=30):
    """
    Downloads historical data and generates X, y pairs for training.
    """
    X_list = []
    y_list = []
    
    start_date = (datetime.now() - timedelta(days=lookback_years * 365)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Generating data for {len(tickers)} tickers from {start_date} to {end_date}...")
    
    for i, ticker in enumerate(tickers):
        if i % 10 == 0:
            print(f"Processing ticker {i+1}/{len(tickers)}: {ticker}")
            
        hist = get_price_history(ticker, start=start_date, end=end_date)
        if hist.empty or len(hist) < 200 + horizon_days:
            continue
            
        close = hist["Close"]
        volume = hist["Volume"]
        daily_returns = close.pct_change()
        
        # We need technicals at each step, but calculate_all_indicators is designed for the most recent day.
        # To avoid massive loops, we'll approximate the features for the NN over a rolling window.
        
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        ma200 = close.rolling(200).mean()
        
        realized_vol_20d = daily_returns.rolling(20).std() * np.sqrt(252)
        realized_vol_60d = daily_returns.rolling(60).std() * np.sqrt(252)
        
        avg_vol_20d = volume.rolling(20).mean()
        avg_vol_60d = volume.rolling(60).mean()
        
        # Approximate RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # ATR Approx
        high_low = hist['High'] - hist['Low']
        high_close = np.abs(hist['High'] - close.shift())
        low_close = np.abs(hist['Low'] - close.shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean()
        atr_pct = (atr / close) * 100
        
        # Shift target by horizon_days
        future_returns_horizon = close.pct_change(periods=horizon_days).shift(-horizon_days)
        
        df = pd.DataFrame({
            "close": close,
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
            "realized_vol_20d": realized_vol_20d,
            "realized_vol_60d": realized_vol_60d,
            "avg_volume_20d": avg_vol_20d,
            "avg_volume_60d": avg_vol_60d,
            "rsi": rsi,
            "atr_pct": atr_pct,
            "iv": 0.0,  # Placeholder for historical IV
            "beta": 1.0, # Placeholder for historical Beta
            "future_ret": future_returns_horizon
        }).dropna()
        
        # Subsample to avoid overlapping and massive data sizes
        # Take every 5th day
        df = df.iloc[::5, :]
        
        if df.empty:
            continue
            
        # Target creation: bear/base/bull multipliers
        # In actual practice, base = mean return over horizon, etc.
        # Here we'll create proxy targets: 
        # base = actual return + 1
        # bear = actual return + 1 - volatility*sqrt(horizon/252)
        # bull = actual return + 1 + volatility*sqrt(horizon/252)
        
        vol_horizon = df["realized_vol_20d"] * np.sqrt(horizon_days / 252.0)
        
        targets = pd.DataFrame({
            "bear": (1.0 + df["future_ret"]) - vol_horizon,
            "base": (1.0 + df["future_ret"]),
            "bull": (1.0 + df["future_ret"]) + vol_horizon
        })
        
        # Ensure positivity
        targets = targets.clip(lower=0.1)
        
        X_cols = ["close", "ma20", "ma50", "ma200", "realized_vol_20d", "realized_vol_60d",
                  "avg_volume_20d", "avg_volume_60d", "rsi", "atr_pct", "iv", "beta"]
                  
        X_list.append(df[X_cols].values)
        y_list.append(targets.values)
        
    if not X_list:
        print("No valid data found.")
        return None, None
        
    X_all = np.vstack(X_list)
    y_all = np.vstack(y_list)
    return X_all, y_all

def train_model():
    print("--- Market Scanner V2 Neural Network Training ---")
    tickers = get_universe('sp500')[:50] # Limit to 50 for speed in demo
    
    X, y = generate_training_data(tickers, lookback_years=2, horizon_days=30)
    if X is None:
        return
        
    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32)
    
    # Normalize X (Simple standard scaling for the example)
    X_mean = X_tensor.mean(dim=0, keepdim=True)
    X_std = X_tensor.std(dim=0, keepdim=True) + 1e-8
    X_scaled = (X_tensor - X_mean) / X_std
    
    model = PriceRangeNN(input_dim=12)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()
    
    dataset = torch.utils.data.TensorDataset(X_scaled, y_tensor)
    loader = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)
    
    epochs = 10
    print(f"\nTraining on {len(X_tensor)} samples for {epochs} epochs...")
    model.train()
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        
        print(f"Epoch {epoch+1}/{epochs} | Loss: {epoch_loss/len(loader):.4f}")
        
    # Create models dir if not exists
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    weights_path = os.path.join(models_dir, "nn_weights.pt")
    
    # Save the model state and normalization stats
    torch.save({
        'model_state_dict': model.state_dict(),
        'X_mean': X_mean,
        'X_std': X_std
    }, weights_path)
    
    print(f"\nModel successfully trained and saved to: {weights_path}")

if __name__ == "__main__":
    train_model()
