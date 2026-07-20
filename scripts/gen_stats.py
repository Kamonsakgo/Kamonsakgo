#!/usr/bin/env python3
"""Generate assets for the profile stats panel from real GitHub activity.

Aggregates the last 365 days of commits across every repo the token can see
(public + private). Output is numbers-only — no repo names ever appear.
"""
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_data

TOKEN = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("METRICS_TOKEN or GITHUB_TOKEN required")

LOGIN = "Kamonsakgo"
API = "https://api.github.com"
NOW = dt.datetime.now(dt.timezone.utc)
SINCE = NOW - dt.timedelta(days=365)
SINCE_ISO = SINCE.strftime("%Y-%m-%dT%H:%M:%SZ")


def api(path, params=None):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": LOGIN,
    })
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (404, 409):  # empty repo etc.
            return []
        raise


def all_pages(path, params):
    page, out = 1, []
    while True:
        batch = api(path, {**params, "per_page": 100, "page": page})
        if not batch:
            return out
        out.extend(batch)
        if len(batch) < 100:
            return out
        page += 1


# ---- collect ---------------------------------------------------------------
repos = all_pages("/user/repos", {
    "affiliation": "owner,collaborator,organization_member",
    "sort": "pushed",
})
repos = [r for r in repos if not r["fork"] and r["pushed_at"] >= SINCE_ISO]

month_keys = []
cur = NOW.replace(day=1)
for _ in range(12):
    month_keys.append(cur.strftime("%Y-%m"))
    cur = (cur - dt.timedelta(days=1)).replace(day=1)
month_keys.reverse()

months = {k: 0 for k in month_keys}
days = set()
total = 0
touched = 0
lang_bytes = {}
daily = {}
repo_rows = []

for r in repos:
    commits = all_pages(f"/repos/{r['full_name']}/commits", {
        "author": LOGIN,
        "since": SINCE_ISO,
    })
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
    # weight languages by MY commits in that repo, not repo size
    if r.get("language"):
        lang_bytes[r["language"]] = lang_bytes.get(r["language"], 0) + len(commits)

for i in range(366):
    key = (SINCE + dt.timedelta(days=i)).strftime("%Y-%m-%d")
    daily.setdefault(key, 0)
daily = {k: daily[k] for k in sorted(daily) if k >= SINCE.strftime("%Y-%m-%d")}

prs = api("/search/issues", {"q": f"author:{LOGIN} is:pr is:merged", "per_page": 1})
prs_merged = prs.get("total_count", 0) if isinstance(prs, dict) else 0

IGNORE_LANGS = {"HTML", "CSS", "SCSS", "Makefile", "Dockerfile", "Procfile"}
langs = sorted(
    ((k, v) for k, v in lang_bytes.items() if k not in IGNORE_LANGS),
    key=lambda kv: -kv[1],
)
lang_total = sum(v for _, v in langs) or 1
top = langs[:5]
other = sum(v for _, v in langs[5:])
lang_rows = [(k, v / lang_total * 100) for k, v in top]
if other:
    lang_rows.append(("Other", other / lang_total * 100))
lang_rows = [(k, p) for k, p in lang_rows if p >= 0.5]

# ---- render ----------------------------------------------------------------
PALETTE = ["#00ff9f", "#00e5ff", "#bd00ff", "#3fb950", "#ffbd2e", "#8b949e"]
TILE_COLORS = ["#00ff9f", "#00e5ff", "#bd00ff", "#00ff9f"]


def fmt(n):
    return f"{n:,}"


tiles = [
    (fmt(total), "COMMITS / 365D"),
    (fmt(len(days)), "ACTIVE DAYS"),
    (fmt(prs_merged), "PRs MERGED"),
    (fmt(touched), "REPOS TOUCHED"),
]

tile_svg = ""
for i, (val, label) in enumerate(tiles):
    cx = 130 + i * 220
    color = TILE_COLORS[i]
    delay = 0.15 + i * 0.15
    tile_svg += f'''
  <g opacity="0" text-anchor="middle" font-family="'Courier New', monospace">
    <animate attributeName="opacity" from="0" to="1" begin="{delay}s" dur="0.5s" fill="freeze"/>
    <animateTransform attributeName="transform" type="translate" values="0 12; 0 0" begin="{delay}s" dur="0.5s" fill="freeze"/>
    <text x="{cx}" y="106" font-size="42" font-weight="bold" fill="{color}" filter="url(#sGlow)">{val}</text>
    <text x="{cx}" y="130" font-size="11" fill="#8b949e" letter-spacing="2">{label}</text>
  </g>'''

max_m = max(list(months.values()) + [1])
bars_svg = ""
for i, k in enumerate(month_keys):
    count = months[k]
    x = 48 + i * 67
    h = max(round(count / max_m * 100), 2 if count else 1)
    y = 300 - h
    label = dt.datetime.strptime(k, "%Y-%m").strftime("%b")
    delay = 0.5 + i * 0.06
    count_txt = (
        f'<text x="{x + 25}" y="{y - 6}" font-size="10" fill="#8b949e" text-anchor="middle" opacity="0">{count}'
        f'<animate attributeName="opacity" from="0" to="1" begin="{delay + 0.4}s" dur="0.3s" fill="freeze"/></text>'
        if count else ""
    )
    bars_svg += f'''
  <rect x="{x}" y="300" width="50" height="0" rx="3" fill="url(#barGrad)" opacity="0.9">
    <animate attributeName="height" from="0" to="{h}" begin="{delay}s" dur="0.5s" fill="freeze"/>
    <animate attributeName="y" from="300" to="{y}" begin="{delay}s" dur="0.5s" fill="freeze"/>
  </rect>
  {count_txt}
  <text x="{x + 25}" y="318" font-size="11" fill="#8b949e" text-anchor="middle" font-family="'Courier New', monospace">{label}</text>'''

seg_svg, legend_svg = "", ""
sx = 48.0
for i, (name, pct) in enumerate(lang_rows):
    w = pct / 100 * 804
    color = PALETTE[i % len(PALETTE)]
    seg_svg += f'''
  <rect x="{sx:.1f}" y="352" width="{max(w - 2, 1):.1f}" height="12" rx="3" fill="{color}" opacity="0">
    <animate attributeName="opacity" from="0" to="0.95" begin="{1.3 + i * 0.12}s" dur="0.4s" fill="freeze"/>
  </rect>'''
    sx += w
    lx = 48 + (i % 3) * 270
    ly = 388 + (i // 3) * 22
    legend_svg += f'''
  <g opacity="0" font-family="'Courier New', monospace">
    <animate attributeName="opacity" from="0" to="1" begin="{1.5 + i * 0.12}s" dur="0.4s" fill="freeze"/>
    <rect x="{lx}" y="{ly - 9}" width="9" height="9" rx="2" fill="{color}"/>
    <text x="{lx + 16}" y="{ly}" font-size="12" fill="#c9d1d9">{name} <tspan fill="#8b949e">{pct:.1f}%</tspan></text>
  </g>'''

synced = NOW.strftime("%Y-%m-%d %H:%M UTC")

svg = f'''<svg width="900" height="460" viewBox="0 0 900 460" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="neonGrad" x1="0" y1="0" x2="900" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#00ff9f"/><stop offset="0.5" stop-color="#00e5ff"/><stop offset="1" stop-color="#bd00ff"/>
    </linearGradient>
    <linearGradient id="barGrad" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="#006d5b"/><stop offset="1" stop-color="#00ff9f"/>
    </linearGradient>
    <filter id="sGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="sGrid" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#1c2530" stroke-width="1"/>
    </pattern>
  </defs>

  <rect width="900" height="460" fill="#0d1117"/>
  <rect width="900" height="460" fill="url(#sGrid)"/>

  <g stroke="url(#neonGrad)" stroke-width="2" fill="none" opacity="0.9">
    <path d="M 16 40 V 16 H 40"/><path d="M 860 16 H 884 V 40"/>
    <path d="M 884 420 V 444 H 860"/><path d="M 40 444 H 16 V 420"/>
  </g>

  <g font-family="'Courier New', monospace">
    <text x="34" y="38" font-size="13" fill="#3fb950">[ DEV.STATS ] :: last 365 days — public + private</text>
    <circle cx="718" cy="33" r="4" fill="#00ff9f" filter="url(#sGlow)">
      <animate attributeName="opacity" values="1;0.2;1" dur="1.6s" repeatCount="indefinite"/>
    </circle>
    <text x="856" y="38" font-size="12" fill="#8b949e" text-anchor="end">synced {synced.split(' ')[0]}</text>
  </g>
  {tile_svg}

  <text x="48" y="172" font-size="13" fill="#00e5ff" font-family="'Courier New', monospace" letter-spacing="2">COMMITS // MONTH</text>
  <line x1="48" y1="300" x2="852" y2="300" stroke="#30363d" stroke-width="1"/>
  {bars_svg}

  <text x="48" y="344" font-size="13" fill="#bd00ff" font-family="'Courier New', monospace" letter-spacing="2">LANGUAGES // WHERE MY COMMITS GO</text>
  {seg_svg}
  {legend_svg}

  <g font-family="'Courier New', monospace" font-size="12">
    <text x="48" y="441" fill="#8b949e">&gt; aggregated nightly via GitHub Actions — no repo names, just the grind</text>
    <rect x="572" y="430" width="8" height="13" fill="#00ff9f">
      <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" repeatCount="indefinite"/>
    </rect>
  </g>

  <rect x="0" y="457" width="900" height="3" fill="url(#neonGrad)">
    <animate attributeName="opacity" values="1;0.5;1" dur="3s" repeatCount="indefinite"/>
  </rect>
</svg>
'''

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

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "web", "index.html")) as f:
    page = f.read()
with open("out/index.html", "w") as f:
    f.write(page)

print(f"total={total} days={len(days)} prs={prs_merged} repos={touched} "
      f"langs={[(k, round(p, 1)) for k, p in lang_rows]}")
