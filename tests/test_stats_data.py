import datetime as dt
import json
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

    def test_current_streak_continues_through_in_progress_zero_day(self):
        # today has zero commits (the day is still in progress at publish
        # time), but the preceding days form an unbroken run — the streak
        # must not collapse to zero just because today hasn't logged a
        # commit yet.
        start = dt.date(2026, 7, 15)
        daily = daily_from(start, [1, 2, 3, 4, 5, 0])
        result = stats_data.compute_streaks(daily, dt.date(2026, 7, 20))
        self.assertEqual(result["current"], 5)

    def test_current_streak_broken_by_a_completed_zero_day(self):
        # today is in progress (zero so far) but yesterday already
        # *completed* with zero commits — that's a real gap, so the streak
        # must not reach past it to the earlier run.
        start = dt.date(2026, 7, 15)
        daily = daily_from(start, [1, 2, 3, 0, 0, 0])
        result = stats_data.compute_streaks(daily, dt.date(2026, 7, 20))
        self.assertEqual(result["current"], 0)

    def test_current_and_longest_together_when_they_differ(self):
        start = dt.date(2026, 7, 15)
        daily = daily_from(start, [1, 1, 1, 0, 1, 1])  # 15th..20th
        result = stats_data.compute_streaks(daily, dt.date(2026, 7, 20))
        self.assertEqual(result, {"current": 2, "longest": 3})

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


class BuildPayloadTest(unittest.TestCase):
    def payload(self, repos):
        return stats_data.build_payload(
            now=dt.datetime(2026, 7, 20, 0, 30, tzinfo=dt.timezone.utc),
            daily={"2026-07-19": 3, "2026-07-20": 5},
            months=[("2026-06", "Jun", 460), ("2026-07", "Jul", 166)],
            languages=[("PHP", 49.7), ("Vue", 28.3)],
            totals={
                "commits": 3088,
                "active_days": 256,
                "prs_merged": 791,
                "repos_touched": 27,
            },
            repos=repos,
        )

    def test_private_repo_names_never_appear(self):
        result = self.payload([
            {"name": "secret-client-api", "url": "https://github.com/x/secret-client-api",
             "private": True, "commits": 100},
            {"name": "public-thing", "url": "https://github.com/x/public-thing",
             "private": False, "commits": 5},
        ])
        self.assertNotIn("secret-client-api", json.dumps(result))
        self.assertEqual(result["repos"]["private"], {"commits": 100, "repos": 1})

    def test_public_repos_sorted_by_commits_desc(self):
        result = self.payload([
            {"name": "small", "url": "https://github.com/x/small",
             "private": False, "commits": 5},
            {"name": "big", "url": "https://github.com/x/big",
             "private": False, "commits": 50},
        ])
        self.assertEqual([r["name"] for r in result["repos"]["public"]], ["big", "small"])
        self.assertEqual(result["repos"]["public"][0]["url"], "https://github.com/x/big")

    def test_window_days_reports_the_true_span_of_daily(self):
        # The daily map is inclusive of both endpoints, so a 366-day map
        # (not the WINDOW_DAYS=365 constant) must be published as-is.
        start = dt.date(2025, 7, 20)
        daily = daily_from(start, [1] * 366)  # 2025-07-20..2026-07-20 inclusive
        result = stats_data.build_payload(
            now=dt.datetime(2026, 7, 20, 0, 30, tzinfo=dt.timezone.utc),
            daily=daily,
            months=[],
            languages=[],
            totals={"commits": 0, "active_days": 0, "prs_merged": 0, "repos_touched": 0},
            repos=[],
        )
        self.assertEqual(len(daily), 366)
        self.assertEqual(result["window_days"], len(daily))

    def test_no_private_repos_gives_zeroed_aggregate(self):
        result = self.payload([
            {"name": "only", "url": "https://github.com/x/only",
             "private": False, "commits": 1},
        ])
        self.assertEqual(result["repos"]["private"], {"commits": 0, "repos": 0})

    def test_scalar_fields_pass_through(self):
        result = self.payload([])
        self.assertEqual(result["synced"], "2026-07-20T00:30:00Z")
        self.assertEqual(result["window_days"], len(result["daily"]))
        self.assertEqual(result["totals"]["commits"], 3088)
        self.assertEqual(result["months"][0], {"key": "2026-06", "label": "Jun", "commits": 460})
        self.assertEqual(result["languages"][0], {"name": "PHP", "pct": 49.7})
        self.assertEqual(result["streak"], {"current": 2, "longest": 2})
        self.assertEqual(result["daily"]["2026-07-20"], 5)

    def test_explicit_streak_overrides_computed(self):
        # when the caller passes an all-time streak, build_payload uses it
        # verbatim instead of computing one from the (windowed) daily map
        result = stats_data.build_payload(
            now=dt.datetime(2026, 7, 20, 0, 30, tzinfo=dt.timezone.utc),
            daily={"2026-07-19": 3, "2026-07-20": 5},
            streak={"current": 23, "longest": 140},
            months=[],
            languages=[],
            totals={"commits": 1, "active_days": 1, "prs_merged": 0, "repos_touched": 1},
            repos=[],
        )
        self.assertEqual(result["streak"], {"current": 23, "longest": 140})


if __name__ == "__main__":
    unittest.main()
