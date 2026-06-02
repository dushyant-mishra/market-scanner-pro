import textwrap
import streamlit as st


def inject_custom_css() -> None:
    """Inject custom CSS for the market scanner dashboard."""
    css_content = """
            <style>
            /* =============================================================
               0. GLOBAL RESETS & TRANSITIONS
               ============================================================= */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

            /* Apply Inter globally without matching broad wildcards that break Streamlit's layouts */
            html, body, .stMarkdown, .stText, .stButton, .stSelectbox, .stTextInput, .stTextArea, .stDataFrame, .stMetric, .score-badge, .metric-card, .strategy-table, .forecast-card, p, h1, h2, h3, h4, h5, h6, table, th, td {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            }

            /* Apply transitions specifically to interactive elements, not globally (*) as it conflicts with Streamlit resize calculations */
            .score-badge, .metric-card, .strategy-table tbody tr {
                transition: all 0.2s ease;
            }

            /* Hide Streamlit default hamburger menu & footer */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header[data-testid="stHeader"] {background: transparent;}

            /* Custom scrollbar */
            ::-webkit-scrollbar {
                width: 6px;
                height: 6px;
            }
            ::-webkit-scrollbar-track {
                background: #0a0e17;
            }
            ::-webkit-scrollbar-thumb {
                background: #2d3748;
                border-radius: 3px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #4a5568;
            }

            /* =============================================================
               1. SCORE BADGES
               ============================================================= */
            .score-badge {
                display: inline-block;
                padding: 4px 14px;
                border-radius: 999px;
                font-weight: 700;
                font-size: 0.85rem;
                letter-spacing: 0.3px;
                text-align: center;
                line-height: 1.4;
            }

            .score-high {
                background: rgba(0, 212, 170, 0.15);
                border: 1px solid rgba(0, 212, 170, 0.45);
                color: #00d4aa;
                box-shadow: 0 0 8px rgba(0, 212, 170, 0.15);
            }

            .score-medium {
                background: rgba(255, 165, 2, 0.15);
                border: 1px solid rgba(255, 165, 2, 0.45);
                color: #ffa502;
                box-shadow: 0 0 8px rgba(255, 165, 2, 0.15);
            }

            .score-low {
                background: rgba(255, 71, 87, 0.15);
                border: 1px solid rgba(255, 71, 87, 0.45);
                color: #ff4757;
                box-shadow: 0 0 8px rgba(255, 71, 87, 0.15);
            }

            /* =============================================================
               2. METRIC CARDS
               ============================================================= */
            .metric-card {
                background: #1a2332;
                border-radius: 12px;
                border: 1px solid #2d3748;
                padding: 1.2rem;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
                backdrop-filter: blur(8px);
                position: relative;
                overflow: hidden;
            }

            .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(90deg, transparent, #00d4aa, transparent);
                opacity: 0.4;
            }

            .metric-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(0, 212, 170, 0.12);
                border-color: rgba(0, 212, 170, 0.25);
            }

            .metric-card h3 {
                font-size: 0.85rem;
                color: #8892a0;
                margin: 0 0 0.4rem 0;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .metric-card .value {
                font-size: 1.8rem;
                font-weight: 700;
                color: #ffffff;
                line-height: 1.2;
                margin-bottom: 0.3rem;
            }

            .metric-card .delta-positive {
                color: #00d4aa;
                font-weight: 600;
                font-size: 0.9rem;
            }

            .metric-card .delta-negative {
                color: #ff4757;
                font-weight: 600;
                font-size: 0.9rem;
            }

            .metric-card .ticker-name {
                font-size: 1.3rem;
                font-weight: 700;
                color: #ffffff;
                margin-bottom: 0.5rem;
            }

            .metric-card .score-row {
                display: flex;
                gap: 8px 8px;
                align-items: center;
                margin: 0.6rem 0;
                flex-wrap: wrap;
            }

            .metric-card .reason-list {
                margin: 0.6rem 0 0 0;
                padding-left: 1rem;
                color: #8892a0;
                font-size: 0.8rem;
                line-height: 1.5;
            }

            .metric-card .reason-list li {
                margin-bottom: 2px;
            }

            /* =============================================================
               3. TOP-STOCK GLOW ANIMATION
               ============================================================= */
            @keyframes pulse-glow {
                0%   { box-shadow: 0 0 8px rgba(0, 212, 170, 0.2),  inset 0 0 8px rgba(0, 212, 170, 0.05); }
                50%  { box-shadow: 0 0 20px rgba(0, 212, 170, 0.45), inset 0 0 12px rgba(0, 212, 170, 0.1); }
                100% { box-shadow: 0 0 8px rgba(0, 212, 170, 0.2),  inset 0 0 8px rgba(0, 212, 170, 0.05); }
            }

            .top-stock {
                animation: pulse-glow 2s ease-in-out infinite;
                border-color: rgba(0, 212, 170, 0.5) !important;
            }

            .top-stock::before {
                opacity: 0.8 !important;
            }

            /* =============================================================
               4. STRATEGY TABLE
               ============================================================= */
            .table-container {
                width: 100%;
                overflow-x: auto;
                border-radius: 10px;
                border: 1px solid #2d3748;
                background: #1a2332;
                margin: 0.5rem 0 1rem 0;
            }

            .strategy-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                overflow: hidden;
                font-size: 0.82rem;
            }

            .strategy-table thead th {
                background: #131a2b;
                color: #8892a0;
                padding: 10px 12px;
                text-align: left;
                font-weight: 600;
                text-transform: uppercase;
                font-size: 0.72rem;
                letter-spacing: 0.5px;
                border-bottom: 2px solid #2d3748;
            }

            .strategy-table tbody tr:nth-child(odd) {
                background: rgba(26, 35, 50, 0.6);
            }

            .strategy-table tbody tr:nth-child(even) {
                background: rgba(19, 26, 43, 0.5);
            }

            .strategy-table tbody tr:hover {
                background: rgba(0, 212, 170, 0.06);
            }

            .strategy-table tbody td {
                padding: 8px 12px;
                color: #e0e6ed;
                border-bottom: 1px solid rgba(45, 55, 72, 0.4);
                white-space: nowrap;
            }

            .strategy-table tbody td:last-child {
                white-space: normal; /* Allow risk warning column to wrap if needed */
            }

            .strategy-table .highlight-row {
                background: rgba(0, 212, 170, 0.08) !important;
                border-left: 3px solid #00d4aa;
            }

            /* =============================================================
               5. HEADER AREA
               ============================================================= */
            .app-header {
                background: linear-gradient(180deg, #131a2b 0%, transparent 100%);
                padding: 1.5rem 0 1rem 0;
                margin-bottom: 1rem;
            }

            .app-header h1 {
                font-size: 2rem;
                font-weight: 800;
                color: #ffffff;
                margin: 0;
                letter-spacing: -0.5px;
            }

            .app-subtitle {
                color: #8892a0;
                font-size: 0.95rem;
                margin: 0.25rem 0 0.5rem 0;
                font-weight: 400;
            }

            .app-disclaimer {
                color: #4a5568;
                font-size: 0.75rem;
                font-style: italic;
                margin-top: 0.25rem;
            }

            /* =============================================================
               6. STREAMLIT TAB STYLING
               ============================================================= */
            .stTabs [data-baseweb="tab-list"] {
                gap: 0;
                border-bottom: 1px solid #2d3748;
            }

            .stTabs [data-baseweb="tab"] {
                padding: 10px 24px;
                color: #8892a0;
                font-weight: 500;
                border-bottom: 2px solid transparent;
            }

            .stTabs [data-baseweb="tab"]:hover {
                color: #e0e6ed;
            }

            .stTabs [aria-selected="true"] {
                color: #00d4aa !important;
                border-bottom: 2px solid #00d4aa !important;
                background: transparent !important;
            }

            /* =============================================================
               7. RISK / WARNING ALERTS
               ============================================================= */
            .risk-warning {
                background: rgba(255, 107, 53, 0.1);
                border-left: 3px solid #ff6b35;
                border-radius: 6px;
                padding: 10px 14px;
                margin: 6px 0;
                color: #ffa502;
                font-size: 0.85rem;
                line-height: 1.45;
            }

            /* =============================================================
               8. FORECAST CARDS & TOP5 RESPONSIVENESS
               ============================================================= */
            .forecast-card {
                background: #1a2332;
                border-radius: 10px;
                border: 1px solid #2d3748;
                padding: 1rem !important;
                min-width: 0;
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            }

            .forecast-card .horizon-title {
                font-size: 0.85rem !important;
                color: #8892a0;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.4px;
                margin-bottom: 0.5rem !important;
            }

            .forecast-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 4px;
                padding: 4px 0 !important;
                border-bottom: 1px solid rgba(45, 55, 72, 0.3);
            }

            .forecast-row:last-child {
                border-bottom: none;
            }

            .forecast-label {
                font-size: 0.78rem !important;
                font-weight: 600;
            }

            .forecast-value {
                font-size: 0.82rem !important;
                font-weight: 700;
                color: #ffffff;
            }

            .forecast-delta {
                font-size: 0.72rem !important;
                margin-left: 4px !important;
            }

            /* Responsive overrides for Top 5 Bullish candidates in narrow columns */
            .top5-card {
                padding: 1rem !important;
                min-width: 0;
                height: 100%;
                display: flex;
                flex-direction: column;
            }

            .top5-card .ticker-name {
                font-size: 1.1rem !important;
                margin-bottom: 0.3rem !important;
            }

            .top5-card .value {
                font-size: 1.2rem !important;
                margin-bottom: 0.2rem !important;
            }

            .top5-card .score-row {
                margin: 0.4rem 0 !important;
                gap: 6px !important;
            }

            .top5-card .score-badge {
                padding: 2px 8px !important;
                font-size: 0.75rem !important;
            }

            /* =============================================================
               9. PROGRESS BARS (Category Breakdown)
               ============================================================= */
            .category-bar-container {
                margin: 6px 0;
            }

            .category-bar-label {
                display: flex;
                justify-content: space-between;
                font-size: 0.82rem;
                color: #8892a0;
                margin-bottom: 3px;
            }

            .category-bar-track {
                width: 100%;
                height: 8px;
                background: rgba(45, 55, 72, 0.5);
                border-radius: 4px;
                overflow: hidden;
            }

            .category-bar-fill {
                height: 100%;
                border-radius: 4px;
                transition: width 0.6s ease;
            }

            /* =============================================================
               10. MISC UTILITIES
               ============================================================= */
            .text-green  { color: #00d4aa; }
            .text-red    { color: #ff4757; }
            .text-yellow { color: #ffa502; }
            .text-muted  { color: #4a5568; }
            .text-secondary { color: #8892a0; }
            .fw-bold { font-weight: 700; }

            .flex-row {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .confidence-bar {
                display: inline-block;
                height: 6px;
                border-radius: 3px;
                background: linear-gradient(90deg, #ff4757 0%, #ffa502 50%, #00d4aa 100%);
                opacity: 0.8;
            }
            </style>
    """
    clean_css = " ".join(line.strip() for line in css_content.splitlines() if line.strip())
    st.markdown(clean_css, unsafe_allow_html=True)
