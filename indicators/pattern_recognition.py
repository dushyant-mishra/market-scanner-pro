import numpy as np
import pandas as pd
from scipy.signal import argrelextrema

def find_extrema(series: pd.Series, order: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Find local maxima and minima indices in a pandas Series."""
    if len(series) < order * 2 + 1:
        return np.array([]), np.array([])
    
    max_idx = argrelextrema(series.values, np.greater_equal, order=order)[0]
    min_idx = argrelextrema(series.values, np.less_equal, order=order)[0]
    return max_idx, min_idx

def detect_support_resistance(close: pd.Series, min_idx: np.ndarray, max_idx: np.ndarray, tolerance: float = 0.02) -> dict:
    """Detect horizontal support and resistance zones."""
    support_levels = []
    resistance_levels = []
    
    if len(min_idx) >= 2:
        min_vals = close.iloc[min_idx].values
        # Simple clustering: if two minima are within tolerance, it's a support zone
        for i in range(len(min_vals)):
            for j in range(i+1, len(min_vals)):
                if abs(min_vals[i] - min_vals[j]) / min_vals[i] <= tolerance:
                    support_levels.append(np.mean([min_vals[i], min_vals[j]]))
                    
    if len(max_idx) >= 2:
        max_vals = close.iloc[max_idx].values
        for i in range(len(max_vals)):
            for j in range(i+1, len(max_vals)):
                if abs(max_vals[i] - max_vals[j]) / max_vals[i] <= tolerance:
                    resistance_levels.append(np.mean([max_vals[i], max_vals[j]]))
                    
    return {
        "supports": sorted(list(set([round(s, 2) for s in support_levels]))),
        "resistances": sorted(list(set([round(r, 2) for r in resistance_levels])))
    }

def detect_trendline_breakout(close: pd.Series, max_idx: np.ndarray) -> bool:
    """Detect if current price breaks out of a descending trendline."""
    if len(max_idx) < 2 or len(close) < 10:
        return False
        
    # Get last two peaks
    idx2, idx1 = max_idx[-2], max_idx[-1]
    
    # Must be a downward sloping trendline
    if close.iloc[idx1] >= close.iloc[idx2] or idx1 <= idx2:
        return False
        
    # Calculate slope (dy / dx)
    slope = (close.iloc[idx1] - close.iloc[idx2]) / (idx1 - idx2)
    
    # Check if current price (last element) is above the extended line
    current_idx = len(close) - 1
    if current_idx <= idx1:
        return False
        
    projected_resistance = close.iloc[idx1] + slope * (current_idx - idx1)
    
    # Breakout logic: Previous close below, current close above
    prev_close = close.iloc[-2]
    prev_projected = close.iloc[idx1] + slope * ((current_idx - 1) - idx1)
    
    if prev_close <= prev_projected and close.iloc[-1] > projected_resistance:
        return True
    return False

def detect_double_bottom(close: pd.Series, min_idx: np.ndarray, tolerance: float = 0.02) -> bool:
    """Detect double bottom pattern."""
    if len(min_idx) < 2:
        return False
    
    idx1, idx2 = min_idx[-2], min_idx[-1]
    
    # Check if they are separated by enough time (e.g. 5 days) but not too much
    if idx2 - idx1 < 5 or idx2 - idx1 > 60:
        return False
        
    val1, val2 = close.iloc[idx1], close.iloc[idx2]
    
    if abs(val1 - val2) / val1 <= tolerance:
        # Check if price has broken above the peak between the two bottoms
        between_max = close.iloc[idx1:idx2].max()
        if close.iloc[-1] > between_max and close.iloc[-2] <= between_max:
            return True
            
    return False

def detect_gaps(close: pd.Series, high: pd.Series, low: pd.Series) -> str:
    """Detect breakaway or exhaustion gaps."""
    if len(close) < 2:
        return "none"
        
    current_low = low.iloc[-1]
    prev_high = high.iloc[-2]
    
    current_high = high.iloc[-1]
    prev_low = low.iloc[-2]
    
    if current_low > prev_high * 1.005:  # 0.5% gap up
        return "gap_up"
    elif current_high < prev_low * 0.995:
        return "gap_down"
        
    return "none"

def detect_flags(close: pd.Series, volume: pd.Series) -> bool:
    """Detect bullish flag consolidation after a sharp move."""
    if len(close) < 20:
        return False
        
    # Look for a sharp move (flagpole) in the last 15 days, e.g., > 10% up in 3-5 days
    returns_5d = close.pct_change(5)
    
    flagpole_idx = None
    for i in range(len(returns_5d)-15, len(returns_5d)-5):
        if returns_5d.iloc[i] > 0.10:
            flagpole_idx = i
            break
            
    if flagpole_idx is None:
        return False
        
    # Consolidation phase: price should slightly drift down or sideways, volume contracts
    consolidation_close = close.iloc[flagpole_idx:len(close)-1]
    if len(consolidation_close) < 3:
        return False
        
    x = np.arange(len(consolidation_close))
    slope, _ = np.polyfit(x, consolidation_close.values, 1)
    
    # Slope should be negative or slightly positive
    if slope > 0.5:
        return False
        
    # Breakout today?
    if close.iloc[-1] > consolidation_close.max():
        return True
        
    return False

def analyze_patterns(hist: pd.DataFrame) -> dict:
    """Run full Edwards & Magee analysis."""
    if hist is None or len(hist) < 50:
        return {}
        
    close = hist['Close']
    high = hist['High']
    low = hist['Low']
    volume = hist['Volume']
    
    max_idx, min_idx = find_extrema(close, order=5)
    
    supp_rest = detect_support_resistance(close, min_idx, max_idx)
    trend_breakout = detect_trendline_breakout(close, max_idx)
    double_bottom = detect_double_bottom(close, min_idx)
    gap = detect_gaps(close, high, low)
    flag = detect_flags(close, volume)
    
    # Volume check: Is today's volume > 150% of 20-day MA?
    vol_ma20 = volume.rolling(20).mean().iloc[-2] # previous day MA
    high_volume = False
    if pd.notna(vol_ma20) and vol_ma20 > 0:
        if volume.iloc[-1] > vol_ma20 * 1.5:
            high_volume = True
            
    return {
        "supports": supp_rest["supports"],
        "resistances": supp_rest["resistances"],
        "trendline_breakout": trend_breakout,
        "double_bottom": double_bottom,
        "gap": gap,
        "flag_breakout": flag,
        "high_volume_event": high_volume
    }
