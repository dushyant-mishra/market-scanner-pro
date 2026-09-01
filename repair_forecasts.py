"""Repair stored forecasts from price histories already embedded in a scan DB."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sqlite3

import pandas as pd

from scoring.forecaster import forecast_price_range


def _history_frame(value: object) -> pd.DataFrame:
    if not isinstance(value, str):
        return pd.DataFrame()
    payload = json.loads(value)
    frame = pd.DataFrame.from_dict(payload, orient="index")
    if "Date" in frame:
        frame["Date"] = pd.to_datetime(frame["Date"], unit="ms", errors="coerce")
        frame = frame.set_index("Date")
    return frame.sort_index()


def _format_forecast(result: dict, confidence: float) -> dict:
    formatted = {}
    for horizon, values in result.get("forecasts", {}).items():
        formatted[str(horizon)] = {
            "bear": values.get("bear_price", 0.0),
            "base": values.get("base_price", 0.0),
            "bull": values.get("bull_price", 0.0),
            "bear_pct": values.get("bear_pct", 0.0) * 100.0,
            "base_pct": values.get("base_pct", 0.0) * 100.0,
            "bull_pct": values.get("bull_pct", 0.0) * 100.0,
            "prob_above": values.get("prob_above_current", 0.5) * 100.0,
            "confidence": confidence,
            "regime": result.get("regime", "range_bound"),
        }
    return {
        "current_price": result.get("current_price", 0.0),
        "forecasts": formatted,
        "model_confidence": result.get("model_confidence", "low"),
        "regime": result.get("regime", "range_bound"),
    }


def repair_database(db_path: Path, backup_path: Path | None = None) -> tuple[int, int]:
    if backup_path:
        shutil.copy2(db_path, backup_path)

    connection = sqlite3.connect(db_path)
    repaired = skipped = 0
    try:
        rows = connection.execute(
            "SELECT r.ticker, r.raw_json, s.confidence "
            "FROM scan_raw_data r JOIN scan_summary s ON s.ticker = r.ticker"
        ).fetchall()
        with connection:
            for ticker, raw_json, confidence in rows:
                details = json.loads(raw_json)
                history = _history_frame(details.get("hist"))
                if history.empty:
                    skipped += 1
                    continue
                result = forecast_price_range(history, details.get("technical", {}))
                forecast = _format_forecast(result, float(confidence or 0.0))
                values = forecast.get("forecasts", {})
                for scenario in values.values():
                    numeric = [scenario.get(key) for key in ("bear", "base", "bull")]
                    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in numeric):
                        raise ValueError(f"Non-finite repaired forecast for {ticker}: {numeric}")
                    if not numeric[0] <= numeric[1] <= numeric[2]:
                        raise ValueError(f"Unordered repaired forecast for {ticker}: {numeric}")

                details["forecast"] = forecast
                bull_pct_90 = float(values.get("90", {}).get("bull_pct", 0.0))
                connection.execute(
                    "UPDATE scan_raw_data SET raw_json = ? WHERE ticker = ?",
                    (json.dumps(details, allow_nan=False, separators=(",", ":")), ticker),
                )
                connection.execute(
                    "UPDATE scan_summary SET bull_pct_90 = ? WHERE ticker = ?",
                    (bull_pct_90, ticker),
                )
                repaired += 1
    finally:
        connection.close()
    return repaired, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("scans_data.db"))
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    repaired, skipped = repair_database(args.db, args.backup)
    print(f"Repaired {repaired} securities; skipped {skipped} without stored history.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
