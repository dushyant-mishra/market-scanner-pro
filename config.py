"""
Market Scanner V2 — Configuration
Constants, scoring weights, strategy definitions, and UI settings.
"""

# ---------------------------------------------------------------------
# Scoring weights  (must sum to 1.0)
# ---------------------------------------------------------------------
SCORING_WEIGHTS = {
    "trend": 0.25,
    "momentum": 0.15,
    "options_flow": 0.20,
    "leaps": 0.15,
    "fundamentals": 0.10,
    "sector": 0.10,
    "volume": 0.05,
}

# ---------------------------------------------------------------------
# Risk filter thresholds
# ---------------------------------------------------------------------
MIN_MARKET_CAP = 2_000_000_000          # $2 B
MIN_AVG_DAILY_VOLUME = 100_000          # shares
MIN_OPTIONS_VOLUME = 500                 # contracts
EARNINGS_PROXIMITY_DAYS = 5              # flag if earnings within N days
ATM_SPREAD_PCT_MAX = 0.10               # 10 % of mid price

# ---------------------------------------------------------------------
# Technical indicator defaults
# ---------------------------------------------------------------------
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2
ATR_PERIOD = 14
STOCH_K = 14
STOCH_D = 3

# ---------------------------------------------------------------------
# Forecast settings
# ---------------------------------------------------------------------
FORECAST_HORIZONS = [30, 90]            # trading days
FORECAST_PERCENTILES = {
    "bear": 20,
    "base": 50,
    "bull": 80,
}

# ---------------------------------------------------------------------
# Options strategies — defined-risk only for V2
# ---------------------------------------------------------------------
STRATEGIES = [
    {
        "name": "LEAPS Call",
        "direction": "bullish",
        "defined_risk": True,
        "min_dte": 180,
        "description": "Long-dated call option for long-term bullish exposure",
    },
    {
        "name": "LEAPS Put",
        "direction": "bearish",
        "defined_risk": True,
        "min_dte": 180,
        "description": "Long-dated put option for long-term bearish exposure or hedging",
    },
    {
        "name": "Call Debit Spread",
        "direction": "bullish",
        "defined_risk": True,
        "min_dte": 30,
        "description": "Buy call + sell higher call — capped risk, capped reward",
    },
    {
        "name": "Put Debit Spread",
        "direction": "bearish",
        "defined_risk": True,
        "min_dte": 30,
        "description": "Buy put + sell lower put — capped risk, capped reward",
    },
    {
        "name": "Covered Call",
        "direction": "neutral_bullish",
        "defined_risk": True,
        "min_dte": 30,
        "description": "Own shares + sell OTM call — income strategy",
    },
    {
        "name": "Cash-Secured Put",
        "direction": "neutral_bullish",
        "defined_risk": True,
        "min_dte": 30,
        "description": "Sell put backed by cash — income or entry strategy",
    },
    {
        "name": "Calendar Spread",
        "direction": "neutral",
        "defined_risk": True,
        "min_dte": 30,
        "description": "Sell near-term + buy far-term at same strike — theta play",
    },
    {
        "name": "Double Calendar",
        "direction": "neutral",
        "defined_risk": True,
        "min_dte": 30,
        "description": "Two calendar spreads at different strikes — range-bound play",
    },
    {
        "name": "Iron Condor",
        "direction": "neutral",
        "defined_risk": True,
        "min_dte": 30,
        "description": "Sell OTM put spread + OTM call spread — range-bound, high IV",
    },
    {
        "name": "Collar",
        "direction": "protective",
        "defined_risk": True,
        "min_dte": 30,
        "description": "Own shares + buy put + sell call — downside protection",
    },
]

# Direction tags for filtering
BULLISH_STRATEGIES = [s["name"] for s in STRATEGIES if "bullish" in s["direction"]]
BEARISH_STRATEGIES = [s["name"] for s in STRATEGIES if "bearish" in s["direction"]]
NEUTRAL_STRATEGIES = [s["name"] for s in STRATEGIES if "neutral" in s["direction"]]

# ---------------------------------------------------------------------
# UI color palette
# ---------------------------------------------------------------------
COLORS = {
    "bg_primary": "#0a0e17",
    "bg_secondary": "#131a2b",
    "bg_card": "#1a2332",
    "accent": "#00d4aa",
    "accent_alt": "#6366f1",
    "bullish": "#00d4aa",
    "bearish": "#ff4757",
    "neutral": "#ffa502",
    "warning": "#ff6b35",
    "text_primary": "#e0e6ed",
    "text_secondary": "#8892a0",
    "text_muted": "#4a5568",
    "border": "#2d3748",
    "chart_up": "#00d4aa",
    "chart_down": "#ff4757",
}

# Score thresholds for color coding
SCORE_THRESHOLDS = {
    "high": 70,
    "medium": 40,
    "low": 0,
}

# ---------------------------------------------------------------------
# Cache TTL (seconds)
# ---------------------------------------------------------------------
CACHE_TTL = 900  # 15 minutes

# Risk budget for option strategies (max loss proportion)
RISK_BUDGET = 0.02

# Machine learning model selection for forecasts
ML_MODEL = "custom_nn"  # options: "custom_nn", "lightgbm", "xgboost"

# ---------------------------------------------------------------------
# Default ticker list (small fast scan)

# ---------------------------------------------------------------------
# Default ticker list (small fast scan)
# ---------------------------------------------------------------------
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META",
    "GOOGL", "TSLA", "AMD", "NFLX", "AVGO",
    "COST", "CRM", "ADBE", "QCOM", "INTC",
    "JPM", "BAC", "XOM", "LLY", "UNH",
]
