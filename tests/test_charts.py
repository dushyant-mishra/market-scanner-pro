import math
import unittest

import pandas as pd

from ui.charts import create_risk_return_chart, create_sector_heatmap


class ChartTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            {
                "ticker": ["AAA", "BBB", "CCC"],
                "company_name": ["Alpha Corp", "Beta Inc", "Gamma Ltd"],
                "industry": ["Software", "Hardware", "Services"],
                "sector": ["Tech", "Tech", None],
                "marketCap": [2e9, 1e9, None],
                "last_price": [100, None, 30],
                "bull_score": [80, None, 25],
                "risk_score": [25, 70, None],
            }
        )

    def test_sector_heatmap_resolves_all_node_colors(self):
        fig = create_sector_heatmap(self.frame)
        self.assertTrue(fig.data)
        for color in fig.data[0].marker.colors:
            self.assertIsNotNone(color)
            self.assertFalse(isinstance(color, float) and math.isnan(color))
        self.assertIn("Alpha Corp", str(fig.data[0].customdata))

    def test_risk_return_chart_sanitizes_missing_values(self):
        fig = create_risk_return_chart(self.frame)
        self.assertTrue(fig.data)
        self.assertEqual(fig.layout.xaxis.range, (0, 100))
        self.assertEqual(fig.layout.yaxis.range, (0, 100))
        self.assertIn("Alpha Corp", str(fig.data[0].customdata))

    def test_risk_gauge_inverts_color_polarity(self):
        from ui.charts import create_score_gauge
        low = create_score_gauge(20, "Risk", invert=True)
        high = create_score_gauge(80, "Risk", invert=True)
        self.assertEqual(low.data[0].gauge.bar.color, "#00d4aa")
        self.assertEqual(high.data[0].gauge.bar.color, "#ff4757")

    def test_heatmap_accepts_empty_legacy_frame(self):
        fig = create_sector_heatmap(pd.DataFrame())
        self.assertTrue(fig.layout.annotations)

    def test_charts_sanitize_infinite_and_negative_values(self):
        frame = pd.DataFrame({
            "ticker": ["BAD"], "bull_score": [float("inf")],
            "risk_score": [float("-inf")], "marketCap": [-1],
        })
        risk_fig = create_risk_return_chart(frame)
        self.assertTrue(risk_fig.data)
        heatmap_fig = create_sector_heatmap(frame)
        self.assertTrue(heatmap_fig.layout.annotations)


if __name__ == "__main__":
    unittest.main()
