import pandas as pd
import numpy as np

def find_historical_lookalikes(hist: pd.DataFrame, current_features: dict, tolerance_pct: float = 0.05) -> dict:
    """
    Finds historical days where technical features matched today's features within a tolerance.
    Calculates average 30-day and 90-day forward returns for those occurrences.
    """
    default_result = {
        "lookalike_count": 0,
        "avg_30d_return": 0.0,
        "avg_90d_return": 0.0,
        "win_rate_30d": 0.0,
        "win_rate_90d": 0.0
    }
    
    if hist is None or hist.empty or len(hist) < 100:
        return default_result
        
    try:
        df = hist.copy()
        
        # Calculate features on the whole history if not present
        if "RSI" not in df.columns:
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))
            
        if "Vol20d" not in df.columns:
            df["Vol20d"] = df["Close"].pct_change().rolling(20).std() * np.sqrt(252)
            
        # Target features
        curr_rsi = current_features.get("rsi") or df["RSI"].iloc[-1]
        curr_vol = current_features.get("realized_vol_20d") or df["Vol20d"].iloc[-1]
        
        if pd.isna(curr_rsi) or pd.isna(curr_vol):
            return default_result
            
        # Define ranges
        rsi_min, rsi_max = curr_rsi * (1 - tolerance_pct), curr_rsi * (1 + tolerance_pct)
        vol_min, vol_max = curr_vol * (1 - tolerance_pct), curr_vol * (1 + tolerance_pct)
        
        # Forward returns
        df["fwd_30d"] = df["Close"].shift(-30) / df["Close"] - 1
        df["fwd_90d"] = df["Close"].shift(-90) / df["Close"] - 1
        
        # Filter for lookalikes (exclude the last 90 days as they don't have full forward returns)
        valid_history = df.iloc[:-90].dropna(subset=["RSI", "Vol20d", "fwd_30d"])
        
        matches = valid_history[
            (valid_history["RSI"] >= rsi_min) & (valid_history["RSI"] <= rsi_max) &
            (valid_history["Vol20d"] >= vol_min) & (valid_history["Vol20d"] <= vol_max)
        ]
        
        if matches.empty:
            return default_result
            
        count = len(matches)
        avg_30d = matches["fwd_30d"].mean()
        avg_90d = matches["fwd_90d"].mean()
        win_30d = (matches["fwd_30d"] > 0).mean() * 100
        win_90d = (matches["fwd_90d"] > 0).mean() * 100
        
        return {
            "lookalike_count": count,
            "avg_30d_return": float(avg_30d) if pd.notna(avg_30d) else 0.0,
            "avg_90d_return": float(avg_90d) if pd.notna(avg_90d) else 0.0,
            "win_rate_30d": float(win_30d) if pd.notna(win_30d) else 0.0,
            "win_rate_90d": float(win_90d) if pd.notna(win_90d) else 0.0
        }
        
    except Exception as e:
        print(f"Error in find_historical_lookalikes: {e}")
        return default_result
