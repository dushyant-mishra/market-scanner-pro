# Market Scanner Pro 📈

An advanced, institutional-grade stock market screening and analysis dashboard built with Python and Streamlit. 

Market Scanner Pro moves beyond standard technical indicators by fusing **Fidelity-style Fundamental Quality Scoring**, **Structural Causal Modeling**, and classic **Edwards & Magee Pattern Recognition** into a unified, mathematically rigorous **Bayesian Inference Engine**. 

![Dashboard Overview - High Upside Candidates](docs/screenshots/dashboard_overview.png)
*(Screenshot Placeholder: Add an image of the main dashboard showing the Top 5 Bayesian Candidates)*

---

## 🧠 Core Architecture

### 1. The Bayesian-Causal Inference Engine
Most screeners rely on subjective "guesswork" or basic momentum overlays. Market Scanner Pro uses **Bayes' Theorem** to calculate the mathematical probability of a massive upside breakout (e.g., +50% target).
*   **The Prior**: Establishes a strict baseline probability for a massive run in the current market environment.
*   **The Evidence**: The engine continuously updates the baseline probability based on three distinct pillars of evidence: Fundamentals, Causal Volume flow, and Classical Chart geometry.

### 2. Fidelity-Style Fundamental Scoring
Evaluates 18 rigorous financial health criteria to generate a Quality Score (0-100%).
*   **Profitability**: Return on Equity (ROE), Return on Invested Capital (ROIC), Operating Margins.
*   **Growth**: 5-Year EPS Growth, Trailing Sales Growth, Forward Projections.
*   **Valuation**: PEG Ratios, Price-to-Free-Cash-Flow.
*   **Health**: Debt-to-Equity, Current Ratio, Interest Coverage.

### 3. Structural Causal Models & Granger Causality
Moving beyond simple correlation, the tool uses **Granger Causality** (F-tests) to determine if trading volume is statistically *leading* price action (indicating hidden institutional accumulation before a breakout).

### 4. Edwards & Magee Algorithmic Pattern Recognition
We digitized the classical charting geometry from Edwards & Magee's seminal text, "Technical Analysis of Stock Trends." 
Using `scipy` local extrema detection, the engine programmatically hunts for:
*   **Support & Resistance Zones**
*   **Trendline Breakouts**
*   **Double Bottoms & Bull Flags**
*   **Breakaway Gaps**
*   **Volume Filter**: Breakouts are only statistically validated if they occur on **>150% average trading volume**.

---

## 📊 Dashboard Features

### The "Home Run" Dashboard
*   **Top 5 Highest Upside (Bayesian Conviction)**: Instantly isolates the top 5 stocks in the entire scanned universe that possess a >0% algorithmic upside target backed by the highest Bayesian probability.
*   **Multi-Factor Bullish Screen**: Ranks candidates based on a weighted composite of their momentum, trend alignment, and options flow.

![Detailed Security Report](docs/screenshots/detailed_report.png)
*(Screenshot Placeholder: Add an image of the Drill-Down tab showing the Causal Insights and Price Forecasts)*

### Detailed Security Drill-Down
Click into any ticker to view a comprehensive teardown:
*   **Probabilistic Forecasting**: 30-day and 90-day predictive targets mapping the Bear, Base, and Bull case prices.
*   **Options Strategy Recommender**: Analyzes current Implied Volatility (IV) and Put/Call skew to rank the top 10 best options strategies (e.g., Cash-Secured Puts vs. Call Debit Spreads) using a custom Radar Chart.
*   **Causal & Pattern Insights**: A live Evidence Log showing exactly *why* the Bayesian model likes the stock, including real-time Edwards & Magee pattern triggers.

---

## 🚀 Installation & Usage

### Prerequisites
*   Python 3.10+
*   `pip` or `conda`

### Running Locally
1. Clone the repository:
   ```bash
   git clone https://github.com/dushyant-mishra/market-scanner-pro.git
   cd market-scanner-pro
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the dashboard:
   ```bash
   streamlit run app.py
   ```

---
*Disclaimer: Financial markets are inherently probabilistic. Market Scanner Pro provides statistical modeling and Bayesian estimates based on historical data. It does not provide guaranteed returns or personalized financial advice.*
