import sqlite3
import json
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = "scans_data.db"

def init_db(db_path=DB_PATH):
    """Initialize the SQLite database with the required tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table for high-level summary rows (used by the heatmap and Top 5 lists)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_summary (
            ticker TEXT PRIMARY KEY,
            last_updated TEXT,
            last_price REAL,
            bull_score REAL,
            risk_score REAL,
            confidence REAL,
            reason TEXT,
            bayesian_posterior REAL,
            bull_pct_90 REAL,
            quality_score REAL,
            sector TEXT,
            market_cap REAL
        )
    ''')
    
    # Table for the deep-dive raw data (used by the Detailed Security Report)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_raw_data (
            ticker TEXT PRIMARY KEY,
            last_updated TEXT,
            raw_json TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


def df_to_json(df):
    """Safely convert a DataFrame to JSON string."""
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return None
    if isinstance(df, pd.DataFrame):
        # Reset index to string to avoid JSON serialization errors with timestamps
        try:
            df_str = df.copy()
            df_str.index = df_str.index.astype(str)
            return df_str.to_json(orient="index")
        except:
            return None
    return None

def json_to_df(json_str):
    """Safely convert JSON string back to DataFrame."""
    if not json_str:
        return pd.DataFrame()
    try:
        df = pd.read_json(json_str, orient="index")
        # Try converting index back to datetime if possible
        try:
            df.index = pd.to_datetime(df.index)
        except:
            pass
        return df
    except:
        return pd.DataFrame()


def clean_dict_for_json(d):
    """Recursively clean dict to ensure all values are JSON serializable."""
    if isinstance(d, dict):
        return {str(k): clean_dict_for_json(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [clean_dict_for_json(i) for i in d]
    elif isinstance(d, pd.DataFrame):
        return df_to_json(d)
    elif pd.isna(d):
        return None
    else:
        # Convert numpy types to native python types
        import numpy as np
        if isinstance(d, (np.int64, np.int32)):
            return int(d)
        elif isinstance(d, (np.float64, np.float32)):
            return float(d)
        elif isinstance(d, np.bool_):
            return bool(d)
        return d


def save_stock_result(ticker, summary_dict, raw_dict, db_path=DB_PATH):
    """Save the scan results for a single stock into the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    try:
        # 1. Save Summary
        cursor.execute('''
            INSERT OR REPLACE INTO scan_summary 
            (ticker, last_updated, last_price, bull_score, risk_score, confidence, 
             reason, bayesian_posterior, bull_pct_90, quality_score, sector, market_cap)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticker,
            now,
            summary_dict.get("last_price", 0.0),
            summary_dict.get("bull_score", 0.0),
            summary_dict.get("risk_score", 0.0),
            summary_dict.get("confidence", 0.0),
            summary_dict.get("reason", ""),
            summary_dict.get("bayesian_posterior", 0.0),
            summary_dict.get("bull_pct_90", 0.0),
            summary_dict.get("quality_score", 0.0),
            summary_dict.get("sector", "Other"),
            summary_dict.get("marketCap", 0.0)
        ))
        
        # 2. Save Raw Data
        cleaned_raw = clean_dict_for_json(raw_dict)
        raw_json_str = json.dumps(cleaned_raw)
        
        cursor.execute('''
            INSERT OR REPLACE INTO scan_raw_data (ticker, last_updated, raw_json)
            VALUES (?, ?, ?)
        ''', (ticker, now, raw_json_str))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to save {ticker} to DB: {e}")
        conn.rollback()
    finally:
        conn.close()


def load_all_summaries(db_path=DB_PATH):
    """Load all summary rows from the database as a DataFrame."""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM scan_summary", conn)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Failed to load summaries: {e}")
        return pd.DataFrame()


def load_raw_data(ticker, db_path=DB_PATH):
    """Load the raw detail dictionary for a specific ticker."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT raw_json FROM scan_raw_data WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            raw_dict = json.loads(row[0])
            
            # Rehydrate DataFrames
            if "hist" in raw_dict and isinstance(raw_dict["hist"], str):
                raw_dict["hist"] = json_to_df(raw_dict["hist"])
                
            if "fundamental_results" in raw_dict and isinstance(raw_dict["fundamental_results"], dict):
                f_res = raw_dict["fundamental_results"]
                if "income_stmt" in f_res and isinstance(f_res["income_stmt"], str):
                    f_res["income_stmt"] = json_to_df(f_res["income_stmt"])
                if "balance_sheet" in f_res and isinstance(f_res["balance_sheet"], str):
                    f_res["balance_sheet"] = json_to_df(f_res["balance_sheet"])
                    
            return raw_dict
    except Exception as e:
        logger.error(f"Failed to load raw data for {ticker}: {e}")
    return {}

def get_db_stats(db_path=DB_PATH):
    """Get the total number of stocks currently cached in the DB."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scan_summary")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(last_updated) FROM scan_summary")
        last_updated = cursor.fetchone()[0]
        
        conn.close()
        return count, last_updated
    except:
        return 0, None
