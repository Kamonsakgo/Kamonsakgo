"""Pure helpers for the Dev Stats dashboard payload.

No network calls and no file I/O — everything here is a plain function over
plain data so it can be tested without a GitHub token.
"""
import datetime as dt


def compute_streaks(daily, today):
    """Return {"current", "longest"} day streaks from a {date: count} map."""
    longest = run = 0
    for key in sorted(daily):
        if daily[key] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    current = 0
    day = today
    while daily.get(day.strftime("%Y-%m-%d"), 0) > 0:
        current += 1
        day -= dt.timedelta(days=1)

    return {"current": current, "longest": longest}
