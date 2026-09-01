import os
import sqlite3
import tempfile
import unittest

from data.db import init_db, load_all_summaries, save_stock_result


class DatabaseTests(unittest.TestCase):
    def test_schema_migrates_and_persists_risk_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "scan.db")
            init_db(path)
            save_stock_result(
                "TEST",
                {
                    "last_price": 10,
                    "bull_score": 70,
                    "risk_score": 30,
                    "confidence": 80,
                    "risk_adjusted_conviction": 52,
                    "annualized_volatility": 0.2,
                    "max_drawdown": -0.15,
                },
                {"scores": {"risk_analysis": {"available": True}}},
                path,
            )
            frame = load_all_summaries(path)
            self.assertEqual(frame.loc[0, "risk_adjusted_conviction"], 52)
            self.assertAlmostEqual(frame.loc[0, "annualized_volatility"], 0.2)
            connection = sqlite3.connect(path)
            try:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(scan_summary)")}
            finally:
                connection.close()
            self.assertIn("max_drawdown", columns)


if __name__ == "__main__":
    unittest.main()
