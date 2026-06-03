import math
import time
import numpy as np
import pandas as pd
import streamlit as st

# Import V2 modules
import config
import data.fetcher as fetcher
import data.universe as universe
import indicators.technical as technical
import scoring.stock_scorer as stock_scorer
import scoring.options_scorer as options_scorer
import scoring.forecaster as forecaster
import scoring.fundamental_screener as fundamental_screener
import scoring.causal_model as causal_model
import scoring.bayesian_inference as bayesian_inference
import indicators.pattern_recognition as pattern_recognition
import scoring.sentiment as sentiment
from backtest.engine import BacktestRunner
import ui.styles as styles
import ui.components as components
import ui.charts as charts

# -------------------------------------------------------------
# App Configuration & SEO Best Practices
# -------------------------------------------------------------
st.set_page_config(
    page_title="Market Scanner V2 — AI-Powered Stock & Options Research Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom styling
styles.inject_custom_css()

# -------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------
if "scan_df" not in st.session_state:
    st.session_state.scan_df = pd.DataFrame()
if "scan_raw" not in st.session_state:
    st.session_state.scan_raw = {}
if "scanned" not in st.session_state:
    st.session_state.scanned = False

# -------------------------------------------------------------
# Sidebar Configuration
# -------------------------------------------------------------
st.sidebar.title("Scanner Configuration")

# Universe selector
universe_names = st.sidebar.multiselect(
    "Select Ticker Universes",
    options=["Default", "S&P 500", "Nasdaq 100", "Top Options", "Fidelity Portfolio", "Custom"],
    default=["S&P 500", "Nasdaq 100"],
    key="sb_universe"
)

# Map selected universe name to get_universe keys
universe_key_map = {
    "Default": "default",
    "S&P 500": "sp500",
    "Nasdaq 100": "nasdaq100",
    "Top Options": "top_liquid",
}

default_text_list = []
for name in universe_names:
    if name == "Custom":
        pass
    elif name == "Fidelity Portfolio":
        fidelity_file = st.sidebar.file_uploader("Upload Fidelity Positions CSV", type=["csv"], key="fidelity_csv")
        if fidelity_file is not None:
            parsed_tickers = universe.parse_fidelity_positions_csv(fidelity_file)
            if parsed_tickers:
                st.sidebar.success(f"Parsed {len(parsed_tickers)} tickers from portfolio!")
                default_text_list.extend(parsed_tickers)
            else:
                st.sidebar.error("Could not parse any tickers from CSV. Please check the file format.")
        else:
            st.sidebar.info("Upload your downloaded Fidelity positions CSV to scan those tickers.")
    else:
        u_key = universe_key_map.get(name)
        if u_key:
            try:
                tickers_list = universe.get_universe(u_key)
                default_text_list.extend(tickers_list)
            except Exception:
                pass

# Remove duplicates and sort
default_text = ", ".join(sorted(list(set(default_text_list))))

tickers_input = st.sidebar.text_area(
    "Tickers to Scan (comma-separated)",
    value=default_text,
    height=150,
    key="sb_tickers_input"
)

run_scan = st.sidebar.button("Run Scan", key="sb_run_scan")

st.sidebar.markdown("---")
st.sidebar.subheader("Advanced Analysis")
run_full_fundamentals = st.sidebar.checkbox("Run Full Fundamental Screen", value=True, help="Fetches financial statements to calculate deep fundamental metrics like ROIC and Interest Coverage.")
min_quality_score = st.sidebar.slider("Minimum Quality Score (%)", 0, 100, 0, 10)

st.sidebar.markdown("---")
# Backtest toggle
enable_backtest = st.sidebar.checkbox("Enable Backtest", key="sb_backtest")
if enable_backtest:
    backtest_start = st.sidebar.date_input("Backtest Start Date", value=None)
    backtest_end = st.sidebar.date_input("Backtest End Date", value=None)
    backtest_risk_budget = st.sidebar.slider("Risk Budget (max loss %)", min_value=0, max_value=20, value=2, step=1, key="sb_risk_budget")
    backtest_intraday = st.sidebar.checkbox("Intraday Backtest", value=False, key="sb_backtest_intraday")

# -------------------------------------------------------------
# Scan Execution Pipeline
# -------------------------------------------------------------
if run_scan:
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    
    if not tickers:
        st.sidebar.error("Please enter at least one ticker.")
    else:
        st.session_state.scan_raw = {}
        rows = []
        
        progress = st.progress(0)
        status = st.empty()
        
        for i, ticker in enumerate(tickers):
            status.markdown(f"**Scanning {ticker}...** ({i+1}/{len(tickers)})")
            
            try:
                # 1. Fetch historical price data
                hist = fetcher.get_price_history(ticker)
                if hist.empty or len(hist) < 50:
                    continue
                
                # 2. Fetch fundamentals and option aggregates
                fundamentals = fetcher.get_fundamentals(ticker)
                options_data = fetcher.get_options_data(ticker)
                earnings_date = fetcher.get_earnings_date(ticker)
                
                if run_full_fundamentals:
                    income_stmt, balance_sheet = fetcher.get_financials_statements(ticker)
                else:
                    income_stmt, balance_sheet = pd.DataFrame(), pd.DataFrame()
                
                # 3. Compute indicators and format price features
                tech_indicators = technical.calculate_all_indicators(hist)
                if not tech_indicators:
                    raise ValueError("Insufficient price data for technical analysis.")
                    
                patterns = pattern_recognition.analyze_patterns(hist)
                
                last_price = float(hist["Close"].iloc[-1])
                ma20 = float(hist["Close"].rolling(20).mean().iloc[-1]) if len(hist) >= 20 else np.nan
                ma50 = float(hist["Close"].rolling(50).mean().iloc[-1]) if len(hist) >= 50 else np.nan
                ma200 = float(hist["Close"].rolling(200).mean().iloc[-1]) if len(hist) >= 200 else np.nan
                
                ret_20d = float(hist["Close"].pct_change(20).iloc[-1]) if len(hist) >= 21 else np.nan
                ret_60d = float(hist["Close"].pct_change(60).iloc[-1]) if len(hist) >= 61 else np.nan
                ret_120d = float(hist["Close"].pct_change(120).iloc[-1]) if len(hist) >= 121 else np.nan
                
                daily_returns = hist["Close"].pct_change()
                realized_vol_20d = float(daily_returns.rolling(20).std().iloc[-1] * math.sqrt(252)) if len(hist) >= 21 else np.nan
                realized_vol_60d = float(daily_returns.rolling(60).std().iloc[-1] * math.sqrt(252)) if len(hist) >= 61 else np.nan
                
                avg_volume_20d = float(hist["Volume"].rolling(20).mean().iloc[-1]) if len(hist) >= 20 else np.nan
                avg_volume_60d = float(hist["Volume"].rolling(60).mean().iloc[-1]) if len(hist) >= 60 else np.nan
                
                price_features = {
                    "close": last_price,
                    "ma20": ma20,
                    "ma50": ma50,
                    "ma200": ma200,
                    "return_20d": ret_20d,
                    "return_60d": ret_60d,
                    "return_120d": ret_120d,
                    "realized_vol_20d": realized_vol_20d,
                    "realized_vol_60d": realized_vol_60d,
                    "avg_volume_20d": avg_volume_20d,
                    "avg_volume_60d": avg_volume_60d,
                }
                
                # 4. Multi-factor Stock Scoring & Fundamentals
                scores = stock_scorer.score_stock(price_features, options_data, fundamentals, tech_indicators)
                
                fundamental_results = fundamental_screener.run_fundamental_screen(
                    fundamentals, tech_indicators, price_features, income_stmt, balance_sheet
                )
                
                quality_score = fundamental_results.get("quality_score", 0)
                if quality_score < min_quality_score:
                    continue  # Filter out tickers that fail the quality score threshold
                
                # 5. Numeric confidence mapping for gauges & components
                confidence_map = {"high": 90.0, "medium": 60.0, "low": 30.0}
                numeric_confidence = confidence_map.get(scores.get("confidence", "low"), 30.0)
                
                # 6. Evaluate option strategies and map keys
                strategies = options_scorer.rank_strategies(scores, options_data, tech_indicators, price_features)
                for s in strategies:
                    s["score"] = s.get("suitability_score", 0.0)
                
                # 7. Probabilistic Forecast mapping and scaling
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
                
                # 8. Add technical indicator columns & moving averages to hist df
                hist_with_ind = technical.add_indicators_to_df(hist)
                hist_with_ind["MA20"] = hist_with_ind["Close"].rolling(20).mean()
                hist_with_ind["MA50"] = hist_with_ind["Close"].rolling(50).mean()
                hist_with_ind["MA200"] = hist_with_ind["Close"].rolling(200).mean()
                
                sector = fundamentals.get("sector") or universe.SECTOR_MAP.get(ticker, "Other")
                
                # 9. Causal Discovery Modeling
                spy_hist = fetcher.get_price_history("SPY")
                sector_etf = universe.get_sector_etf(sector)
                sector_hist = fetcher.get_price_history(sector_etf) if sector_etf != "SPY" else pd.DataFrame()
                
                causal_results = causal_model.run_causal_analysis(
                    hist_with_ind, sector_hist, spy_hist, fundamental_results
                )
                
                # 10. NLP Sentiment Analysis
                news_texts = fetcher.get_news(ticker)
                sentiment_data = sentiment.calculate_news_sentiment(news_texts)
                sentiment_score = sentiment_data.get("score", 0.0)
                
                # 11. Bayesian Inference Integration
                bayesian_results = bayesian_inference.calculate_bayesian_conviction(
                    quality_score, causal_results, patterns, sentiment_score
                )
                
                forecasts_dict = raw_forecast.get("forecasts", {})
                bull_pct_90 = 0.0
                if 90 in forecasts_dict:
                    bull_pct_90 = forecasts_dict[90].get("bull_pct", 0.0)
                
                # Cache parsed ticker details
                st.session_state.scan_raw[ticker] = {
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
                
                # Build summary row
                rows.append({
                    "ticker": ticker,
                    "last_price": last_price,
                    "bull_score": scores.get("bull_score", 50.0),
                    "risk_score": scores.get("risk_score", 50.0),
                    "confidence": numeric_confidence,
                    "put_call_volume_ratio": options_data.get("put_call_volume_ratio", np.nan),
                    "put_call_oi_ratio": options_data.get("put_call_oi_ratio", np.nan),
                    "leaps_call_put_oi_ratio": options_data.get("leaps_call_put_oi_ratio", np.nan),
                    "iv_skew_put_minus_call": options_data.get("iv_skew_put_minus_call", np.nan),
                    "reason": scores["reasons"][0] if scores.get("reasons") else "No strong signals",
                    "marketCap": fundamentals.get("marketCap") or 1e9,
                    "sector": sector,
                    "quality_score": quality_score,
                    "bayesian_posterior": bayesian_results["posterior_prob"],
                    "bull_pct_90": bull_pct_90,
                })
                
            except Exception as e:
                st.sidebar.warning(f"Error scanning {ticker}: {str(e)}")
                continue
            
            progress.progress((i + 1) / len(tickers))
        
        status.empty()
        progress.empty()
        
        if rows:
            df = pd.DataFrame(rows)
            df = df.sort_values(by=["bull_score", "risk_score"], ascending=[False, True])
            st.session_state.scan_df = df
            st.session_state.scanned = True

            # Run backtest if enabled and dates provided
            if enable_backtest and backtest_start and backtest_end:
                bt = BacktestRunner(tickers, start_date=str(backtest_start), end_date=str(backtest_end))
                backtest_results = bt.run()
                st.session_state.backtest_results = backtest_results
        else:
            st.error("No valid results returned.")
            st.session_state.scanned = False

# -------------------------------------------------------------
# Main Dashboard Layout
# -------------------------------------------------------------
components.render_header()

if not st.session_state.scanned:
    # If backtest results exist, show summary
    if hasattr(st.session_state, 'backtest_results'):
        bt = st.session_state.backtest_results
        st.subheader("📈 Backtest Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total P&L", f"${bt['total_pnl']:.2f}")
        with col2:
            st.metric("Max Drawdown", f"{bt['max_drawdown']:.2f}%")
        with col3:
            st.metric("Win Rate", f"{bt['win_rate']:.1f}%")
        st.markdown("---")
    st.info("Enter tickers in the sidebar and click **Run Scan** to run the multi-factor V2 analysis.")
    st.info("Enter tickers in the sidebar and click **Run Scan** to run the multi-factor V2 analysis.")
else:
    scan_df = st.session_state.scan_df
    
    # 1. Sector Heatmap (rendered if 2 or more stocks exist)
    if len(scan_df) >= 2:
        heatmap_fig = charts.create_sector_heatmap(scan_df)
        st.plotly_chart(heatmap_fig, use_container_width=True)
    
    st.markdown("---")
    df = st.session_state.scan_df
    
    st.markdown("### Top Candidates")
    components.render_top5_upside_cards(df)
    st.markdown("---")
    components.render_top5_cards(df, "Top 5 Bullish (Multi-Factor)")
    st.markdown("---")
    
    # 3. Scan Results Table
    st.subheader("Full Scan Results")
    
    display_df = scan_df.copy()
    display_df["last_price"] = display_df["last_price"].map(lambda p: f"${p:,.2f}")
    display_df["bull_score"] = display_df["bull_score"].map(lambda s: f"{s:.1f}")
    display_df["risk_score"] = display_df["risk_score"].map(lambda s: f"{s:.1f}")
    display_df["confidence"] = display_df["confidence"].map(lambda c: f"{c:.0f}%")
    
    st.dataframe(
        display_df[[
            "ticker", "last_price", "quality_score", "bull_score", "risk_score", "confidence",
            "put_call_volume_ratio", "put_call_oi_ratio", "leaps_call_put_oi_ratio",
            "reason"
        ]],
        use_container_width=True,
        hide_index=True
    )
    
    st.download_button(
        "📥 Download Scan Results as CSV",
        scan_df.to_csv(index=False),
        "market_scan_results.csv",
        "text/csv",
        key="btn_download_csv"
    )
    
    st.markdown("---")
    
    # 4. Detail Security Report Drill-down
    st.subheader("Detailed Security Report")
    
    selected_ticker = st.selectbox(
        "Select Ticker to Inspect",
        options=scan_df["ticker"].tolist(),
        key="sb_detailed_ticker"
    )
    
    if selected_ticker and selected_ticker in st.session_state.scan_raw:
        details = st.session_state.scan_raw[selected_ticker]
        
        # General Info
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### {selected_ticker} — {details['fundamentals'].get('shortName', '')}")
            st.markdown(f"**Sector:** {details['fundamentals'].get('sector', 'N/A')} | **Industry:** {details['fundamentals'].get('industry', 'N/A')}")
        with col2:
            st.metric("Last Price", f"${details['price_features']['close']:,.2f}")
        with col3:
            mcap = details['fundamentals'].get('marketCap')
            mcap_str = f"${mcap/1e9:,.2f} B" if mcap and mcap >= 1e9 else f"${mcap/1e6:,.2f} M" if mcap else "N/A"
            st.metric("Market Cap", mcap_str)
            
        st.markdown(" ")
        
        tab1, tab2, tab3 = st.tabs(["Performance & Technicals", "Causal & Fundamentals", "Raw Data"])
        
        with tab1:
            # Technical Subplots & Gauges
            chart_col, score_col = st.columns([2, 1])
            
            with chart_col:
                price_fig = charts.create_price_chart(details["hist"], selected_ticker)
                st.plotly_chart(price_fig, use_container_width=True)
                
            with score_col:
                st.markdown("##### Performance Scores")
                g_col1, g_col2 = st.columns(2)
                with g_col1:
                    st.plotly_chart(
                        charts.create_score_gauge(details["scores"]["bull_score"], "Bull Score"),
                        use_container_width=True
                    )
                with g_col2:
                    st.plotly_chart(
                        charts.create_score_gauge(details["scores"]["risk_score"], "Risk Score", max_val=100),
                        use_container_width=True
                    )
                    
                st.markdown("##### Category Breakdown")
                components.render_category_breakdown(details["scores"]["category_scores"])
                
                st.markdown("##### Warnings & Risks")
                components.render_risk_warnings(details["scores"]["warnings"])
                
            st.markdown("---")
            
            # Options & Forecast Section
            opt_col, fcast_col = st.columns([1, 1])
            
            with opt_col:
                st.markdown("##### Recommended Option Strategies")
                components.render_strategy_table(details["strategies"])
                
                radar_fig = charts.create_strategy_radar(details["strategies"])
                st.plotly_chart(radar_fig, use_container_width=True)
                
            with fcast_col:
                st.markdown("##### Probabilistic Forecasts")
                components.render_forecast_card(details["forecast"]["forecasts"])
                
                fcast_fig = charts.create_forecast_chart(
                    details["forecast"]["current_price"],
                    details["forecast"]["forecasts"],
                    selected_ticker
                )
                st.plotly_chart(fcast_fig, use_container_width=True)
                
        with tab2:
            st.markdown("### Bayesian-Causal Discovery & Fundamentals")
            st.markdown("Integrates the Fidelity-style Quality Score with Structural Causal Models, Edwards & Magee Pattern Breakouts, and Bayesian Inference.")
            
            causal_col, fund_col = st.columns([1, 1])
            with causal_col:
                components.render_causal_analysis_card(
                    details.get("causal_results", {}), 
                    details.get("bayesian_results", {}),
                    details.get("patterns", {}),
                    details.get("sentiment", {})
                )
            with fund_col:
                components.render_fundamental_screen_table(details.get("fundamental_results", {}))

        with tab3:
            raw_col1, raw_col2 = st.columns(2)
            with raw_col1:
                st.markdown("**Fundamentals**")
                fund_data = {
                    "Trailing P/E": details["fundamentals"].get("trailingPE", "N/A"),
                    "Forward P/E": details["fundamentals"].get("forwardPE", "N/A"),
                    "PEG Ratio": details["fundamentals"].get("pegRatio", "N/A"),
                    "Beta": details["fundamentals"].get("beta", "N/A"),
                    "Dividend Yield": f"{details['fundamentals'].get('dividendYield', 0)*100:.2f}%" if details["fundamentals"].get("dividendYield") else "N/A",
                    "Revenue Growth": f"{details['fundamentals'].get('revenueGrowth', 0)*100:.2f}%" if details["fundamentals"].get("revenueGrowth") else "N/A",
                    "Profit Margin": f"{details['fundamentals'].get('profitMargins', 0)*100:.2f}%" if details["fundamentals"].get("profitMargins") else "N/A",
                }
                st.json(fund_data)
                
            with raw_col2:
                st.markdown("**Options Sentiment**")
                opts_data = {
                    "Put/Call Vol Ratio": details["options_data"].get("put_call_volume_ratio", "N/A"),
                    "Put/Call OI Ratio": details["options_data"].get("put_call_oi_ratio", "N/A"),
                    "LEAPS Call/Put OI Ratio": details["options_data"].get("leaps_call_put_oi_ratio", "N/A"),
                    "Avg Call IV": f"{details['options_data'].get('avg_call_iv', 0)*100:.1f}%" if details["options_data"].get("avg_call_iv") else "N/A",
                    "Avg Put IV": f"{details['options_data'].get('avg_put_iv', 0)*100:.1f}%" if details["options_data"].get("avg_put_iv") else "N/A",
                    "IV Term Structure (Near/Far)": details["options_data"].get("iv_term_structure", "N/A"),
                    "Options Liquidity Score": details["options_data"].get("options_liquidity_score", "N/A"),
                }
                st.json(opts_data)
