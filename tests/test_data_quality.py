import unittest

import pandas as pd

from data.quality import price_history_issues


class PriceHistoryQualityTests(unittest.TestCase):
    def test_normal_history_passes(self):
        frame = pd.DataFrame({"Close": [100 + i * 0.2 for i in range(60)]})
        self.assertEqual(price_history_issues(frame), [])

    def test_isolated_impossible_jump_fails(self):
        prices = [100.0] * 40
        prices[20] = 280.0
        self.assertTrue(price_history_issues(pd.DataFrame({"Close": prices})))

    def test_repeated_split_like_moves_fail(self):
        prices = [100.0] * 40
        prices[15], prices[16], prices[25], prices[26] = 50.0, 100.0, 50.0, 100.0
        self.assertTrue(price_history_issues(pd.DataFrame({"Close": prices})))
