import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import stats_data


def daily_from(start, counts):
    """Build a {'YYYY-MM-DD': count} dict starting at `start` date."""
    return {
        (start + dt.timedelta(days=i)).strftime("%Y-%m-%d"): c
        for i, c in enumerate(counts)
    }


class ComputeStreaksTest(unittest.TestCase):
    def test_current_streak_counts_back_from_today(self):
        start = dt.date(2026, 7, 15)
        daily = daily_from(start, [1, 0, 2, 3, 4, 5])  # 15th..20th
        result = stats_data.compute_streaks(daily, dt.date(2026, 7, 20))
        self.assertEqual(result["current"], 4)

    def test_current_streak_is_zero_when_today_has_no_commits(self):
        start = dt.date(2026, 7, 15)
        daily = daily_from(start, [1, 2, 3, 4, 5, 0])
        result = stats_data.compute_streaks(daily, dt.date(2026, 7, 20))
        self.assertEqual(result["current"], 0)

    def test_longest_streak_finds_run_in_the_middle(self):
        start = dt.date(2026, 7, 15)
        daily = daily_from(start, [0, 1, 1, 1, 0, 2])
        result = stats_data.compute_streaks(daily, dt.date(2026, 7, 20))
        self.assertEqual(result["longest"], 3)

    def test_all_zero_days_give_zero_streaks(self):
        start = dt.date(2026, 7, 15)
        daily = daily_from(start, [0, 0, 0, 0, 0, 0])
        result = stats_data.compute_streaks(daily, dt.date(2026, 7, 20))
        self.assertEqual(result, {"current": 0, "longest": 0})


if __name__ == "__main__":
    unittest.main()
