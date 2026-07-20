# Clickable Dev Stats Dashboard

**Date:** 2026-07-20
**Status:** Approved, ready for implementation plan

## Problem

The Dev Stats panel on the profile README is a static SVG. Clicking it does nothing.
The goal is to let a visitor click through to per-day commit detail.

GitHub proxies every README image through camo and renders it as a plain `<img>`.
Links, scripts, and hover states inside an SVG are therefore dead — only CSS/SMIL
animation survives. The only interaction available is wrapping the whole image in
an anchor. So the detail view has to live on a separate HTML page.

## Solution

Publish a real dashboard page to GitHub Pages from the existing `stats` branch, and
make the README image link to it.

The nightly workflow already pushes the whole `out/` directory to branch `stats`
(`crazy-max/ghaction-github-pages`, `build_dir: out`). Adding files to `out/` gets
them published with no workflow change.

## Privacy constraint

The dashboard is public. Private repo names must never appear on it — they would
reveal client and employer systems. Public repos are named and linked; every private
repo is collapsed into a single aggregate row.

No commit messages, no diffs, no branch names, no private repo names anywhere in the
generated JSON. Numbers only.

## Components

### 1. `scripts/gen_stats.py` — emit `out/data.json`

The existing commit loop already fetches every commit with its author date and
discards the per-day counts. Keep them, and write a second output file alongside
`out/stats.svg`.

Schema:

```json
{
  "synced": "2026-07-20T00:30:00Z",
  "window_days": 365,
  "totals": {
    "commits": 3088,
    "active_days": 256,
    "prs_merged": 791,
    "repos_touched": 27
  },
  "streak": { "current": 4, "longest": 31 },
  "daily": { "2025-07-21": 7, "2025-07-22": 0, "...": 0 },
  "months": [ { "key": "2026-06", "label": "Jun", "commits": 460 } ],
  "languages": [ { "name": "PHP", "pct": 49.7 } ],
  "repos": {
    "public": [ { "name": "Kamonsakgo", "url": "https://github.com/Kamonsakgo/Kamonsakgo", "commits": 42 } ],
    "private": { "commits": 2140, "repos": 12 }
  }
}
```

Rules:

- `daily` contains an entry for all 365 days in the window, including zero days, so
  the page does not have to fill gaps.
- `streak.current` counts back from today; a zero day ends the streak.
  `streak.longest` is the longest run of consecutive non-zero days in the window.
- `repos.public` is sorted by commits descending, and only includes repos with at
  least one commit in the window (same filter the SVG already applies via `touched`).
- `repos.private` aggregates every non-public repo into one object. Individual
  private repo names, URLs, and per-repo counts are never written.
- `languages` reuses the existing computation, including the `IGNORE_LANGS` filter
  and the 0.5% floor, so the page and the SVG always agree.
- `totals` reuses the values already rendered into the SVG tiles.

The SVG output is unchanged.

### 2. `out/index.html` — the dashboard

One self-contained file: inline CSS and JS, no CDN, no build step, no dependencies.
It fetches `data.json` from the same directory at load.

Visual language matches the SVG: background `#0d1117`, neon accents `#00ff9f`,
`#00e5ff`, `#bd00ff`, muted text `#8b949e`, `Courier New` monospace.

Sections, top to bottom:

1. **Header** — title and `synced <timestamp>`.
2. **Stat tiles** — the four existing numbers, plus current and longest streak.
3. **Heatmap** — 365 day cells in a GitHub-style week grid. Hover on desktop, tap on
   mobile, shows a tooltip: `20 Jun 2026 · 14 commits`. Zero days render as an empty
   cell and read as `no commits`.
4. **Monthly bars** — the same twelve months as the SVG. Clicking a month highlights
   that month's columns in the heatmap and scrolls them into view. Clicking again
   clears the highlight.
5. **Languages** — the stacked bar and legend, same percentages as the SVG.
6. **Repos** — public repos as name, link, and commit count; a final non-linked row
   reading `Private work — 2,140 commits across 12 repos`.

Responsive: readable on a phone. The heatmap scrolls horizontally inside its own
container rather than forcing the page to scroll sideways.

If `data.json` fails to load, the page shows a short error line instead of an empty
shell.

### 3. `README.md` — link the image

Wrap the existing `<img>` on line 53 in an anchor to
`https://kamonsakgo.github.io/Kamonsakgo/`, and add a small caption line under the
image inviting the click. Nothing else about the panel changes.

### 4. Deployment

No workflow change. One manual step, which the repo owner must perform because it is
a repository setting: **Settings → Pages → Source = branch `stats`, folder `/`**.

Until Pages is enabled the README link 404s, so enable Pages before merging the
README change, or accept a short window where the link is dead.

## Data flow

```
GitHub API (METRICS_TOKEN, public + private)
  → gen_stats.py
      → out/stats.svg   (unchanged, embedded in README)
      → out/data.json   (new)
  → workflow pushes out/ to branch stats
      → raw.githubusercontent.com serves stats.svg
      → GitHub Pages serves index.html + data.json
```

`index.html` is a static asset committed in `out/`, published unchanged by the same
push.

## Error handling

- `gen_stats.py`: existing `HTTPError` handling for 404/409 stays. If the JSON write
  fails the script exits non-zero so the workflow surfaces it rather than publishing
  a stale or partial dashboard.
- `index.html`: a failed or malformed `data.json` fetch renders an inline error
  message. Missing optional fields degrade to an empty section, not a blank page.

## Verification

- Run `gen_stats.py` locally with a PAT and confirm `data.json` validates against the
  schema above, that `sum(daily.values()) == totals.commits`, and that no private
  repo name appears anywhere in the file.
- Without a PAT, generate a fixture `data.json` and preview via
  `python3 -m http.server` in `out/` to check layout, tooltips, month filtering, and
  mobile width.
- After the first nightly run, load the Pages URL and confirm the numbers match the
  SVG in the README.

## Out of scope

- Per-day commit messages or repo attribution.
- Any interaction inside the SVG itself — not possible on GitHub.
- Custom domain, analytics, or a framework/build step for the page.
