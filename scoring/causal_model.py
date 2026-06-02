"""
Market Scanner V3 — Causal Modeling

Runs causal inference using historical time-series data:
1. Granger Causality (time-lagged predictive power)
2. Structural Causal Model (SCM) path analysis
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Any
import statsmodels.api as sm
from statsmodels.tsa.stattools import grangercausalitytests

def calculate_returns(df: pd.DataFrame) -> pd.Series:
    """Calculate daily returns from price history."""
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    return df["Close"].pct_change().dropna()

def calculate_volume_change(df: pd.DataFrame) -> pd.Series:
    """Calculate daily volume percentage change."""
    if df.empty or "Volume" not in df.columns:
        return pd.Series(dtype=float)
    return df["Volume"].pct_change().dropna()

def run_granger_causality(data: pd.DataFrame, target: str, predictor: str, maxlag: int = 5) -> dict[str, Any]:
    """Run Granger causality test.
    data must contain target and predictor columns.
    Null hypothesis: predictor does NOT Granger-cause target.
    If p-value < 0.05, we reject null -> predictor Granger-causes target.
    """
    df = data[[target, predictor]].dropna()
    if len(df) < maxlag * 3 + 10:
        return {"is_causal": False, "min_p_value": np.nan, "best_lag": np.nan}
        
    try:
        # grangercausalitytests expects [target, predictor]
        res = grangercausalitytests(df, maxlag=maxlag, verbose=False)
        
        # Extract p-values from SSR F-test
        p_values = {lag: res[lag][0]['ssr_ftest'][1] for lag in res}
        min_p = min(p_values.values())
        best_lag = min(p_values, key=p_values.get)
        
        return {
            "is_causal": min_p < 0.05,
            "min_p_value": min_p,
            "best_lag": best_lag
        }
    except Exception:
        return {"is_causal": False, "min_p_value": np.nan, "best_lag": np.nan}

def run_causal_analysis(
    stock_df: pd.DataFrame,
    sector_df: pd.DataFrame,
    spy_df: pd.DataFrame,
    fundamental_results: dict[str, Any],
) -> dict[str, Any]:
    """
    Runs the SCM path analysis and Granger causality using stock, sector, and SPY data.
    Incorporates fundamental screener results to generate insights.
    """
    results: dict[str, Any] = {
        "scm_path": {},
        "granger": {},
        "insights": []
    }
    
    # Need sufficient data
    if stock_df.empty or spy_df.empty:
        results["insights"].append("Insufficient price history for causal analysis.")
        return results
        
    stock_ret = calculate_returns(stock_df)
    stock_vol = calculate_volume_change(stock_df)
    spy_ret = calculate_returns(spy_df)
    
    # Handle optional sector ETF
    if not sector_df.empty:
        sector_ret = calculate_returns(sector_df)
    else:
        sector_ret = spy_ret.copy() # fallback

    # Align dates
    df = pd.concat([stock_ret, stock_vol, sector_ret, spy_ret], axis=1, join="inner")
    df.columns = ["R_stock", "V_stock", "R_sector", "R_spy"]
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    
    if len(df) < 50:
        results["insights"].append("Insufficient overlapping date history for causal analysis.")
        return results

    # --- 1. SCM Path Analysis ---
    # Eq 1: R_sector = a * R_spy + e1
    try:
        X1 = sm.add_constant(df["R_spy"])
        y1 = df["R_sector"]
        model1 = sm.OLS(y1, X1).fit()
        a = model1.params["R_spy"]
        
        # Eq 2: R_stock = b * R_sector + c * R_spy + d * V_stock + e2
        X2 = sm.add_constant(df[["R_sector", "R_spy", "V_stock"]])
        y2 = df["R_stock"]
        model2 = sm.OLS(y2, X2).fit()
        b = model2.params["R_sector"]
        c = model2.params["R_spy"]
        d = model2.params["V_stock"]
        
        total_market_effect = c + (a * b)
        
        results["scm_path"] = {
            "a_spy_to_sector": a,
            "b_sector_to_stock": b,
            "c_spy_to_stock": c,
            "d_vol_to_stock": d,
            "total_market_effect": total_market_effect
        }
        
    except Exception as e:
        results["insights"].append("SCM Path estimation failed.")
        
    # --- 2. Granger Causality ---
    results["granger"]["sector_leads_stock"] = run_granger_causality(df, "R_stock", "R_sector")
    results["granger"]["spy_leads_stock"] = run_granger_causality(df, "R_stock", "R_spy")
    results["granger"]["vol_leads_stock"] = run_granger_causality(df, "R_stock", "V_stock")
    
    # --- 3. Insight Generation integrating Fundamentals ---
    quality_score = fundamental_results.get("quality_score", 0)
    
    if "total_market_effect" in results["scm_path"]:
        tme = results["scm_path"]["total_market_effect"]
        if tme > 1.2:
            results["insights"].append(f"Highly sensitive to market movements (Total Market Effect: {tme:.2f}).")
        elif tme < 0.8:
            results["insights"].append(f"Relatively insulated from broader market (Total Market Effect: {tme:.2f}).")
            
    # Combine with fundamentals
    if quality_score > 70:
        results["insights"].append(f"High Quality Score ({quality_score}%) suggests strong fundamentals can override short-term sector weakness.")
        if results["scm_path"].get("b_sector_to_stock", 0) > 0.8:
            results["insights"].append("However, stock remains heavily dependent on sector momentum.")
    elif quality_score < 40:
        results["insights"].append(f"Low Quality Score ({quality_score}%). Stock may be disproportionately punished during market downturns.")
        
    if results["granger"]["vol_leads_stock"].get("is_causal"):
        lag = results["granger"]["vol_leads_stock"]["best_lag"]
        results["insights"].append(f"Volume changes Granger-cause price movements (lag {lag} days) - strong volume indicator.")
        
    if fundamental_results.get("roic_pass") and fundamental_results.get("fwd_eps_growth_pass"):
        results["insights"].append("Strong ROIC and forward earnings growth provide a fundamental floor against volatility shocks.")

    return results
