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
    if daily.get(day.strftime("%Y-%m-%d"), 0) == 0:
        # `today` is still in progress at publish time — a day with no
        # commits *yet* must not break the streak. Only a completed day
        # (yesterday and earlier) with zero commits ends it.
        day -= dt.timedelta(days=1)
    while daily.get(day.strftime("%Y-%m-%d"), 0) > 0:
        current += 1
        day -= dt.timedelta(days=1)

    return {"current": current, "longest": longest}


def build_payload(*, now, daily, months, languages, totals, repos, streak=None):
    """Assemble the data.json structure served to the dashboard page.

    Private repos are collapsed into a single aggregate — their names and URLs
    are dropped here and never reach the published file.

    `daily` is the heatmap window (last ~year). `streak`, when given, is used
    verbatim (so it can reflect all-time history rather than just `daily`);
    otherwise it is computed from `daily`.
    """
    public = sorted(
        (
            {"name": r["name"], "url": r["url"], "commits": r["commits"]}
            for r in repos
            if not r["private"]
        ),
        key=lambda r: (-r["commits"], r["name"]),
    )
    private = [r for r in repos if r["private"]]

    return {
        "synced": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": len(daily),
        "totals": dict(totals),
        "streak": streak if streak is not None else compute_streaks(daily, now.date()),
        "daily": dict(daily),
        "months": [
            {"key": k, "label": label, "commits": c} for k, label, c in months
        ],
        "languages": [{"name": n, "pct": round(p, 1)} for n, p in languages],
        "repos": {
            "public": public,
            "private": {
                "commits": sum(r["commits"] for r in private),
                "repos": len(private),
            },
        },
    }
