"""
Market Scanner V2 — Ticker Universe & Sector Mapping

Provides hardcoded ticker lists for S&P 500, Nasdaq 100, and top liquid
options names, plus a sector map and a convenience function to retrieve
any universe by name.
"""

from __future__ import annotations

from config import DEFAULT_TICKERS

# =====================================================================
# S&P 500 Tickers  (as of mid-2026, ~503 symbols)
# Grouped alphabetically for easy maintenance.
# =====================================================================
SP500_TICKERS: list[str] = [
    # A
    "A", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI", "ADM",
    "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", "AKAM",
    "ALB", "ALGN", "ALK", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN",
    "AMP", "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH",
    "APTV", "ARE", "ATO", "ATVI", "AVB", "AVGO", "AVY", "AWK", "AXP", "AZO",
    # B
    "BA", "BAC", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF.B", "BG", "BIIB",
    "BIO", "BK", "BKNG", "BKR", "BLK", "BMY", "BR", "BRK.B", "BRO", "BSX",
    "BWA", "BXP",
    # C
    "C", "CAG", "CAH", "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL",
    "CDAY", "CDNS", "CDW", "CE", "CEG", "CF", "CFG", "CHD", "CHRW", "CHTR",
    "CI", "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS",
    "CNC", "CNP", "COF", "COO", "COP", "COST", "CPB", "CPRT", "CPT", "CRL",
    "CRM", "CSCO", "CSGP", "CSX", "CTAS", "CTLT", "CTRA", "CTSH", "CTVA",
    "CVS", "CVX",
    # D
    "D", "DAL", "DD", "DE", "DECK", "DFS", "DG", "DGX", "DHI", "DHR",
    "DIS", "DISH", "DLTR", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA",
    "DVN",
    # E
    "EA", "EBAY", "ECL", "ED", "EFX", "EIX", "EL", "EMN", "EMR", "ENPH",
    "EOG", "EPAM", "EQIX", "EQR", "EQT", "ES", "ESS", "ETN", "ETR", "ETSY",
    "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR",
    # F
    "F", "FANG", "FAST", "FBHS", "FCX", "FDS", "FDX", "FE", "FFIV", "FIS",
    "FISV", "FITB", "FLT", "FMC", "FOX", "FOXA", "FRC", "FRT",
    # G
    "GD", "GE", "GEHC", "GEN", "GILD", "GIS", "GL", "GLW", "GM", "GNRC",
    "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW",
    # H
    "HAL", "HAS", "HBAN", "HCA", "HOLX", "HON", "HPE", "HPQ",
    "HRL", "HSIC", "HST", "HSY", "HUM", "HWM",
    # I
    "IBM", "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC", "INTU",
    "INVH", "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ",
    # J
    "J", "JBHT", "JCI", "JKHY", "JNJ", "JNPR", "JPM",
    # K
    "K", "KDP", "KEY", "KEYS", "KHC", "KIM", "KLAC", "KMB", "KMI",
    "KMX", "KO", "KR",
    # L
    "L", "LDOS", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT",
    "LNC", "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV",
    # M
    "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT",
    "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST",
    "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI",
    "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU",
    # N
    "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC",
    "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWL", "NWS",
    "NWSA",
    # O
    "O", "ODFL", "OGN", "OKE", "OMC", "ON", "ORCL", "ORLY", "OTIS", "OXY",
    # P
    "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEAK", "PEG", "PEP", "PFE",
    "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PKI", "PLD", "PM", "PNC",
    "PNR", "PNW", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PVH",
    "PWR", "PXD",
    # Q
    "QCOM", "QRVO",
    # R
    "RCL", "RE", "REG", "REGN", "RF", "RHI", "RJF", "RL", "RMD", "ROK",
    "ROL", "ROP", "ROST", "RSG", "RTX",
    # S
    "SBAC", "SBNY", "SBUX", "SCHW", "SEE", "SHW", "SIVB", "SJM", "SLB",
    "SNA", "SNPS", "SO", "SPG", "SPGI", "SRE", "STE", "STT", "STX", "STZ",
    "SWK", "SWKS", "SYF", "SYK", "SYY",
    # T
    "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT",
    "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA",
    "TSN", "TT", "TTWO", "TXN", "TXT", "TYL",
    # U
    "UAL", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB",
    # V
    "V", "VFC", "VICI", "VLO", "VMC", "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ",
    # W
    "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WHR", "WM",
    "WMB", "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN",
    # X
    "XEL", "XOM", "XRAY", "XYL",
    # Y-Z
    "YUM", "ZBH", "ZBRA", "ZION", "ZTS",
]

# =====================================================================
# Nasdaq 100 Tickers
# =====================================================================
NASDAQ100_TICKERS: list[str] = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "ALGN", "AMAT",
    "AMD", "AMGN", "AMZN", "ANSS", "ARM", "ASML", "AVGO", "AZN",
    "BIIB", "BKNG", "BKR", "CDNS", "CDW", "CEG", "CHTR", "CMCSA",
    "COST", "CPRT", "CRWD", "CSCO", "CSGP", "CTAS", "CTSH", "DASH",
    "DDOG", "DLTR", "DXCM", "EA", "EBAY", "ENPH", "EXC",
    "FANG", "FAST", "FTNT", "GEHC", "GFS", "GILD", "GOOG", "GOOGL",
    "HON", "IDXX", "ILMN", "INTC", "INTU", "ISRG",
    "KDP", "KHC", "KLAC", "LRCX", "LULU",
    "MAR", "MCHP", "MDB", "MDLZ", "MELI", "META", "MNST", "MRNA",
    "MRVL", "MSFT", "MU",
    "NFLX", "NVDA",
    "ODFL", "ON", "ORLY",
    "PANW", "PAYX", "PCAR", "PDD", "PEP", "PYPL",
    "QCOM", "REGN", "RIVN", "ROST",
    "SBUX", "SIRI", "SMCI", "SNPS", "SPLK", "TEAM", "TMUS", "TSLA",
    "TTD", "TTWO", "TXN",
    "VRSK", "VRTX",
    "WBA", "WBD", "WDAY", "XEL", "ZS",
]

# =====================================================================
# Top 100 Most Actively-Traded Options Tickers
# Mega-caps, popular retail names, and high-liquidity ETFs.
# =====================================================================
TOP_LIQUID_OPTIONS: list[str] = [
    # Broad-market & sector ETFs
    "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "XLV", "XLI",
    "XLP", "XLY", "XLU", "XLRE", "XLC", "XLB", "GLD", "SLV", "TLT",
    "EEM", "HYG", "ARKK",
    # Mega-cap tech & semis
    "AAPL", "MSFT", "NVDA", "AMD", "AMZN", "META", "GOOGL", "GOOG",
    "TSLA", "AVGO", "INTC", "MU", "QCOM", "MRVL", "AMAT", "LRCX",
    "KLAC", "SNPS", "CDNS", "ARM",
    # Software & cloud
    "CRM", "ADBE", "NOW", "ORCL", "INTU", "SHOP", "SNOW", "DDOG",
    "PANW", "CRWD", "NET", "ZS", "WDAY", "PLTR",
    # Internet, media & streaming
    "NFLX", "DIS", "BKNG", "UBER", "LYFT", "ABNB", "DASH", "RBLX",
    "SNAP", "PINS",
    # Financials
    "JPM", "BAC", "GS", "MS", "C", "WFC", "SCHW", "COF",
    # Healthcare & biotech
    "UNH", "LLY", "JNJ", "PFE", "ABBV", "MRK", "BMY", "MRNA",
    "AMGN", "GILD", "REGN", "BIIB",
    # Energy
    "XOM", "CVX", "COP", "SLB", "OXY",
    # Consumer & retail
    "COST", "WMT", "TGT", "NKE", "SBUX", "MCD", "HD", "LOW",
    # Industrial & other
    "BA", "CAT", "GE", "F", "GM", "RIVN",
]

# =====================================================================
# Sector Map — ticker → GICS-style sector string
# Covers S&P 500 + major ETFs + additional liquid names.
# =====================================================================
SECTOR_MAP: dict[str, str] = {
    # --- Technology ---
    "AAPL": "Technology", "ACN": "Technology", "ADBE": "Technology",
    "ADI": "Technology", "ADP": "Technology", "ADSK": "Technology",
    "AKAM": "Technology", "AMAT": "Technology", "AMD": "Technology",
    "ANET": "Technology", "ANSS": "Technology", "APH": "Technology",
    "ARM": "Technology", "AVGO": "Technology", "BR": "Technology",
    "CDNS": "Technology", "CDW": "Technology", "CRM": "Technology",
    "CSCO": "Technology", "CSGP": "Technology", "CTSH": "Technology",
    "DDOG": "Technology", "ENPH": "Technology", "EPAM": "Technology",
    "FFIV": "Technology", "FIS": "Technology", "FISV": "Technology",
    "FLT": "Technology", "FTNT": "Technology", "GEN": "Technology",
    "GLW": "Technology", "GPN": "Technology", "HPE": "Technology",
    "HPQ": "Technology", "IBM": "Technology", "INTC": "Technology",
    "INTU": "Technology", "IT": "Technology", "JKHY": "Technology",
    "KEYS": "Technology", "KLAC": "Technology", "LRCX": "Technology",
    "MCHP": "Technology", "MPWR": "Technology", "MRVL": "Technology",
    "MSFT": "Technology", "MSI": "Technology", "MU": "Technology",
    "NET": "Technology", "NOW": "Technology", "NTAP": "Technology",
    "NVDA": "Technology", "ON": "Technology", "ORCL": "Technology",
    "PANW": "Technology", "PAYC": "Technology", "PLTR": "Technology",
    "PTC": "Technology", "QCOM": "Technology", "QRVO": "Technology",
    "SHOP": "Technology", "SMCI": "Technology", "SNOW": "Technology",
    "SNPS": "Technology", "STX": "Technology", "SWKS": "Technology",
    "TEL": "Technology", "TER": "Technology", "TRMB": "Technology",
    "TXN": "Technology", "TYL": "Technology", "VRSN": "Technology",
    "WDAY": "Technology", "WDC": "Technology", "ZBRA": "Technology",
    "ZS": "Technology", "CRWD": "Technology",
    # ETFs
    "XLK": "Technology", "QQQ": "Technology",

    # --- Healthcare ---
    "A": "Healthcare", "ABBV": "Healthcare", "ABT": "Healthcare",
    "ALGN": "Healthcare", "AMGN": "Healthcare", "BAX": "Healthcare",
    "BDX": "Healthcare", "BIIB": "Healthcare", "BIO": "Healthcare",
    "BMY": "Healthcare", "BSX": "Healthcare", "CAH": "Healthcare",
    "CI": "Healthcare", "CNC": "Healthcare", "COO": "Healthcare",
    "CRL": "Healthcare", "CTLT": "Healthcare", "CVS": "Healthcare",
    "DXCM": "Healthcare", "DVA": "Healthcare", "EW": "Healthcare",
    "GEHC": "Healthcare", "GILD": "Healthcare", "HCA": "Healthcare",
    "HOLX": "Healthcare", "HSIC": "Healthcare", "HUM": "Healthcare",
    "IDXX": "Healthcare", "ILMN": "Healthcare", "INCY": "Healthcare",
    "IQV": "Healthcare", "ISRG": "Healthcare", "JNJ": "Healthcare",
    "LH": "Healthcare", "LLY": "Healthcare", "MCK": "Healthcare",
    "MDT": "Healthcare", "MET": "Healthcare", "MOH": "Healthcare",
    "MRK": "Healthcare", "MRNA": "Healthcare", "MTD": "Healthcare",
    "PFE": "Healthcare", "PKI": "Healthcare", "REGN": "Healthcare",
    "RMD": "Healthcare", "STE": "Healthcare", "SYK": "Healthcare",
    "TECH": "Healthcare", "TFX": "Healthcare", "TMO": "Healthcare",
    "UHS": "Healthcare", "UNH": "Healthcare", "VRTX": "Healthcare",
    "WAT": "Healthcare", "WST": "Healthcare", "ZBH": "Healthcare",
    "ZTS": "Healthcare",
    # ETF
    "XLV": "Healthcare",

    # --- Financial ---
    "AFL": "Financial", "AIG": "Financial", "AIZ": "Financial",
    "AJG": "Financial", "ALL": "Financial", "AMP": "Financial",
    "AXP": "Financial", "BAC": "Financial", "BEN": "Financial",
    "BK": "Financial", "BKR": "Financial", "BLK": "Financial",
    "BRK.B": "Financial", "BRO": "Financial", "C": "Financial",
    "CB": "Financial", "CBOE": "Financial", "CFG": "Financial",
    "CINF": "Financial", "CMA": "Financial", "CME": "Financial",
    "COF": "Financial", "DFS": "Financial", "FITB": "Financial",
    "FRC": "Financial", "GL": "Financial", "GS": "Financial",
    "HBAN": "Financial", "ICE": "Financial", "IVZ": "Financial",
    "JPM": "Financial", "KEY": "Financial", "L": "Financial",
    "LNC": "Financial", "MA": "Financial", "MCO": "Financial",
    "MET": "Financial", "MKTX": "Financial", "MMC": "Financial",
    "MS": "Financial", "MSCI": "Financial", "MTB": "Financial",
    "NDAQ": "Financial", "NTRS": "Financial", "PFG": "Financial",
    "PGR": "Financial", "PNC": "Financial", "PRU": "Financial",
    "PYPL": "Financial", "RE": "Financial", "RF": "Financial",
    "RJF": "Financial", "SBNY": "Financial", "SCHW": "Financial",
    "SIVB": "Financial", "SPGI": "Financial", "STT": "Financial",
    "SYF": "Financial", "TFC": "Financial", "TROW": "Financial",
    "TRV": "Financial", "USB": "Financial", "V": "Financial",
    "WFC": "Financial", "WRB": "Financial", "ZION": "Financial",
    # ETF
    "XLF": "Financial",

    # --- Consumer Cyclical ---
    "ABNB": "Consumer Cyclical", "AMZN": "Consumer Cyclical",
    "APTV": "Consumer Cyclical", "AZO": "Consumer Cyclical",
    "BBY": "Consumer Cyclical", "BKNG": "Consumer Cyclical",
    "BWA": "Consumer Cyclical", "CCL": "Consumer Cyclical",
    "CMG": "Consumer Cyclical", "CPRT": "Consumer Cyclical",
    "CZR": "Consumer Cyclical", "DASH": "Consumer Cyclical",
    "DHI": "Consumer Cyclical", "DPZ": "Consumer Cyclical",
    "DRI": "Consumer Cyclical", "EBAY": "Consumer Cyclical",
    "ETSY": "Consumer Cyclical", "EXPE": "Consumer Cyclical",
    "F": "Consumer Cyclical", "GM": "Consumer Cyclical",
    "GRMN": "Consumer Cyclical", "HAS": "Consumer Cyclical",
    "HD": "Consumer Cyclical", "LEN": "Consumer Cyclical",
    "LOW": "Consumer Cyclical", "LULU": "Consumer Cyclical",
    "LVS": "Consumer Cyclical", "LYV": "Consumer Cyclical",
    "MAR": "Consumer Cyclical", "MCD": "Consumer Cyclical",
    "MGM": "Consumer Cyclical", "MHK": "Consumer Cyclical",
    "NCLH": "Consumer Cyclical", "NKE": "Consumer Cyclical",
    "NVR": "Consumer Cyclical", "NWL": "Consumer Cyclical",
    "ORLY": "Consumer Cyclical", "PHM": "Consumer Cyclical",
    "POOL": "Consumer Cyclical", "PVH": "Consumer Cyclical",
    "RBLX": "Consumer Cyclical", "RCL": "Consumer Cyclical",
    "RIVN": "Consumer Cyclical", "RL": "Consumer Cyclical",
    "ROST": "Consumer Cyclical", "SBUX": "Consumer Cyclical",
    "SNAP": "Consumer Cyclical", "TGT": "Consumer Cyclical",
    "TPR": "Consumer Cyclical", "TSCO": "Consumer Cyclical",
    "TSLA": "Consumer Cyclical", "TJX": "Consumer Cyclical",
    "UBER": "Consumer Cyclical", "ULTA": "Consumer Cyclical",
    "VFC": "Consumer Cyclical", "WHR": "Consumer Cyclical",
    "WYNN": "Consumer Cyclical", "YUM": "Consumer Cyclical",
    # ETF
    "XLY": "Consumer Cyclical",

    # --- Consumer Defensive ---
    "ADM": "Consumer Defensive", "BF.B": "Consumer Defensive",
    "CAG": "Consumer Defensive", "CHD": "Consumer Defensive",
    "CL": "Consumer Defensive", "CLX": "Consumer Defensive",
    "COST": "Consumer Defensive", "CPB": "Consumer Defensive",
    "EL": "Consumer Defensive", "GIS": "Consumer Defensive",
    "HRL": "Consumer Defensive", "HSY": "Consumer Defensive",
    "K": "Consumer Defensive", "KDP": "Consumer Defensive",
    "KHC": "Consumer Defensive", "KMB": "Consumer Defensive",
    "KO": "Consumer Defensive", "KR": "Consumer Defensive",
    "LW": "Consumer Defensive", "MDLZ": "Consumer Defensive",
    "MKC": "Consumer Defensive", "MNST": "Consumer Defensive",
    "MO": "Consumer Defensive", "PEP": "Consumer Defensive",
    "PG": "Consumer Defensive", "PM": "Consumer Defensive",
    "SJM": "Consumer Defensive", "STZ": "Consumer Defensive",
    "SYY": "Consumer Defensive", "TAP": "Consumer Defensive",
    "TSN": "Consumer Defensive", "WBA": "Consumer Defensive",
    "WMT": "Consumer Defensive",
    # ETF
    "XLP": "Consumer Defensive",

    # --- Industrials ---
    "AME": "Industrials", "AOS": "Industrials", "BA": "Industrials",
    "CARR": "Industrials", "CAT": "Industrials", "CDAY": "Industrials",
    "CHRW": "Industrials", "CMI": "Industrials", "CSX": "Industrials",
    "CTAS": "Industrials", "DAL": "Industrials", "DE": "Industrials",
    "DECK": "Industrials", "DOV": "Industrials", "EMR": "Industrials",
    "ETN": "Industrials", "EXPD": "Industrials", "FAST": "Industrials",
    "FDX": "Industrials", "GD": "Industrials", "GE": "Industrials",
    "GNRC": "Industrials", "GPC": "Industrials", "GWW": "Industrials",
    "HWM": "Industrials", "HON": "Industrials", "IEX": "Industrials",
    "IR": "Industrials", "ITW": "Industrials", "J": "Industrials",
    "JBHT": "Industrials", "JCI": "Industrials", "LHX": "Industrials",
    "LMT": "Industrials", "LUV": "Industrials", "MAS": "Industrials",
    "MLM": "Industrials", "MMM": "Industrials", "NDSN": "Industrials",
    "NOC": "Industrials", "NSC": "Industrials", "ODFL": "Industrials",
    "OTIS": "Industrials", "PCAR": "Industrials", "PH": "Industrials",
    "PNR": "Industrials", "PWR": "Industrials", "RHI": "Industrials",
    "ROK": "Industrials", "ROL": "Industrials", "ROP": "Industrials",
    "RSG": "Industrials", "RTX": "Industrials", "SNA": "Industrials",
    "SWK": "Industrials", "TDG": "Industrials", "TDY": "Industrials",
    "TT": "Industrials", "TXT": "Industrials", "UAL": "Industrials",
    "UNP": "Industrials", "UPS": "Industrials", "URI": "Industrials",
    "VRSK": "Industrials", "WAB": "Industrials", "WM": "Industrials",
    "XYL": "Industrials", "LDOS": "Industrials", "ALK": "Industrials",
    # ETF
    "XLI": "Industrials",

    # --- Energy ---
    "APA": "Energy", "BKR": "Energy", "COP": "Energy",
    "CTRA": "Energy", "CVX": "Energy", "DVN": "Energy",
    "EOG": "Energy", "EQT": "Energy", "FANG": "Energy",
    "HAL": "Energy", "KMI": "Energy", "MPC": "Energy",
    "MRO": "Energy", "OKE": "Energy", "OXY": "Energy",
    "PSX": "Energy", "PXD": "Energy", "SLB": "Energy",
    "TRGP": "Energy", "VLO": "Energy", "WMB": "Energy",
    "XOM": "Energy",
    # ETF
    "XLE": "Energy",

    # --- Utilities ---
    "AEE": "Utilities", "AEP": "Utilities", "AES": "Utilities",
    "ATO": "Utilities", "AWK": "Utilities", "CEG": "Utilities",
    "CMS": "Utilities", "CNP": "Utilities", "D": "Utilities",
    "DTE": "Utilities", "DUK": "Utilities", "ED": "Utilities",
    "EIX": "Utilities", "ES": "Utilities", "ETR": "Utilities",
    "EVRG": "Utilities", "EXC": "Utilities", "FE": "Utilities",
    "LNT": "Utilities", "NEE": "Utilities", "NI": "Utilities",
    "NRG": "Utilities", "PCG": "Utilities", "PEG": "Utilities",
    "PNW": "Utilities", "PPL": "Utilities", "SO": "Utilities",
    "SRE": "Utilities", "WEC": "Utilities", "XEL": "Utilities",
    # ETF
    "XLU": "Utilities",

    # --- Real Estate ---
    "AMT": "Real Estate", "ARE": "Real Estate", "AVB": "Real Estate",
    "BXP": "Real Estate", "CCI": "Real Estate", "CPT": "Real Estate",
    "DLR": "Real Estate", "EQIX": "Real Estate", "EQR": "Real Estate",
    "ESS": "Real Estate", "EXR": "Real Estate", "FRT": "Real Estate",
    "HST": "Real Estate", "INVH": "Real Estate", "IRM": "Real Estate",
    "KIM": "Real Estate", "MAA": "Real Estate", "O": "Real Estate",
    "PEAK": "Real Estate", "PLD": "Real Estate", "PSA": "Real Estate",
    "REG": "Real Estate", "SBAC": "Real Estate", "SPG": "Real Estate",
    "UDR": "Real Estate", "VICI": "Real Estate", "VTR": "Real Estate",
    "WELL": "Real Estate",
    # ETF
    "XLRE": "Real Estate",

    # --- Communication Services ---
    "ATVI": "Communication Services", "CHTR": "Communication Services",
    "CMCSA": "Communication Services", "DIS": "Communication Services",
    "DISH": "Communication Services", "EA": "Communication Services",
    "FOX": "Communication Services", "FOXA": "Communication Services",
    "GOOG": "Communication Services", "GOOGL": "Communication Services",
    "IPG": "Communication Services", "LYV": "Communication Services",
    "META": "Communication Services", "MTCH": "Communication Services",
    "NFLX": "Communication Services", "NWS": "Communication Services",
    "NWSA": "Communication Services", "OMC": "Communication Services",
    "PARA": "Communication Services", "PINS": "Communication Services",
    "T": "Communication Services", "TMUS": "Communication Services",
    "TTWO": "Communication Services", "VZ": "Communication Services",
    "WBD": "Communication Services",
    # ETF
    "XLC": "Communication Services",

    # --- Basic Materials ---
    "ALB": "Basic Materials", "AMCR": "Basic Materials",
    "APD": "Basic Materials", "AVY": "Basic Materials",
    "BG": "Basic Materials", "CE": "Basic Materials",
    "CF": "Basic Materials", "CTVA": "Basic Materials",
    "DD": "Basic Materials", "DOW": "Basic Materials",
    "ECL": "Basic Materials", "EMN": "Basic Materials",
    "FCX": "Basic Materials", "FMC": "Basic Materials",
    "IFF": "Basic Materials", "IP": "Basic Materials",
    "LIN": "Basic Materials", "LYB": "Basic Materials",
    "MLM": "Basic Materials", "MOS": "Basic Materials",
    "NEM": "Basic Materials", "NUE": "Basic Materials",
    "PKG": "Basic Materials", "PPG": "Basic Materials",
    "SEE": "Basic Materials", "SHW": "Basic Materials",
    "VMC": "Basic Materials", "WRK": "Basic Materials",
    # ETF
    "XLB": "Basic Materials",

    # --- Broad-market & other ETFs (no single sector) ---
    "SPY": "Technology",   # placeholder — ETF, not a true sector
    "IWM": "Technology",
    "DIA": "Technology",
    "GLD": "Basic Materials",
    "SLV": "Basic Materials",
    "TLT": "Financial",
    "EEM": "Technology",
    "HYG": "Financial",
    "ARKK": "Technology",
}


# =====================================================================
# Public API
# =====================================================================

def get_universe(name: str) -> list[str]:
    """Return a list of ticker symbols for the requested universe.

    Parameters
    ----------
    name : str
        One of ``'sp500'``, ``'nasdaq100'``, ``'top_liquid'``, or
        ``'default'``.

    Returns
    -------
    list[str]
        Ticker symbols belonging to the chosen universe.

    Raises
    ------
    ValueError
        If *name* is not a recognised universe identifier.
    """
    _universes: dict[str, list[str]] = {
        "sp500": SP500_TICKERS,
        "nasdaq100": NASDAQ100_TICKERS,
        "top_liquid": TOP_LIQUID_OPTIONS,
        "default": DEFAULT_TICKERS,
    }

    key = name.strip().lower()
    if key not in _universes:
        raise ValueError(
            f"Unknown universe '{name}'. "
            f"Valid options: {sorted(_universes.keys())}"
        )
    return _universes[key]


def parse_fidelity_positions_csv(file_obj) -> list[str]:
    """Parse a Fidelity positions CSV export and extract ticker symbols.

    Fidelity's CSV typically has metadata in the header and columns like 'Symbol'
    and 'Quantity'. It also lists cash/sweep vehicles (like SPAXX) and summary lines.
    """
    import pandas as pd
    from io import StringIO
    try:
        # Read the file lines to locate the header
        content = file_obj.read()
        if isinstance(content, bytes):
            try:
                decoded = content.decode("utf-8")
            except UnicodeDecodeError:
                decoded = content.decode("latin-1")
        else:
            decoded = str(content)

        lines = decoded.splitlines()

        # Find the line index containing both Symbol and Quantity
        header_idx = -1
        for idx, line in enumerate(lines):
            if "Symbol" in line and "Quantity" in line:
                header_idx = idx
                break

        if header_idx == -1:
            # Fallback: try reading the CSV directly
            file_obj.seek(0)
            df = pd.read_csv(file_obj)
        else:
            csv_data = "\n".join(lines[header_idx:])
            df = pd.read_csv(StringIO(csv_data))

        # Clean column names
        df.columns = [c.strip() for c in df.columns]

        if "Symbol" not in df.columns:
            return []

        tickers = []
        for symbol in df["Symbol"].dropna():
            sym_str = str(symbol).strip().upper()
            if not sym_str or sym_str in ["CASH", "TOTAL", "SPAXX", "FDRXX", "FCASH", "PENDING ACTIVITY"]:
                continue
            # Remove any trailing symbols like asterisks or spaces
            clean_sym = "".join(c for c in sym_str if c.isalnum() or c == "-").split("*")[0].strip()
            # Standard stock/ETF tickers are 1-5 chars long
            if clean_sym and 1 <= len(clean_sym) <= 5:
                tickers.append(clean_sym)

        return sorted(list(set(tickers)))
    except Exception:
        return []

def get_sector_etf(sector: str) -> str:
    """Return the SPDR Sector ETF ticker for a given sector name."""
    mapping = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financial": "XLF",
        "Consumer Cyclical": "XLY",
        "Consumer Defensive": "XLP",
        "Industrials": "XLI",
        "Energy": "XLE",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Communication Services": "XLC",
        "Basic Materials": "XLB"
    }
    return mapping.get(sector, "SPY")  # Fallback to SPY

