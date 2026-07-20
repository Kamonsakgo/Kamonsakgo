# Clickable Dev Stats Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Dev Stats image on the profile README clickable, leading to a GitHub Pages dashboard with per-day commit detail.

**Architecture:** `gen_stats.py` already fetches every commit with its author date and throws the per-day counts away. Keep them, emit `out/data.json` next to the existing `out/stats.svg`, and copy a static `web/index.html` into `out/` at generate time. The nightly workflow already publishes all of `out/` to branch `stats`, so nothing about the workflow changes. The README image gets wrapped in an anchor.

**Tech Stack:** Python 3 standard library only (no new dependencies), `unittest` for tests, vanilla HTML/CSS/JS with no build step.

Spec: `docs/superpowers/specs/2026-07-20-clickable-dev-stats-dashboard-design.md`

## Global Constraints

- **No new runtime dependencies.** `gen_stats.py` uses only the Python standard library. Keep it that way. Tests use `unittest` (stdlib) because `pytest` is not installed on this machine.
- **No workflow changes.** `.github/workflows/stats.yml` is not modified by any task.
- **Privacy is non-negotiable.** `data.json` must never contain a private repo name, URL, commit message, diff, or branch name. Private repos are aggregated into a single `{"commits": N, "repos": M}` object.
- **`out/` is gitignored.** Never `git add` anything under `out/`. Page source lives at `web/index.html`.
- **Existing SVG output is unchanged.** No task edits the SVG rendering code or the numbers it prints.
- **Palette (copy verbatim):** background `#0d1117`, panel border `#30363d`, grid `#1c2530`, muted text `#8b949e`, body text `#c9d1d9`, accents `#00ff9f` / `#00e5ff` / `#bd00ff`, font `'Courier New', monospace`.
- **Pages URL:** `https://kamonsakgo.github.io/Kamonsakgo/`
- **Window:** 365 days ending today, matching the existing `SINCE` in `gen_stats.py`.

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `scripts/stats_data.py` | Create | Pure functions: streak computation and `data.json` payload assembly. No network, no I/O — testable in isolation. |
| `tests/test_stats_data.py` | Create | `unittest` suite for `stats_data.py`. |
| `scripts/gen_stats.py` | Modify | Collect per-day counts and per-repo public/private buckets during the existing commit loop; call `stats_data.build_payload`; write `out/data.json`; copy `web/index.html` to `out/`. |
| `web/index.html` | Create | The dashboard: self-contained HTML/CSS/JS, fetches `data.json`. |
| `README.md` | Modify | Wrap the stats `<img>` (line 53) in an anchor + caption. |

`gen_stats.py` stays the collector/renderer it already is; only the pure, testable
logic moves into `stats_data.py`. The SVG rendering block is not touched.

---

### Task 1: Streak computation

**Files:**
- Create: `scripts/stats_data.py`
- Test: `tests/test_stats_data.py`

**Interfaces:**
- Consumes: nothing
- Produces: `compute_streaks(daily: dict[str, int], today: datetime.date) -> dict` returning `{"current": int, "longest": int}`. `daily` maps `"YYYY-MM-DD"` to a commit count, and includes zero-count days. `current` counts consecutive non-zero days ending at `today`; if `today` has zero commits the streak is `0`. `longest` is the longest run of consecutive non-zero days anywhere in `daily`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_stats_data.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Desktop/Go/Kamonsakgo && python3 -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats_data'`

- [ ] **Step 3: Write minimal implementation**

Create `scripts/stats_data.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Desktop/Go/Kamonsakgo && python3 -m unittest discover -s tests -v`
Expected: PASS — `Ran 4 tests` / `OK`

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/Go/Kamonsakgo
git add scripts/stats_data.py tests/test_stats_data.py
git commit -m "Add streak computation for the stats dashboard payload"
```

---

### Task 2: Payload assembly with private-repo aggregation

**Files:**
- Modify: `scripts/stats_data.py`
- Test: `tests/test_stats_data.py`

**Interfaces:**
- Consumes: `compute_streaks(daily, today)` from Task 1
- Produces: `build_payload(*, now, daily, months, languages, totals, repos) -> dict`

  Parameters, all keyword-only:
  - `now`: `datetime.datetime` (UTC), the sync timestamp
  - `daily`: `{"YYYY-MM-DD": int}` — must already cover all 365 days including zeros
  - `months`: list of `(key, label, count)` tuples, oldest first, e.g. `("2026-06", "Jun", 460)`
  - `languages`: list of `(name, pct)` tuples, e.g. `("PHP", 49.7)`
  - `totals`: `{"commits": int, "active_days": int, "prs_merged": int, "repos_touched": int}`
  - `repos`: list of dicts, one per repo with at least one commit in the window, each
    `{"name": str, "url": str, "private": bool, "commits": int}`

  Returns the `data.json` structure from the spec. Public repos are sorted by
  commits descending then name ascending; private repos are collapsed into
  `{"commits": total, "repos": count}` with names and URLs discarded.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_stats_data.py`, above the `if __name__` block:

```python
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

    def test_no_private_repos_gives_zeroed_aggregate(self):
        result = self.payload([
            {"name": "only", "url": "https://github.com/x/only",
             "private": False, "commits": 1},
        ])
        self.assertEqual(result["repos"]["private"], {"commits": 0, "repos": 0})

    def test_scalar_fields_pass_through(self):
        result = self.payload([])
        self.assertEqual(result["synced"], "2026-07-20T00:30:00Z")
        self.assertEqual(result["window_days"], 365)
        self.assertEqual(result["totals"]["commits"], 3088)
        self.assertEqual(result["months"][0], {"key": "2026-06", "label": "Jun", "commits": 460})
        self.assertEqual(result["languages"][0], {"name": "PHP", "pct": 49.7})
        self.assertEqual(result["streak"], {"current": 2, "longest": 2})
        self.assertEqual(result["daily"]["2026-07-20"], 5)
```

Add `import json` to the imports at the top of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/Desktop/Go/Kamonsakgo && python3 -m unittest discover -s tests -v`
Expected: FAIL — `AttributeError: module 'stats_data' has no attribute 'build_payload'`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/stats_data.py`:

```python
WINDOW_DAYS = 365


def build_payload(*, now, daily, months, languages, totals, repos):
    """Assemble the data.json structure served to the dashboard page.

    Private repos are collapsed into a single aggregate — their names and URLs
    are dropped here and never reach the published file.
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
        "window_days": WINDOW_DAYS,
        "totals": dict(totals),
        "streak": compute_streaks(daily, now.date()),
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/Desktop/Go/Kamonsakgo && python3 -m unittest discover -s tests -v`
Expected: PASS — `Ran 8 tests` / `OK`

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/Go/Kamonsakgo
git add scripts/stats_data.py tests/test_stats_data.py
git commit -m "Assemble dashboard payload with private repos aggregated"
```

---

### Task 3: Wire `gen_stats.py` to emit `out/data.json`

**Files:**
- Modify: `scripts/gen_stats.py`
- Test: manual — this task is network I/O and file writing, verified by running the script

**Interfaces:**
- Consumes: `stats_data.build_payload` and `stats_data.compute_streaks` from Tasks 1-2
- Produces: `out/data.json` conforming to the spec schema

Read `scripts/gen_stats.py` before editing. The relevant regions:
- the collection loop starting at `for r in repos:` (around line 74)
- the `lang_rows` computation (around line 100)
- the final write block at the end of the file

- [ ] **Step 1: Import the helper and add per-day / per-repo accumulators**

Add near the other imports at the top of `scripts/gen_stats.py`:

```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_data
```

Then find this block:

```python
months = {k: 0 for k in month_keys}
days = set()
total = 0
touched = 0
lang_bytes = {}
```

and add two accumulators:

```python
months = {k: 0 for k in month_keys}
days = set()
total = 0
touched = 0
lang_bytes = {}
daily = {}
repo_rows = []
```

- [ ] **Step 2: Record per-day counts and repo rows inside the existing loop**

In the `for r in repos:` loop, the body currently reads:

```python
    if not commits:
        continue
    touched += 1
    for c in commits:
        date = c["commit"]["author"]["date"]
        total += 1
        days.add(date[:10])
        if date[:7] in months:
            months[date[:7]] += 1
```

Change it to:

```python
    if not commits:
        continue
    touched += 1
    for c in commits:
        date = c["commit"]["author"]["date"]
        total += 1
        days.add(date[:10])
        daily[date[:10]] = daily.get(date[:10], 0) + 1
        if date[:7] in months:
            months[date[:7]] += 1
    repo_rows.append({
        "name": r["name"],
        "url": r["html_url"],
        "private": r["private"],
        "commits": len(commits),
    })
```

- [ ] **Step 3: Fill zero days so the heatmap has a complete 365-day grid**

Add this right after the `for r in repos:` loop finishes, before the `prs = api(...)` line:

```python
for i in range(365):
    key = (SINCE + dt.timedelta(days=i)).strftime("%Y-%m-%d")
    daily.setdefault(key, 0)
daily = {k: daily[k] for k in sorted(daily) if k >= SINCE.strftime("%Y-%m-%d")}
```

The second line drops any commit dated before the window (author dates can lag
the `since` filter, which GitHub applies to committer date) so `daily` covers
exactly the published window.

Because of that trim, `sum(daily.values())` can be a hair below `totals.commits`,
which counts every commit the API returned. That is expected — `totals` must keep
matching the SVG, so it is not recomputed from `daily`.

- [ ] **Step 4: Write `data.json` next to the SVG**

Find the write block at the very end of the file:

```python
os.makedirs("out", exist_ok=True)
with open("out/stats.svg", "w") as f:
    f.write(svg)
```

and add the JSON write after it:

```python
os.makedirs("out", exist_ok=True)
with open("out/stats.svg", "w") as f:
    f.write(svg)

payload = stats_data.build_payload(
    now=NOW,
    daily=daily,
    months=[
        (k, dt.datetime.strptime(k, "%Y-%m").strftime("%b"), months[k])
        for k in month_keys
    ],
    languages=lang_rows,
    totals={
        "commits": total,
        "active_days": len(days),
        "prs_merged": prs_merged,
        "repos_touched": touched,
    },
    repos=repo_rows,
)
with open("out/data.json", "w") as f:
    json.dump(payload, f, separators=(",", ":"))
```

`json` and `os` are already imported at the top of the file. No new imports beyond
`stats_data`.

- [ ] **Step 5: Run the script and verify the output**

If a PAT is available:

```bash
cd ~/Desktop/Go/Kamonsakgo
METRICS_TOKEN=<pat> python3 scripts/gen_stats.py
python3 - <<'EOF'
import json
d = json.load(open("out/data.json"))
assert sum(d["daily"].values()) <= d["totals"]["commits"], "daily sum exceeds total"
assert sum(d["daily"].values()) >= d["totals"]["commits"] * 0.99, "daily lost too many commits"
assert len(d["daily"]) in (365, 366), f"expected ~365 days, got {len(d['daily'])}"
assert all(k in d for k in ("synced", "streak", "months", "languages", "repos"))
print("OK", d["totals"], "public repos:", len(d["repos"]["public"]),
      "private:", d["repos"]["private"])
EOF
```

Expected: `OK {...} public repos: N private: {...}` with no assertion error.

Then eyeball the file for leaks:

```bash
python3 -c "import json;print(json.dumps(json.load(open('out/data.json'))['repos'],indent=2))"
```

Expected: only public repo names under `public`; `private` is a bare
`{"commits": N, "repos": M}` with no names.

If no PAT is available, skip the run and note it — Task 4 covers preview with a
fixture, and the real file lands on the next nightly run.

- [ ] **Step 6: Commit**

```bash
cd ~/Desktop/Go/Kamonsakgo
git add scripts/gen_stats.py
git commit -m "Emit out/data.json with per-day commit counts"
```

---

### Task 4: The dashboard page

**Files:**
- Create: `web/index.html`
- Create: `tests/fixtures/data.json` (fixture for offline preview)
- Modify: `scripts/gen_stats.py` (copy `web/index.html` into `out/`)

**Interfaces:**
- Consumes: the `data.json` schema produced in Task 2
- Produces: `out/index.html`, served at `https://kamonsakgo.github.io/Kamonsakgo/`

- [ ] **Step 1: Create the preview fixture**

Create `tests/fixtures/data.json` with a generator so the heatmap has realistic
density (run this, don't hand-write 365 entries):

```bash
cd ~/Desktop/Go/Kamonsakgo
mkdir -p tests/fixtures
python3 - <<'EOF'
import datetime as dt, json, os, sys
sys.path.insert(0, "scripts")
import stats_data

now = dt.datetime(2026, 7, 20, 0, 30, tzinfo=dt.timezone.utc)
since = now - dt.timedelta(days=364)
# deterministic pseudo-random density, no randomness so previews are stable
daily = {}
for i in range(365):
    day = since + dt.timedelta(days=i)
    n = (i * 7919) % 23
    daily[day.strftime("%Y-%m-%d")] = 0 if n < 6 else n - 5

months = []
cur = now.replace(day=1)
keys = []
for _ in range(12):
    keys.append(cur.strftime("%Y-%m"))
    cur = (cur - dt.timedelta(days=1)).replace(day=1)
for k in reversed(keys):
    months.append((k, dt.datetime.strptime(k, "%Y-%m").strftime("%b"),
                   sum(v for d, v in daily.items() if d[:7] == k)))

payload = stats_data.build_payload(
    now=now, daily=daily, months=months,
    languages=[("PHP", 49.7), ("Vue", 28.3), ("TypeScript", 9.7),
               ("Python", 7.6), ("JavaScript", 4.8)],
    totals={"commits": sum(daily.values()),
            "active_days": sum(1 for v in daily.values() if v),
            "prs_merged": 791, "repos_touched": 27},
    repos=[{"name": f"public-repo-{i}", "url": f"https://github.com/Kamonsakgo/public-repo-{i}",
            "private": False, "commits": 200 - i * 30} for i in range(5)]
         + [{"name": f"secret-{i}", "url": "x", "private": True, "commits": 150}
            for i in range(12)],
)
os.makedirs("tests/fixtures", exist_ok=True)
json.dump(payload, open("tests/fixtures/data.json", "w"), indent=2)
print("wrote fixture:", payload["totals"], payload["streak"])
EOF
```

Expected: `wrote fixture: {...} {...}`

- [ ] **Step 2: Write the page**

Create `web/index.html`. Requirements, all mandatory:

- Single file. Inline `<style>` and `<script>`. No CDN links, no external fonts, no
  build step, no framework.
- `fetch("data.json")` on load. On failure (network error, non-200, or malformed
  JSON) replace the content area with a single line:
  `could not load stats — try again later` in `#8b949e`. Do not leave a blank page.
- Colors and font exactly as listed in Global Constraints.
- Page title: `Dev Stats — Kamonsakgo`.

Sections in order:

1. **Header** — `[ DEV.STATS ]` in `#00ff9f`, subtitle `last 365 days — public + private`,
   and `synced <YYYY-MM-DD>` derived from `data.synced` on the right.
2. **Tiles** — six tiles in a responsive grid: commits, active days, PRs merged,
   repos touched, current streak, longest streak. Value large and colored, label
   below in `#8b949e` uppercase with `letter-spacing: 2px`. Streak labels read
   `CURRENT STREAK` / `LONGEST STREAK` and their values are suffixed with ` d`.
3. **Heatmap** — one cell per entry in `data.daily`, laid out in columns of 7 days
   (weeks), oldest column at the left, day-of-week as the row. Cell size 11px with
   2px gaps, 2px radius. Five intensity buckets by commit count relative to the
   max daily value: `0` → `#161b22`; then `#0e4429`, `#006d32`, `#26a641`, `#00ff9f`.
   Month labels above the columns where the month changes.
   The grid lives in a `overflow-x: auto` container so the page body never scrolls
   horizontally.
   Hover (desktop) and tap (mobile) show a tooltip anchored to the cell reading
   `20 Jun 2026 · 14 commits`, or `20 Jun 2026 · no commits` when the count is 0.
   Use `1 commit` (singular) when the count is exactly 1.
4. **Monthly bars** — twelve bars from `data.months`, count above each bar, month
   label below, using a top-to-bottom gradient from `#006d5b` to `#00ff9f`.
   Clicking a bar highlights that month's heatmap cells (dim all others to
   `opacity: 0.25`) and scrolls the heatmap container so that month is visible.
   Clicking the same bar again clears the highlight. The active bar is visually
   marked (e.g. `#00e5ff` outline) so the filter state is obvious.
5. **Languages** — a single stacked horizontal bar plus a legend, colors in order
   `#00ff9f`, `#00e5ff`, `#bd00ff`, `#3fb950`, `#ffbd2e`, `#8b949e`, matching the
   SVG's `PALETTE`. Legend entries read `PHP 49.7%` with the percentage in `#8b949e`.
6. **Repos** — a list. Each public repo is a row: name as a link to `repo.url`
   (opens in a new tab, `rel="noopener"`), commit count right-aligned. After them,
   one non-linked row reading
   `Private work — 2,140 commits across 12 repos` built from
   `data.repos.private`, styled muted. Omit the private row entirely when
   `data.repos.private.repos` is 0. Use `1 repo` / `1 commit` singular forms.
7. **Footer** — `aggregated nightly via GitHub Actions` and a link back to
   `https://github.com/Kamonsakgo`.

Responsive: below 640px the tile grid collapses to two columns, and font sizes
step down. The heatmap keeps its cell size and scrolls.

Escape any string interpolated into HTML, or build nodes with
`document.createElement` and `textContent`. Repo names come from the GitHub API
and must not be injected as raw HTML.

- [ ] **Step 3: Preview against the fixture**

```bash
cd ~/Desktop/Go/Kamonsakgo
mkdir -p /tmp/devstats-preview
cp web/index.html tests/fixtures/data.json /tmp/devstats-preview/
cd /tmp/devstats-preview && python3 -m http.server 8765
```

Open `http://localhost:8765/` and confirm:
- all six tiles show numbers
- the heatmap renders 365 cells in 7 rows with visible intensity variation
- hovering a cell shows the tooltip with the correct date and count
- clicking a month bar dims the other months; clicking again restores them
- the language bar and legend render
- five public repo rows plus one `Private work — ... across 12 repos` row
- no private repo name (`secret-`) appears anywhere on the page
- at a 375px-wide viewport the page does not scroll horizontally

Stop the server with Ctrl-C when done.

- [ ] **Step 4: Copy the page into `out/` at generate time**

In `scripts/gen_stats.py`, extend the write block from Task 3. After the
`json.dump(...)` lines add:

```python
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "web", "index.html")) as f:
    page = f.read()
with open("out/index.html", "w") as f:
    f.write(page)
```

`out/` is gitignored, so `index.html` is versioned only at `web/index.html`.

- [ ] **Step 5: Verify the copy and re-run the suite**

```bash
cd ~/Desktop/Go/Kamonsakgo
python3 -m unittest discover -s tests -v
```

Expected: `Ran 8 tests` / `OK` (the page has no Python tests; this confirms
Tasks 1-2 still pass after the `gen_stats.py` edits).

If a PAT is available, also run `METRICS_TOKEN=<pat> python3 scripts/gen_stats.py`
and confirm `out/index.html` exists and is byte-identical to `web/index.html`:

```bash
diff web/index.html out/index.html && echo "identical"
```

Expected: `identical`

- [ ] **Step 6: Commit**

```bash
cd ~/Desktop/Go/Kamonsakgo
git add web/index.html tests/fixtures/data.json scripts/gen_stats.py
git commit -m "Add the Dev Stats dashboard page and publish it with the stats output"
```

---

### Task 5: Link the README image

**Files:**
- Modify: `README.md:52-54`

**Interfaces:**
- Consumes: the Pages URL from Task 4
- Produces: nothing downstream

- [ ] **Step 1: Wrap the image in an anchor**

The block currently reads:

```html
<div align="center">
  <img src="https://raw.githubusercontent.com/Kamonsakgo/Kamonsakgo/stats/stats.svg" alt="Dev stats — updated daily" width="100%" />
</div>
```

Replace it with:

```html
<div align="center">
  <a href="https://kamonsakgo.github.io/Kamonsakgo/">
    <img src="https://raw.githubusercontent.com/Kamonsakgo/Kamonsakgo/stats/stats.svg" alt="Dev stats — updated daily" width="100%" />
  </a>
  <sub><a href="https://kamonsakgo.github.io/Kamonsakgo/">→ click for the full dashboard — per-day commits, streaks, languages</a></sub>
</div>
```

- [ ] **Step 2: Verify the markup renders**

Run: `cd ~/Desktop/Go/Kamonsakgo && grep -n "kamonsakgo.github.io" README.md`
Expected: two matches, both on the lines just added.

GitHub renders this fine — an `<a>` wrapping an `<img>` survives README
sanitization. The link 404s until Pages is enabled (Task 6).

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/Go/Kamonsakgo
git add README.md
git commit -m "Link the Dev Stats panel to the full dashboard"
```

---

### Task 6: Enable Pages and verify the live deployment

**Files:** none — repository settings and verification only

- [ ] **Step 1: Hand the Pages step to the repo owner**

This cannot be automated from here. The owner must do it in the browser:

> **Settings → Pages → Build and deployment → Source: Deploy from a branch →
> Branch: `stats` / `(root)` → Save**

Do this *before* pushing the README change, otherwise the link 404s until the
setting is saved.

- [ ] **Step 2: Push and trigger a run**

```bash
cd ~/Desktop/Go/Kamonsakgo
git push origin main
gh workflow run "Dev Stats" 2>/dev/null || echo "trigger manually: Actions → Dev Stats → Run workflow"
```

The workflow's `push` trigger only fires on changes to `scripts/gen_stats.py` or
the workflow file, so Task 3's edit does trigger it. `web/index.html` alone would
not — hence the explicit `workflow_run`.

- [ ] **Step 3: Verify the published output**

After the run completes:

```bash
curl -sI https://kamonsakgo.github.io/Kamonsakgo/ | head -1
curl -s https://kamonsakgo.github.io/Kamonsakgo/data.json | python3 -m json.tool | head -20
```

Expected: `HTTP/2 200`, and JSON whose `totals` match the numbers rendered in the
README SVG.

- [ ] **Step 4: Final privacy check on the live file**

```bash
curl -s https://kamonsakgo.github.io/Kamonsakgo/data.json \
  | python3 -c "import json,sys;print(json.dumps(json.load(sys.stdin)['repos'],indent=2))"
```

Expected: every name under `public` is a repo that is genuinely public on GitHub;
`private` is a bare `{"commits": N, "repos": M}`. If any private repo name appears,
stop, revert the README link, and fix the filter before anything else.

- [ ] **Step 5: Open the dashboard and confirm it matches the SVG**

Load `https://kamonsakgo.github.io/Kamonsakgo/` in a browser. The four shared
tiles must equal the numbers in the README image, and the heatmap must be
populated.
