import pandas as pd
import numpy as np
import datetime

def get_historical_win_rate(hist: pd.DataFrame) -> dict:
    """
    Performs a fast vectorized historical backtest on the ticker's price history.
    It identifies 'bullish' setups (Price > MA200, MACD > 0, RSI > 50) and calculates 
    the win rate 30 and 90 days later.
    """
    default_res = {
        "signal_count": 0,
        "win_rate_30d": 0.0,
        "win_rate_90d": 0.0,
        "avg_return_30d": 0.0,
        "avg_return_90d": 0.0
    }
    
    if hist is None or hist.empty or len(hist) < 250:
        return default_res
        
    try:
        df = hist.copy()
        
        # 1. Compute fast proxies for the strategy
        close = df["Close"]
        ma200 = close.rolling(200).mean()
        
        # MACD approx
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - signal
        
        # RSI approx
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Define bullish signal: Trend is up, Momentum is positive
        bullish_signal = (close > ma200) & (macd_hist > 0) & (rsi > 50) & (rsi < 70)
        
        # Shift forward to get 30d and 90d returns
        df["fwd_30d"] = close.shift(-30) / close - 1
        df["fwd_90d"] = close.shift(-90) / close - 1
        
        # Filter where signal was true
        signals_df = df[bullish_signal].copy()
        
        if signals_df.empty:
            return default_res
            
        # 30 day analysis (exclude last 30 days)
        valid_30d = signals_df.dropna(subset=["fwd_30d"])
        win_30d = (valid_30d["fwd_30d"] > 0).mean() * 100 if not valid_30d.empty else 0.0
        avg_30d = valid_30d["fwd_30d"].mean() * 100 if not valid_30d.empty else 0.0
        
        # 90 day analysis (exclude last 90 days)
        valid_90d = signals_df.dropna(subset=["fwd_90d"])
        win_90d = (valid_90d["fwd_90d"] > 0).mean() * 100 if not valid_90d.empty else 0.0
        avg_90d = valid_90d["fwd_90d"].mean() * 100 if not valid_90d.empty else 0.0
        
        return {
            "signal_count": len(signals_df),
            "win_rate_30d": float(win_30d) if pd.notna(win_30d) else 0.0,
            "win_rate_90d": float(win_90d) if pd.notna(win_90d) else 0.0,
            "avg_return_30d": float(avg_30d) if pd.notna(avg_30d) else 0.0,
            "avg_return_90d": float(avg_90d) if pd.notna(avg_90d) else 0.0
        }
        
    except Exception as e:
        print(f"Error in get_historical_win_rate: {e}")
        return default_res
