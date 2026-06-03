"""
Overnight Headless Market Scanner (V2)

This script is designed to run overnight (or in Google Colab).
It safely loops through thousands of stocks, implements API rate limits,
and saves the heavy machine-learning and causal outputs directly to SQLite.
"""

import time
import logging
import pandas as pd
from datetime import datetime

# Import internal modules
from data import fetcher
from data.universe import SECTOR_MAP, get_sector_etf
from data.db import init_db, save_stock_result
from indicators import technical, pattern_recognition
from scoring import stock_scorer, options_scorer, forecaster, causal_model, sentiment, bayesian_inference, fundamental_screener

# Configure basic logging to terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_russell_3000_tickers():
    """
    Returns a list of ~3000 tickers.
    For this implementation, we will use a large proxy list combining S&P 500, Nasdaq 100, and standard large/mid caps.
    In a true production environment, you would scrape the iShares IWV holdings CSV here.
    """
    # Fetching a reliable large universe
    try:
        # We can pull the S&P 500 list from Wikipedia as a strong starting point
        tables = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        sp500 = tables[0]['Symbol'].tolist()
        
        # We can also add Nasdaq 100
        tables_ndx = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')
        ndx = tables_ndx[4]['Ticker'].tolist()
        
        combined = list(set(sp500 + ndx))
        # Replace '.' with '-' for Yahoo Finance (e.g., BRK.B -> BRK-B)
        combined = [t.replace('.', '-') for t in combined]
        return combined
    except Exception as e:
        logger.error(f"Failed to fetch ticker lists: {e}")
        # Fallback to a hardcoded list if internet fails
        return ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL"]

def run_nightly_scan():
    logger.info("Initializing SQLite Database...")
    init_db()
    
    tickers = get_russell_3000_tickers()
    logger.info(f"Loaded {len(tickers)} tickers for overnight scanning.")
    
    # Pre-fetch SPY for causal model
    spy_hist = fetcher.get_price_history("SPY")
    
    success_count = 0
    fail_count = 0
    
    for i, ticker in enumerate(tickers):
        logger.info(f"[{i+1}/{len(tickers)}] Scanning {ticker}...")
        
        try:
            # 1. Fetch historical price data
            hist = fetcher.get_price_history(ticker)
            if hist.empty or len(hist) < 50:
                logger.warning(f"{ticker}: Insufficient price history. Skipping.")
                fail_count += 1
                continue
            
            # 2. Fetch fundamentals and option aggregates
            fundamentals = fetcher.get_fundamentals(ticker)
            options_data = fetcher.get_options_data(ticker)
            
            income_stmt, balance_sheet = fetcher.get_financials_statements(ticker)
            
            # 3. Compute Technicals & Patterns
            tech_indicators = technical.calculate_all_indicators(hist)
            patterns = pattern_recognition.analyze_patterns(hist)
            
            last_price = float(hist["Close"].iloc[-1])
            price_features = {
                "close": last_price,
                "ma20": float(hist["Close"].rolling(20).mean().iloc[-1]),
                "ma50": float(hist["Close"].rolling(50).mean().iloc[-1]),
                "ma200": float(hist["Close"].rolling(200).mean().iloc[-1]),
                "return_20d": float(hist["Close"].pct_change(20).iloc[-1]),
                "return_60d": float(hist["Close"].pct_change(60).iloc[-1]),
                "return_120d": float(hist["Close"].pct_change(120).iloc[-1]),
                "avg_volume_20d": float(hist["Volume"].rolling(20).mean().iloc[-1]),
                "avg_volume_60d": float(hist["Volume"].rolling(60).mean().iloc[-1]),
            }
            
            # 4. Multi-Factor Scoring
            scores = stock_scorer.score_stock(price_features, options_data, fundamentals, tech_indicators)
            
            fundamental_results = fundamental_screener.run_fundamental_screen(
                fundamentals, tech_indicators, price_features, income_stmt, balance_sheet
            )
            quality_score = fundamental_results.get("quality_score", 0)
            
            numeric_confidence = float(scores.get("confidence", 30.0))
            
            strategies = options_scorer.rank_strategies(scores, options_data, tech_indicators, price_features)
            for s in strategies:
                s["score"] = s.get("suitability_score", 0.0)
            
            raw_forecast = forecaster.forecast_price_range(hist, tech_indicators)
            forecast_formatted = {}
            for h, f_data in raw_forecast.get("forecasts", {}).items():
                forecast_formatted[str(h)] = {
                    "bear": f_data.get("bear_price", 0.0),
                    "base": f_data.get("base_price", 0.0),
                    "bull": f_data.get("bull_price", 0.0),
                    "bear_pct": f_data.get("bear_pct", 0.0) * 100.0,
                    "base_pct": f_data.get("base_pct", 0.0) * 100.0,
                    "bull_pct": f_data.get("bull_pct", 0.0) * 100.0,
                    "prob_above": f_data.get("prob_above_current", 0.50) * 100.0,
                    "confidence": numeric_confidence,
                    "regime": raw_forecast.get("regime", "range_bound")
                }
            
            hist_with_ind = technical.add_indicators_to_df(hist)
            hist_with_ind["MA20"] = hist_with_ind["Close"].rolling(20).mean()
            hist_with_ind["MA50"] = hist_with_ind["Close"].rolling(50).mean()
            hist_with_ind["MA200"] = hist_with_ind["Close"].rolling(200).mean()
            
            sector = fundamentals.get("sector") or SECTOR_MAP.get(ticker, "Other")
            
            sector_etf = get_sector_etf(sector)
            sector_hist = fetcher.get_price_history(sector_etf) if sector_etf != "SPY" else pd.DataFrame()
            
            causal_results = causal_model.run_causal_analysis(
                hist_with_ind, sector_hist, spy_hist, fundamental_results
            )
            
            news_texts = fetcher.get_news(ticker)
            sentiment_data = sentiment.calculate_news_sentiment(news_texts)
            sentiment_score = sentiment_data.get("score", 0.0)
            
            bayesian_results = bayesian_inference.calculate_bayesian_conviction(
                quality_score, causal_results, patterns, sentiment_score
            )
            
            bull_pct_90 = 0.0
            if "90" in forecast_formatted:
                bull_pct_90 = forecast_formatted["90"].get("bull_pct", 0.0)
                
            # Build Summary Dict
            summary_dict = {
                "ticker": ticker,
                "last_price": last_price,
                "bull_score": scores.get("bull_score", 50.0),
                "risk_score": scores.get("risk_score", 50.0),
                "confidence": numeric_confidence,
                "reason": scores["reasons"][0] if scores.get("reasons") else "No strong signals",
                "marketCap": fundamentals.get("marketCap") or 1e9,
                "sector": sector,
                "quality_score": quality_score,
                "bayesian_posterior": bayesian_results["posterior_prob"],
                "bull_pct_90": bull_pct_90,
            }
            
            # Build Raw Details Dict
            raw_dict = {
                "price_features": price_features,
                "fundamentals": fundamentals,
                "options_data": options_data,
                "technical": tech_indicators,
                "patterns": patterns,
                "scores": scores,
                "numeric_confidence": numeric_confidence,
                "strategies": strategies,
                "forecast": {
                    "current_price": raw_forecast.get("current_price", last_price),
                    "forecasts": forecast_formatted,
                    "model_confidence": raw_forecast.get("model_confidence", "low"),
                    "regime": raw_forecast.get("regime", "range_bound")
                },
                "fundamental_results": fundamental_results,
                "causal_results": causal_results,
                "sentiment": sentiment_data,
                "bayesian_results": bayesian_results,
                "hist": hist_with_ind
            }
            
            # Commit to SQLite
            save_stock_result(ticker, summary_dict, raw_dict)
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error scanning {ticker}: {str(e)}")
            fail_count += 1
            continue
            
        # RATE LIMITING: Extremely important for Colab / Overnight scans
        # We sleep 1 second to avoid yfinance blocking our IP address
        time.sleep(1.0)
        
    logger.info(f"NIGHTLY SCAN COMPLETE. Success: {success_count}, Failed: {fail_count}")


if __name__ == "__main__":
    run_nightly_scan()
