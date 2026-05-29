"""
L4 preview build: reads canonical/*.csv, writes dashboard/preview/index.html.

A single static HTML file with the four live metrics, sortable tables,
inline charts (Chart.js via CDN), per-metric provenance, and a "data
current to" notice on every tile.

Usage:
  python dashboard/build.py
  open dashboard/preview/index.html
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CANONICAL_DIR = REPO_ROOT / "canonical"
OUT_PATH = REPO_ROOT / "docs" / "index.html"


def load_metric(name: str) -> list[dict]:
    rows: list[dict] = []
    p = CANONICAL_DIR / f"{name}.csv"
    if not p.exists():
        return rows
    with p.open() as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def state_label(code: str) -> str:
    # Reverse-lookup canonical code -> display name. Inline mini-mapping
    # for the preview; full mapping lives in transform/geography_codes.py.
    mapping = {
        "IN": "All India",
        "IN-S01": "Jammu & Kashmir", "IN-S02": "Himachal Pradesh",
        "IN-S03": "Punjab", "IN-S04": "Chandigarh",
        "IN-S05": "Uttarakhand", "IN-S06": "Haryana",
        "IN-S07": "NCT of Delhi", "IN-S08": "Rajasthan",
        "IN-S09": "Uttar Pradesh", "IN-S10": "Bihar",
        "IN-S11": "Sikkim", "IN-S12": "Arunachal Pradesh",
        "IN-S13": "Nagaland", "IN-S14": "Manipur",
        "IN-S15": "Mizoram", "IN-S16": "Tripura",
        "IN-S17": "Meghalaya", "IN-S18": "Assam",
        "IN-S19": "West Bengal", "IN-S20": "Jharkhand",
        "IN-S21": "Odisha", "IN-S22": "Chhattisgarh",
        "IN-S23": "Madhya Pradesh", "IN-S24": "Gujarat",
        "IN-S25": "Daman & Diu", "IN-S26": "Dadra & Nagar Haveli",
        "IN-S25_26": "DNH and Daman & Diu (merged)",
        "IN-S27": "Maharashtra", "IN-S28": "Andhra Pradesh",
        "IN-S29": "Karnataka", "IN-S30": "Goa",
        "IN-S31": "Lakshadweep", "IN-S32": "Kerala",
        "IN-S33": "Tamil Nadu", "IN-S34": "Puducherry",
        "IN-S35": "Andaman & Nicobar Islands",
        "IN-S36": "Telangana", "IN-S37": "Ladakh",
    }
    return mapping.get(code, code)


def fmt_num(v: float, unit: str) -> str:
    if unit in ("percent",):
        return f"{v:.2f}%"
    if unit == "females_per_1000_males":
        return f"{v:.0f}"
    if unit == "per_1000_live_births":
        return f"{v:.1f}"
    if unit == "count":
        return f"{int(v):,}"
    return str(v)


# ---------- Metric prep ----------

def compute_prison_rates() -> dict:
    """Read prison + undertrial rates and counts from L3 canonical only.

    Canonical metrics:
      prison-rate-per-100k.csv      value = rate per 100k of religious population
      undertrial-rate-per-100k.csv  same, undertrials only

    The absolute count is preserved on each canonical row in the `denominator`
    field as 'population_per_100k (count=N, pop=M)'. We parse it back here so
    the dashboard never touches L2/L3-raw data — every number it shows traces
    to a canonical row.

    Returns {'prison': {religion: {'count': int, 'rate_per_100k': float}},
             'undertrial': {...}}
    """
    import re as _re
    out: dict[str, dict] = {"prison": {}, "undertrial": {}}
    for kind, metric_id in (("prison", "prison-rate-per-100k"),
                            ("undertrial", "undertrial-rate-per-100k")):
        for row in load_metric(metric_id):
            if row["geography_level"] != "national":
                continue
            rel = row["religion"]
            rate = float(row["value"])
            m = _re.search(r"count=(\d+)", row["denominator"])
            count = int(m.group(1)) if m else 0
            out[kind][rel] = {"count": count, "rate_per_100k": rate}
    return out


MUSLIM_POP_SHARE = 14.23

# Map metric cluster (from metrics.yaml cluster field) to scorecard cluster display name.
# (Most just title-case the cluster id; civic/justice get explicit overrides for the dashboard.)
# Display sections group one or more metrics.yaml clusters under a single
# header. The fine-grained `cluster` stays on each metric (semantic); this is
# purely the dashboard's section layout. Order here = render order; empty
# sections (no live metric in any member cluster) are skipped.
SECTION_GROUPS = [
    ("Demographics", ["demographics"]),
    ("Education & Employment", ["education", "employment"]),
    ("Income", ["income"]),
    ("Health & Housing", ["health", "housing"]),
    ("Finance", ["finance"]),
    ("Representation", ["representation"]),
    ("Justice & Civic", ["justice", "civic"]),
]
SECTION_OF = {cid: name for name, cids in SECTION_GROUPS for cid in cids}


def load_scorecard_spec() -> list[tuple]:
    """Read display.scorecard blocks from manifest/metrics.yaml and build the
    SCORECARD_SPEC tuple list. SSOT discipline: scorecard config lives in the
    manifest, not hardcoded in dashboard code.

    Returns list of (cluster, metric_id, label, unit_format, reference, higher_is_better, special_render).
    """
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        data = _yaml.safe_load(f)
    specs = []
    for m in data["metrics"]:
        disp = m.get("display", {}).get("scorecard")
        if not disp:
            continue
        if disp.get("include", True) is False:
            continue
        # For prison-share / undertrial-share, scorecard pulls from prison-rate-per-100k
        # / undertrial-rate-per-100k metrics now — keep them out of the manifest-driven
        # scorecard if they don't have display blocks.
        # special_render is honored for ls-share, communal-incidents-govt, prison/undertrial
        special = disp.get("special_render")
        # Backward-compat: prison-rate-per-100k -> "prison-share" alias (renderer
        # in render_scorecard_rows still uses these IDs).
        mid = m["id"]
        if special == "prison_rate":
            mid = "prison-share"  # render_scorecard_rows special-cases this id
        elif special == "undertrial_rate":
            mid = "undertrial-share"
        specs.append((
            SECTION_OF.get(m["cluster"], m["cluster"].capitalize()),
            mid,
            disp["label"],
            disp["unit_format"],
            disp.get("reference"),
            disp.get("higher_is_better"),
        ))
    specs.sort(key=lambda s: next(
        (d["display"]["scorecard"]["order"] for d in data["metrics"]
         if d["id"] == s[1] or (d["id"] == "prison-rate-per-100k" and s[1] == "prison-share")
         or (d["id"] == "undertrial-rate-per-100k" and s[1] == "undertrial-share")
         if d.get("display", {}).get("scorecard")),
        9999,
    ))
    return specs


SCORECARD_SPEC = load_scorecard_spec()


def render_scorecard_rows() -> str:
    """Compute one HTML <tr> per metric showing Muslim/Hindu/All and gap vs reference."""
    prison_rates = compute_prison_rates()
    rows: list[str] = []
    for cluster, mid, name, unit, ref, higher_better in SCORECARD_SPEC:
        # Justice metrics get a special two-line presentation: absolute count + rate per 100k pop
        if mid in ("prison-share", "undertrial-share"):
            kind = "prison" if mid == "prison-share" else "undertrial"
            d = prison_rates[kind]
            year = 2022
            def cell(rel: str) -> str:
                x = d[rel]
                return f'<b>{x["count"]:,}</b><br><span class="rate-sub">{x["rate_per_100k"]} per 100k</span>'
            # Gap: rate ratio Muslim / Hindu
            ratio = d["muslim"]["rate_per_100k"] / d["hindu"]["rate_per_100k"]
            gap_str = f"{ratio:.2f}× Hindu rate"
            gap_class = "gap-bad" if ratio > 1 else "gap-good"
            rows.append(
                f'<tr>'
                f'<td>{html.escape(cluster)}</td>'
                f'<td>{html.escape(name)}</td>'
                f'<td>{year}</td>'
                f'<td>{cell("muslim")}</td>'
                f'<td>{cell("hindu")}</td>'
                f'<td>{cell("all")}</td>'
                f'<td class="{gap_class}">{html.escape(gap_str)}</td>'
                f'</tr>'
            )
            continue

        # Special case: time-series count metrics (communal-incidents-govt + -civic)
        if mid in ("communal-incidents-govt", "communal-incidents-civic"):
            data = load_metric(mid)
            if not data:
                continue
            latest = max(data, key=lambda r: int(r["year"]))
            val = int(float(latest["value"]))
            year = latest["year"]
            rows.append(
                f'<tr>'
                f'<td>{html.escape(cluster)}</td>'
                f'<td>{html.escape(name)}</td>'
                f'<td>{year}</td>'
                f'<td colspan="3" style="text-align:left">{val:,} (national aggregate)</td>'
                f'<td class="gap-neutral">{"NCRB tally; civic counts higher" if mid == "communal-incidents-govt" else "IHL: hate speech events, not riots"}</td>'
                f'</tr>'
            )
            continue

        # Special case: ls-share / mla-share — national row, gap vs 14.23% pop share
        if mid in ("ls-share", "mla-share"):
            data = load_metric(mid)
            # Filter to national row for the latest year
            nat = [r for r in data if r["geography_level"] == "national"]
            latest = max(nat, key=lambda r: int(r["year"])) if nat else None
            if latest is None:
                continue
            m_val = float(latest["value"])
            year = latest["year"]
            gap = m_val - MUSLIM_POP_SHARE
            sign = "+" if gap > 0 else ""
            rows.append(
                f'<tr>'
                f'<td>{html.escape(cluster)}</td>'
                f'<td>{html.escape(name)}</td>'
                f'<td>{year}</td>'
                f'<td>{m_val:.2f}%</td>'
                f'<td>—</td>'
                f'<td>—</td>'
                f'<td class="{"gap-bad" if gap < 0 else "gap-good"}">{sign}{gap:.2f}pp vs 14.23% pop</td>'
                f'</tr>'
            )
            continue

        data = load_metric(mid)
        # Find national row per religion
        by_rel: dict[str, float] = {}
        year = "—"
        for r in data:
            if r["geography_level"] != "national":
                continue
            by_rel[r["religion"]] = float(r["value"])
            year = r["year"]
        m_val = by_rel.get("muslim")
        h_val = by_rel.get("hindu")
        a_val = by_rel.get("all")
        muslim_str = fmt_num(m_val, unit) if m_val is not None else "—"
        hindu_str = fmt_num(h_val, unit) if h_val is not None else "—"
        all_str = fmt_num(a_val, unit) if a_val is not None else "—"

        # Gap computation
        gap_str = "—"
        gap_class = "gap-neutral"
        if ref == "hindu" and m_val is not None and h_val is not None:
            diff = m_val - h_val
            sign = "+" if diff > 0 else ""
            gap_str = f"{sign}{diff:.2f}"
            if unit == "percent":
                gap_str += "pp"
            elif unit == "females_per_1000_males":
                pass  # no unit suffix
            elif unit == "per_1000_live_births":
                pass
            # Class based on direction
            if higher_better is True:
                gap_class = "gap-bad" if diff < 0 else ("gap-good" if diff > 0 else "gap-neutral")
            elif higher_better is False:
                gap_class = "gap-bad" if diff > 0 else ("gap-good" if diff < 0 else "gap-neutral")
            else:
                gap_class = "gap-neutral"
        elif mid == "muslim-higher-ed-enrolment":
            gap_str = "n/a (no Hindu count in source)"
            gap_class = "gap-neutral"
        elif mid == "pop-share":
            gap_str = "baseline"
            gap_class = "gap-neutral"

        rows.append(
            f'<tr>'
            f'<td>{html.escape(cluster)}</td>'
            f'<td>{html.escape(name)}</td>'
            f'<td>{year}</td>'
            f'<td>{html.escape(muslim_str)}</td>'
            f'<td>{html.escape(hindu_str)}</td>'
            f'<td>{html.escape(all_str)}</td>'
            f'<td class="{gap_class}">{html.escape(gap_str)}</td>'
            f'</tr>'
        )
    return "\n    ".join(rows)


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Indian Muslims Living Conditions — Preview</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --fg: #1a1a1a;
    --muted: #666;
    --bg: #fafaf7;
    --card: #ffffff;
    --rule: #e6e3da;
    --muslim: #2b6cb0;
    --hindu:  #b76a2b;
    --all:    #5a6a5d;
    --accent: #7b1d22;
  }
  * { box-sizing: border-box; }
  body {
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text",
          "Helvetica Neue", Arial, sans-serif;
    color: var(--fg); background: var(--bg);
    margin: 0; padding: 0;
  }
  .page { max-width: 1080px; margin: 0 auto; padding: 32px 24px 80px; }
  h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }
  h2 { font-size: 20px; margin: 0 0 4px; letter-spacing: -0.01em; }
  .tagline { color: var(--muted); margin: 0 0 24px; font-size: 14px; }
  .status-bar {
    background: var(--card); border: 1px solid var(--rule); border-radius: 6px;
    padding: 14px 18px; margin-bottom: 32px;
    display: flex; gap: 24px; flex-wrap: wrap; font-size: 13px;
  }
  .status-bar b { color: var(--accent); }
  .status-bar span { color: var(--muted); }
  section.intro {
    background: #fff7f0; border-left: 4px solid var(--accent);
    padding: 14px 18px; margin-bottom: 24px; border-radius: 4px;
  }
  section.intro p { margin: 0 0 8px; font-size: 14px; color: #4a3a2a; }
  section.intro p:last-child { margin-bottom: 0; }
  section.intro a { color: var(--muslim); }
  section.intro i { font-style: italic; font-weight: 600; }
  .tile {
    background: var(--card); border: 1px solid var(--rule); border-radius: 6px;
    padding: 22px 24px; margin-bottom: 22px;
  }
  .tile-head { border-bottom: 1px solid var(--rule); padding-bottom: 12px; margin-bottom: 16px; }
  .source {
    font-size: 12px; color: var(--muted); margin: 2px 0 0;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .data-current {
    font-size: 11px; color: var(--muted); margin-top: 4px;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .headline {
    font-size: 38px; font-weight: 700; color: var(--accent);
    margin: 14px 0 2px; letter-spacing: -0.02em;
    font-feature-settings: "tnum";
  }
  .headline-caption { font-size: 13px; color: var(--muted); margin: 0 0 18px; }
  .methodology {
    font-size: 12.5px; color: var(--muted); margin: 14px 0 0;
    border-left: 3px solid var(--rule); padding-left: 12px;
  }
  .chart-wrap { margin: 18px 0; position: relative; height: 420px; }
  details {
    margin-top: 14px; border-top: 1px dashed var(--rule); padding-top: 12px;
  }
  details summary {
    cursor: pointer; font-size: 13px; color: var(--muted);
    list-style: none; user-select: none;
  }
  details summary::before {
    content: "▸ ";
    display: inline-block; transition: transform 0.15s;
  }
  details[open] summary::before { content: "▾ "; }
  table {
    width: 100%; border-collapse: collapse; margin-top: 12px;
    font-size: 13px; font-feature-settings: "tnum";
  }
  th, td {
    text-align: right; padding: 6px 10px;
    border-bottom: 1px solid var(--rule);
  }
  th:first-child, td:first-child { text-align: left; }
  th { font-weight: 600; color: var(--muted); font-size: 12px;
       text-transform: uppercase; letter-spacing: 0.04em; }
  tr.national td { font-weight: 700; background: #fff7f0; }
  .note {
    margin-top: 22px; padding: 14px 16px; border: 1px solid var(--rule);
    background: #faf7f0; border-radius: 4px; font-size: 13px; color: #5a4a2a;
  }
  .cluster-header {
    font-size: 14px; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 36px 0 10px; padding: 8px 0;
    border-top: 2px solid var(--rule);
  }
  .scorecard table { font-size: 13px; }
  .scorecard-table tbody tr:hover { background: #faf7f0; }
  .scorecard-table th.sortable {
    cursor: pointer; user-select: none;
  }
  .scorecard-table th.sortable:hover { color: var(--accent); }
  .scorecard-table th.sortable::after {
    content: " ⇅"; font-size: 10px; color: var(--rule);
  }
  .scorecard-table th.sorted-asc::after { content: " ↑"; color: var(--accent); }
  .scorecard-table th.sorted-desc::after { content: " ↓"; color: var(--accent); }
  .scorecard-table .gap-bad { color: var(--accent); font-weight: 600; }
  .scorecard-table .gap-good { color: #2d6a3e; font-weight: 600; }
  .scorecard-table .gap-neutral { color: var(--muted); }
  .scorecard-table .rate-sub {
    font-size: 11px; color: var(--muted); font-weight: 400;
  }
  .csv-link {
    font-size: 12px; color: var(--muslim); text-decoration: none;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    margin-left: 8px;
  }
  .csv-link:hover { text-decoration: underline; }
  footer {
    margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--rule);
    color: var(--muted); font-size: 12px;
  }
  footer code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    background: #efece4; padding: 1px 5px; border-radius: 3px;
  }
  /* --- Card grid (Hawaii-Dashboard-style rollout) --- */
  :root {
    --positive: #065F46; --negative: #991B1B; --neutral: #555555;
    --radius: 8px; --radius-pill: 999px;
    --shadow-card: 0 4px 14px rgba(0,0,0,.09);
    --t-2xs: .70rem; --t-xs: .75rem; --t-sm: .82rem; --t-base: .88rem;
  }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 16px; margin-bottom: 8px; }
  .card {
    background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
    padding: 18px 18px 14px; display: flex; flex-direction: column;
    transition: border-color .15s, box-shadow .15s, transform .15s;
  }
  .card:hover { border-color: var(--accent); box-shadow: var(--shadow-card); transform: translateY(-2px); }
  .card:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
  .card-metric { font-size: var(--t-sm); font-weight: 600; color: var(--fg); margin-bottom: 8px; line-height: 1.3; }
  .card-hero { display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }
  .card-value { font-size: 1.7rem; font-weight: 700; letter-spacing: -.02em; color: var(--accent); font-feature-settings: "tnum"; }
  .card-unit, .card-year { font-size: var(--t-sm); color: var(--muted); font-weight: 500; }
  .card-direction {
    align-self: flex-start; font-size: .62rem; font-weight: 600; color: var(--muted);
    background: var(--bg); padding: 1px 7px; border-radius: var(--radius-pill);
    margin-bottom: 8px; text-transform: uppercase; letter-spacing: .03em;
  }
  .card-chartwrap { width: 100%; margin: 2px 0 4px; position: relative; }
  .card-comparisons { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: auto; padding-top: 10px; border-top: 1px solid var(--rule); }
  .card-comp { text-align: center; padding: 5px 4px; border-radius: 6px; }
  .comp-label { font-size: var(--t-xs); color: var(--muted); font-weight: 500; margin-bottom: 2px; }
  .comp-verdict { font-size: var(--t-base); font-weight: 700; font-feature-settings: "tnum"; }
  .comp-detail { font-size: var(--t-2xs); color: var(--muted); margin-top: 1px; }
  .card-comp.positive .comp-verdict, .card-comp.good .comp-verdict { color: var(--positive); }
  .card-comp.negative .comp-verdict, .card-comp.bad .comp-verdict { color: var(--negative); }
  .card-comp.neutral .comp-verdict, .card-comp.mid .comp-verdict { color: var(--neutral); }
  .comp-note { grid-column: 1 / -1; text-align: left; font-size: var(--t-xs); color: var(--muted); line-height: 1.45; }
  .card-foot { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--rule); display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: var(--t-2xs); color: var(--muted); }
  .card-foot a { color: var(--muslim); text-decoration: none; font-weight: 500; }
  .card-foot a:hover { text-decoration: underline; }
  .card details { margin-top: 10px; border-top: 1px dashed var(--rule); padding-top: 8px; }
  .card details summary { font-size: var(--t-xs); }
  .card details table { font-size: 12px; }
  @media (max-width: 560px) { .cards { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="page">

<h1>Indian Muslims — Living Conditions Dashboard</h1>
<p class="tagline">Built {timestamp} · <a href="https://github.com/iqbash1/indian-muslims-dashboard">source on GitHub</a></p>

<section class="intro">
  <p>A scorecard of living-conditions indicators for India's Muslim population, with
  Hindu and all-India comparison baselines on every metric. The gap between Muslim
  outcomes and these baselines is the story this dashboard is built around —
  inheriting the Sachar Committee (2006) methodology of focused, comparative measurement.</p>
  <p>Each metric is a card showing the Muslim value, where it ranks among religious
  communities (the analog of a US state's rank), and — where the source has multiple
  survey rounds — how it has changed over time, with the source linked to its canonical
  CSV. Click any scorecard column to sort. Numbers tagged <i>"paradox"</i> are ones where
  Muslim outcomes run <i>ahead of</i> Hindu — notably infant survival, women's anaemia, and
  sex ratio. These coexist with persistent Muslim disadvantage on the socioeconomic,
  representation, and justice indicators.</p>
</section>

<div class="status-bar">
  <span><b>{n_metrics}</b> metrics live</span>
  <span><b>{n_sources}</b> sources archived</span>
  <span><b>{n_rows}</b> canonical rows · all schema-valid</span>
  <span>Comparison baseline on every applicable card</span>
</div>

<!-- SCORECARD -->
<section class="tile scorecard">
  <div class="tile-head">
    <h2>Scorecard — all metrics at a glance</h2>
    <p class="data-current">Muslim outcome vs Hindu/All baseline · sorted by gap magnitude</p>
  </div>
  <table class="scorecard-table" id="scorecard"><thead><tr>
    <th class="sortable" data-col="0">Cluster</th>
    <th class="sortable" data-col="1">Metric</th>
    <th class="sortable" data-col="2">Year</th>
    <th class="sortable" data-col="3">Muslim</th>
    <th class="sortable" data-col="4">Hindu</th>
    <th class="sortable" data-col="5">All</th>
    <th class="sortable" data-col="6">Gap vs reference</th>
  </tr></thead><tbody>
    {scorecard_rows}
  </tbody></table>
  <p class="methodology">"Gap" is Muslim minus reference baseline (Hindu where available, else All).
  Red gap = Muslim outcome worse than reference; green = Muslim outcome better. For justice
  metrics, cells show absolute count + incarceration rate per 100k of religious population;
  gap is the Muslim-to-Hindu rate ratio (1.0× = parity, >1.0× = Muslim overrepresented).</p>
</section>

{cluster_grids}

<footer>
  <p>Built by <code>dashboard/build.py</code> from <code>canonical/*.csv</code> at {timestamp}.
  Every number on this page traces L4 → L3 (canonical) → L2 (extracted) → L1 (source file)
  with SHA256 sidecar provenance. Re-run the builder after any canonical change:
  <code>python dashboard/build.py</code></p>
</footer>

</div>

<script>
// Sortable scorecard table. Click a column header to sort.
(function setupSortableScorecard() {
  const table = document.getElementById('scorecard');
  if (!table) return;
  const headers = table.querySelectorAll('th.sortable');
  let lastSorted = { col: -1, dir: 1 };

  const sortKey = (cellText, col) => {
    const t = cellText.trim();
    // Numeric extraction: pull first numeric token (handles "33.0 per 1000", "1.59× Hindu rate", etc.)
    const m = t.match(/-?[0-9,]+[.]?[0-9]*/);
    if (m && col >= 2) return parseFloat(m[0].replace(/,/g, ''));
    return t.toLowerCase();
  };

  headers.forEach(h => {
    h.addEventListener('click', () => {
      const col = parseInt(h.dataset.col);
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const dir = (lastSorted.col === col) ? -lastSorted.dir : 1;
      rows.sort((a, b) => {
        const ka = sortKey(a.cells[col].textContent, col);
        const kb = sortKey(b.cells[col].textContent, col);
        if (ka < kb) return -1 * dir;
        if (ka > kb) return 1 * dir;
        return 0;
      });
      rows.forEach(r => tbody.appendChild(r));
      headers.forEach(x => x.classList.remove('sorted-asc', 'sorted-desc'));
      h.classList.add(dir === 1 ? 'sorted-asc' : 'sorted-desc');
      lastSorted = { col, dir };
    });
  });
})();

// Returns a FRESH config object on every call. Chart.js mutates the option
// objects it is given (it bakes resolved scale `type` into scales.x/scales.y).
// A shared const would let the first vertical chart pin x:'category'/y:'linear',
// which then overrides indexAxis:'y' on later horizontal charts and blanks them.
function cfgBase() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { font: { size: 12 } } },
      tooltip: { titleFont: { size: 12 }, bodyFont: { size: 12 } },
    },
    scales: {
      // Value axis does not force a zero baseline; it hugs the data range so
      // small gaps between groups stay legible. `grace` keeps bars off the edges.
      y: { beginAtZero: false, grace: '5%', ticks: { font: { size: 11 } } },
      x: { ticks: { font: { size: 11 }, maxRotation: 60, minRotation: 60 } },
    },
  };
}

// Muslim/Hindu/All horizontal comparison tiles. Value axis is x and does NOT
// force a zero baseline — the axis hugs the data range so the (often small) gap
// between groups is legible. A small `grace` keeps the shortest bar a visible
// sliver instead of zero-width. Category axis is y. (Own fresh config per call.)
function hCompare() {
  const c = cfgBase();
  c.indexAxis = 'y';
  c.plugins.legend = { display: false };
  c.scales.x = { beginAtZero: false, grace: '5%', ticks: { font: { size: 11 } } };
  return c;
}

// --- Card-grid chart helpers (generated card initialisers call these) ---
function _valueLabels(decimals, suffix) {
  return { id: 'vl', afterDatasetsDraw(chart) {
    const { ctx } = chart; const meta = chart.getDatasetMeta(0);
    ctx.save(); ctx.font = '600 11px -apple-system, system-ui, sans-serif';
    ctx.textBaseline = 'middle'; ctx.fillStyle = '#555';
    meta.data.forEach((bar, i) => { const v = chart.data.datasets[0].data[i];
      ctx.fillText(v.toFixed(decimals) + suffix, bar.x + 6, bar.y); });
    ctx.restore();
  } };
}
// "All-India" is a weighted aggregate that CONTAINS every community, so it is
// never a peer bar. It is drawn as a dashed baseline reference line (the same
// way the Hawaiʻi dashboard draws the US reference), passed via refValue.
function _refLine(refValue, refLabel) {
  return { id: 'refline', afterDatasetsDraw(chart) {
    if (refValue == null) return;
    const { ctx, chartArea: { top, bottom }, scales: { x } } = chart;
    const px = x.getPixelForValue(refValue);
    ctx.save();
    ctx.strokeStyle = '#9aa3a8'; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(px, top); ctx.lineTo(px, bottom); ctx.stroke();
    ctx.setLineDash([]);
    ctx.font = '600 9px -apple-system, system-ui, sans-serif';
    ctx.fillStyle = '#9aa3a8'; ctx.textAlign = 'center';
    ctx.fillText(refLabel, px, top - 3);
    ctx.restore();
  } };
}
function hbar(id, labels, values, colors, suffix, decimals, refValue, refLabel) {
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 3, barPercentage: 0.82, categoryPercentage: 0.86 }] },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false, animation: false,
      layout: { padding: { right: 46, top: 14 } },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => c.parsed.x.toFixed(decimals) + suffix } } },
      scales: { x: { display: false, grace: '8%', beginAtZero: false }, y: { grid: { display: false }, border: { display: false }, ticks: { font: { size: 11 } } } },
    },
    plugins: [_valueLabels(decimals, suffix), _refLine(refValue == null ? null : refValue, refLabel)],
  });
}
function vbar(id, labels, values, color, suffix) {
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels: labels, datasets: [{ data: values, backgroundColor: color, borderRadius: 3 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => c.parsed.y.toFixed(1) + suffix } } },
      scales: { y: { beginAtZero: false, grace: '8%', ticks: { font: { size: 10 } } }, x: { ticks: { font: { size: 9 }, maxRotation: 60, minRotation: 60 }, grid: { display: false } } },
    },
  });
}
function lineChart(id, labels, values, color, suffix) {
  new Chart(document.getElementById(id), {
    type: 'line',
    data: { labels: labels, datasets: [{ data: values, borderColor: color, backgroundColor: 'rgba(43,108,176,.12)', fill: true, tension: 0.3, pointRadius: 3, pointBackgroundColor: color }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => c.parsed.y + suffix } } },
      scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } }, y: { beginAtZero: false, grace: '10%', ticks: { font: { size: 10 } } } },
    },
  });
}

// Multi-round trend: Muslim (solid accent) vs Hindu (dashed reference) over
// survey rounds. hasBreak → Muslim line dashed too (cross-round comparability
// caveat, e.g. anaemia). Value axis hugs the data (no forced zero baseline).
function trendChart(id, years, muslim, hindu, suffix, hasBreak) {
  new Chart(document.getElementById(id), {
    type: 'line',
    data: { labels: years, datasets: [
      { label: 'Muslim', data: muslim, borderColor: '#7b1d22', backgroundColor: 'rgba(123,29,34,.07)',
        fill: true, tension: 0.25, pointRadius: 3, pointBackgroundColor: '#7b1d22',
        borderDash: hasBreak ? [5, 4] : [], spanGaps: false },
      { label: 'Hindu', data: hindu, borderColor: '#9aa3a8', backgroundColor: 'transparent',
        fill: false, tension: 0.25, pointRadius: 2, pointBackgroundColor: '#9aa3a8',
        borderDash: [4, 3], spanGaps: false },
    ]},
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: {
        legend: { display: true, position: 'top', align: 'end', labels: { boxWidth: 10, font: { size: 9 } } },
        tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + c.parsed.y + suffix } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { beginAtZero: false, grace: '12%', ticks: { font: { size: 10 } } },
      },
    },
  });
}

{card_charts}
</script>
</body>
</html>
"""


def build() -> None:
    # Status-bar counts derived from canonical (SSOT — never goes stale).
    n_metrics = len(SCORECARD_SPEC)
    n_rows, source_ids = 0, set()
    for cpath in sorted(CANONICAL_DIR.glob("*.csv")):
        with cpath.open() as f:
            for row in csv.DictReader(f):
                n_rows += 1
                if row.get("source_id"):
                    source_ids.add(row["source_id"])
    n_sources = len(source_ids)

    cluster_grids, card_charts = render_all_clusters()

    substitutions = {
        "{timestamp}": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "{n_metrics}": str(n_metrics),
        "{n_sources}": str(n_sources),
        "{n_rows}": str(n_rows),
        "{scorecard_rows}": render_scorecard_rows(),
        "{cluster_grids}": cluster_grids,
        "{card_charts}": card_charts,
    }
    html_out = TEMPLATE
    for k, v in substitutions.items():
        html_out = html_out.replace(k, v)

    import shutil as _shutil

    # Copy canonical CSVs into the publish folder so the download links resolve.
    # (Card footers link the source NAME directly to its canonical/*.csv — see
    # _card_shell — so no path-text auto-linkification is needed here.)
    publish_canonical = OUT_PATH.parent / "canonical"
    publish_canonical.mkdir(exist_ok=True)
    for csv_path in CANONICAL_DIR.glob("*.csv"):
        _shutil.copy2(csv_path, publish_canonical / csv_path.name)

    # Ensure a .nojekyll is inside the publish folder so GitHub Pages serves the
    # HTML as-is without Jekyll processing (root-level .nojekyll doesn't apply
    # when publishing from a subfolder).
    (OUT_PATH.parent / ".nojekyll").touch()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html_out)
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} ({len(html_out):,} bytes)")


# ============================================================================
# Education card-grid prototype (Hawaii-Dashboard-style, multi-community)
#
# Non-destructive: writes a standalone docs/preview-education-cards.html so the
# new layout can be diffed against the current build before any rewrite.
# Demonstrates two patterns learned from hawaiidashboard.org:
#   (1) compact card grid with polarity pill + two-up comparison block, and
#   (2) "rank among communities" — the Muslim-vs-49-other-states analog, now
#       possible because lit-7plus canonical carries all six named communities.
# ============================================================================

NAMED_COMMUNITIES = ("hindu", "muslim", "christian", "sikh", "buddhist", "jain")
COMMUNITY_LABEL = {
    "hindu": "Hindu", "muslim": "Muslim", "christian": "Christian",
    "sikh": "Sikh", "buddhist": "Buddhist", "jain": "Jain",
    "all": "All", "other": "Other",
}
# Tier text colors mirror the Hawaii pattern: top third green, bottom third
# red, middle muted grey ("neutral isn't worth shouting about").
TIER_HEX = {"good": "#065F46", "mid": "#555555", "bad": "#991B1B"}


def _ordinal(k: int) -> str:
    suffix = "th" if 10 <= k % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(k % 10, "th")
    return f"{k}{suffix}"


def community_rank(by_religion: dict[str, float], higher_is_better: bool):
    """Rank 'muslim' among the named communities present. rank 1 = best.

    Returns (rank, n, tier, ordered_pairs) where ordered_pairs is the list of
    (community, value) sorted best-first, and tier is good/mid/bad by thirds.
    """
    present = [(c, by_religion[c]) for c in NAMED_COMMUNITIES if c in by_religion]
    present.sort(key=lambda kv: kv[1], reverse=bool(higher_is_better))
    order = [c for c, _ in present]
    n = len(order)
    if n == 0 or "muslim" not in order:
        return 0, n, "mid", present
    rank = order.index("muslim") + 1
    if rank <= n / 3:
        tier = "good"
    elif rank > 2 * n / 3:
        tier = "bad"
    else:
        tier = "mid"
    return rank, n, tier, present


# ============================================================================
# Full card-grid rollout — generic, manifest-driven renderer for index.html.
# Replaces the former hand-written single-column tiles. Each live metric (those
# with a display.scorecard block) becomes one Hawaii-style card. The comparison
# block adapts: a "rank among communities" tier where >=4 named communities are
# present (e.g. literacy), else the Muslim-vs-Hindu / vs-All gap.
# ============================================================================

# Plain-language caption shown next to each headline value (Hawaii-style).
CAPTION = {
    "lit-7plus": "literate, age 7+",
    "sex-ratio": "females per 1,000 males",
    "lfpr-15plus": "in the labour force, 15+",
    "wpr-15plus": "working, 15+",
    "salaried-share": "in regular salaried work",
    "imr": "deaths per 1,000 live births",
    "inst-delivery": "of births in a facility",
    "women-anemia": "of women 15–49 anaemic",
    "improved-sanitation": "of households have a toilet",
    "pop-share": "of total population",
    "district-concentration-top100": "of Muslims in top-100 districts",
    "muslim-higher-ed-enrolment": "students",
    "ls-share": "of 543 Lok Sabha seats",
    "mla-share": "of state-assembly seats (agg.)",
    "prison-rate-per-100k": "per 100k Muslims",
    "undertrial-rate-per-100k": "per 100k Muslims",
    "communal-incidents-govt": "incidents (NCRB)",
    "communal-incidents-civic": "hate-speech events (IHL)",
}
# (suffix, decimals) for chart value labels, keyed by unit_format.
UNIT_JS = {
    "percent": ("%", 1), "females_per_1000_males": ("", 0),
    "per_1000_live_births": ("", 1), "rate_per_100k": ("", 1), "count": ("", 0),
}
SOURCE_LABEL = {
    "census-india-2011": "Census 2011 · C-series",
    "nfhs-5": "NFHS-5 (2019-21)", "plfs": "PLFS 2023-24", "aishe": "AISHE 2021-22",
    "ncrb-prison": "NCRB PSI 2022", "ncrb-crime": "NCRB CII 2022",
    "prs-eci-affidavits": "PRS / ECI affidavits", "civic-incident-databases": "India Hate Lab",
}


def _verdict(gap: float, hib) -> str:
    """good / bad / neutral for a Muslim-minus-reference gap given polarity."""
    if hib is None or gap == 0:
        return "neutral"
    return "good" if ((gap > 0) if hib else (gap < 0)) else "bad"


def _gap_str(gap: float, unit: str) -> str:
    if unit == "count":
        return f"{gap:+,.0f}"
    return f"{gap:+.1f}{'pp' if unit == 'percent' else ''}"


def _verdict_word(cls: str) -> str:
    return {"good": "ahead", "bad": "behind", "neutral": "—"}[cls]


def _tier_word(tier: str) -> str:
    return {"good": "top tier", "mid": "middle tier", "bad": "bottom tier"}[tier]


def _year_of(metric_id: str):
    yrs = [int(r["year"]) for r in load_metric(metric_id) if r["geography_level"] == "national"]
    return max(yrs) if yrs else ""


def _comp(label: str, verdict: str, detail: str, cls: str) -> str:
    return (f'<div class="card-comp {cls}"><div class="comp-label">{html.escape(label)}</div>'
            f'<div class="comp-verdict">{html.escape(verdict)}</div>'
            f'<div class="comp-detail">{html.escape(detail)}</div></div>')


def _card_shell(label, value, unit_txt, year, polarity, chart_html, comps_html,
                src, csv_href, details_html="") -> str:
    pill = f'<div class="card-direction">{html.escape(polarity)}</div>' if polarity else ""
    yr = f'<span class="card-year">({html.escape(str(year))})</span>' if year else ""
    return (
        '<section class="card">'
        f'<div class="card-metric">{html.escape(label)}</div>'
        f'<div class="card-hero"><span class="card-value">{value}</span>'
        f'<span class="card-unit">{html.escape(unit_txt)}</span>{yr}</div>'
        f'{pill}{chart_html}'
        f'<div class="card-comparisons">{comps_html}</div>'
        f'{details_html}'
        # The source NAME is the hyperlink (target = the canonical CSV); the raw
        # path is not shown. Built directly here — no post-processing linkifier.
        f'<div class="card-foot">'
        f'<a href="{html.escape(csv_href)}">{html.escape(src)}</a>'
        f'</div>'
        '</section>'
    )


def _state_details(metric_id: str, unit: str) -> str:
    from collections import defaultdict
    rows = load_metric(metric_id)
    by_geo: dict[str, dict] = defaultdict(dict)
    for r in rows:
        if r["geography_level"] == "state":
            by_geo[r["geography_code"]][r["religion"]] = float(r["value"])
    if not by_geo:
        return ""
    has_hindu = any("hindu" in v for v in by_geo.values())
    order = sorted(by_geo, key=lambda g: by_geo[g].get("muslim", 0))
    head = "<tr><th>State / UT</th><th>Muslim</th>" + ("<th>Hindu</th>" if has_hindu else "") + "</tr>"
    trs = []
    for g in order:
        b = by_geo[g]
        cells = (f"<td>{html.escape(state_label(g))}</td>"
                 f"<td>{fmt_num(b['muslim'], unit) if 'muslim' in b else '—'}</td>")
        if has_hindu:
            cells += f"<td>{fmt_num(b['hindu'], unit) if 'hindu' in b else '—'}</td>"
        trs.append(f"<tr>{cells}</tr>")
    return (f'<details><summary>Full state data ({len(order)} states)</summary>'
            f'<table><thead>{head}</thead><tbody>{"".join(trs)}</tbody></table></details>')


def _nat_by_religion(metric_id: str) -> dict:
    """National {religion: value} for the LATEST year present (avoids multi-year collision)."""
    nat = [r for r in load_metric(metric_id) if r["geography_level"] == "national"]
    if not nat:
        return {}
    latest = max(int(r["year"]) for r in nat)
    return {r["religion"]: float(r["value"]) for r in nat if int(r["year"]) == latest}


def _nat_trend(metric_id: str):
    """Return (years_sorted, {religion:{year:value}}, has_break) for national rows."""
    nat = [r for r in load_metric(metric_id) if r["geography_level"] == "national"]
    years = sorted({int(r["year"]) for r in nat})
    series: dict = {}
    has_break = False
    for r in nat:
        series.setdefault(r["religion"], {})[int(r["year"])] = float(r["value"])
        if str(r.get("break_flag", "")).strip().lower() in ("true", "1", "yes"):
            has_break = True
    return years, series, has_break


def _community_table(nat: dict, unit: str, hib) -> str:
    """<details> table of the latest-year value per named community, Muslim marked."""
    rows = [(COMMUNITY_LABEL[c], nat[c], c == "muslim") for c in NAMED_COMMUNITIES if c in nat]
    if hib is not None:
        rows.sort(key=lambda b: b[1], reverse=bool(hib))
    trs = []
    for name, val, is_m in rows:
        cls = ' style="font-weight:700;color:var(--accent)"' if is_m else ""
        trs.append(f"<tr{cls}><td>{html.escape(name)}</td><td>{fmt_num(val, unit)}</td></tr>")
    return ("<details><summary>By community (latest year)</summary>"
            "<table><thead><tr><th>Community</th><th>Value</th></tr></thead>"
            f"<tbody>{''.join(trs)}</tbody></table></details>")


def render_metric_card(m: dict):
    """Return (card_html, chart_js_or_None) for one live metric."""
    mid = m["id"]
    disp = m["display"]["scorecard"]
    label = m.get("name", disp["label"])  # full metric name on the card (scorecard keeps the short label)
    unit = disp["unit_format"]
    hib = disp.get("higher_is_better", m.get("higher_is_better"))
    special = disp.get("special_render")
    src = SOURCE_LABEL.get(m.get("sources", {}).get("primary"), m.get("sources", {}).get("primary", ""))
    csv_href = f"canonical/{mid}.csv"
    cvid = "cc-" + mid
    suffix, dec = UNIT_JS.get(unit, ("", 1))

    if special in ("prison_rate", "undertrial_rate"):
        return _card_rate(mid, label, src, csv_href, cvid)
    if special == "time_series_latest":
        return _card_timeseries(mid, label, unit, src, csv_href, cvid)
    if special == "time_series_count":
        return _card_ts_count(mid, label, src, csv_href, cvid)
    if mid in ("pop-share", "district-concentration-top100", "muslim-higher-ed-enrolment"):
        return _card_muslim_only(mid, label, unit, src, csv_href, cvid)
    return _card_comparison(mid, label, unit, hib, src, csv_href, cvid, suffix, dec)


def _card_comparison(mid, label, unit, hib, src, csv_href, cvid, suffix, dec):
    nat = _nat_by_religion(mid)
    muslim, hindu, all_v = nat.get("muslim"), nat.get("hindu"), nat.get("all")
    headline = fmt_num(muslim, unit) if muslim is not None else "—"
    polarity = "higher is better" if hib is True else ("lower is better" if hib is False else "")

    named = [c for c in NAMED_COMMUNITIES if c in nat]
    rank = n = 0
    if len(named) >= 4 and hib is not None:
        rank, n, tier, _ = community_rank(nat, bool(hib))
    elif hindu is not None:
        tier = {"good": "good", "bad": "bad", "neutral": "mid"}[_verdict(muslim - hindu, hib)]
    else:
        tier = "mid"

    # Comparison block (latest year): vs-Hindu gap + rank-among-communities (or vs-All).
    comps = ""
    if hindu is not None:
        gap = muslim - hindu
        cls = _verdict(gap, hib)
        comps += _comp("vs Hindu", _gap_str(gap, unit), _verdict_word(cls), cls)
    if rank:
        comps += _comp("Among communities", f"{_ordinal(rank)} of {n}", _tier_word(tier), tier)
    elif all_v is not None:
        gap = muslim - all_v
        cls = _verdict(gap, hib)
        comps += _comp("vs All-India", _gap_str(gap, unit), _verdict_word(cls), cls)

    years, series, has_break = _nat_trend(mid)
    if len(years) >= 2:
        # TIME SERIES card: Muslim trend (solid) vs Hindu (dashed reference) over
        # rounds; full latest-year community ranking moves to a <details> table.
        m_series = [series.get("muslim", {}).get(y) for y in years]
        h_series = [series.get("hindu", {}).get(y) for y in years]
        chart_html = f'<div class="card-chartwrap" style="height:150px"><canvas id="{cvid}"></canvas></div>'
        js = (f'trendChart("{cvid}", {json.dumps(years)}, {json.dumps(m_series)}, '
              f'{json.dumps(h_series)}, {json.dumps(suffix)}, {json.dumps(bool(has_break))});')
        details = _community_table(nat, unit, hib)
    else:
        # SNAPSHOT card: community bar with the All-India dashed baseline.
        pairs = [(COMMUNITY_LABEL[c], nat[c], c == "muslim") for c in named]
        if hib is not None:
            pairs.sort(key=lambda b: b[1], reverse=bool(hib))
        labels = [p[0] for p in pairs]
        values = [round(p[1], 4) for p in pairs]
        mhex = TIER_HEX.get(tier, "#555555")
        colors = [mhex if p[2] else "#D8DEE2" for p in pairs]
        h = len(pairs) * 28 + 28
        chart_html = f'<div class="card-chartwrap" style="height:{h}px"><canvas id="{cvid}"></canvas></div>'
        ref = json.dumps(round(all_v, 4)) if all_v is not None else "null"
        js = (f'hbar("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, {json.dumps(colors)}, '
              f'{json.dumps(suffix)}, {dec}, {ref}, "All-India");')
        details = _state_details(mid, unit)

    return _card_shell(label, headline, CAPTION.get(mid, ""), _year_of(mid), polarity,
                       chart_html, comps, src, csv_href, details), js


def _card_muslim_only(mid, label, unit, src, csv_href, cvid):
    nat = _nat_by_religion(mid)
    muslim = nat.get("muslim")
    headline = fmt_num(muslim, unit) if muslim is not None else "—"
    chart_html, js, note = "", None, ""
    if mid == "pop-share":
        st = [(state_label(r["geography_code"]), float(r["value"]))
              for r in load_metric(mid) if r["geography_level"] == "state"]
        st.sort(key=lambda x: -x[1])
        st = st[:8]
        chart_html = f'<div class="card-chartwrap" style="height:200px"><canvas id="{cvid}"></canvas></div>'
        js = f'vbar("{cvid}", {json.dumps([s[0] for s in st])}, {json.dumps([round(s[1], 2) for s in st])}, "#2b6cb0", "%");'
        note = "Baseline metric — Muslim share of total population. Top-8 states shown; no community ranking."
    elif mid == "district-concentration-top100":
        # Two-bar split: the top-100 districts vs every other district. Directly
        # visualises the concentration the headline measures.
        rest = round(100 - muslim, 2)
        chart_html = f'<div class="card-chartwrap" style="height:92px"><canvas id="{cvid}"></canvas></div>'
        js = (f'hbar("{cvid}", {json.dumps(["Top-100 districts", "Other districts"])}, '
              f'{json.dumps([round(muslim, 2), rest])}, {json.dumps(["#7b1d22", "#D8DEE2"])}, '
              f'"%", 1, null, "");')
        note = ("Share of all Indian Muslims living in the 100 most Muslim-populous districts — "
                "a geographic-concentration measure, not a community comparison.")
    else:  # muslim-higher-ed-enrolment
        # Top-8 states by Muslim enrolment, shown in thousands (the national
        # headline is the absolute total; no community comparator exists).
        st = [(state_label(r["geography_code"]), float(r["value"]))
              for r in load_metric(mid) if r["geography_level"] == "state"]
        st.sort(key=lambda x: -x[1])
        st = st[:8]
        if st:
            chart_html = f'<div class="card-chartwrap" style="height:{len(st) * 26 + 20}px"><canvas id="{cvid}"></canvas></div>'
            labels = [s[0] for s in st]
            vals = [round(s[1] / 1000) for s in st]
            js = (f'hbar("{cvid}", {json.dumps(labels)}, {json.dumps(vals)}, '
                  f'{json.dumps(["#2b6cb0"] * len(st))}, "k", 0, null, "");')
        note = ("No community ranking — AISHE tabulates “Muslim Minority” enrolment separately; "
                "other communities are not enumerated in the same table. Top-8 states shown (thousands).")
    comps = f'<div class="comp-note">{html.escape(note)}</div>'
    return _card_shell(label, headline, CAPTION.get(mid, ""), _year_of(mid), "",
                       chart_html, comps, src, csv_href, _state_details(mid, unit)), js


def _card_rate(mid, label, src, csv_href, cvid):
    kind = "prison" if "prison" in mid else "undertrial"
    r = compute_prison_rates()[kind]
    rate_by = {rel: r[rel]["rate_per_100k"] for rel in r}
    muslim, hindu, allr = rate_by.get("muslim"), rate_by.get("hindu"), rate_by.get("all")
    ratio = round(muslim / hindu, 2) if hindu else 0
    # Bars are real communities; "All-India" (which contains them all) is the
    # dashed baseline. Incarceration rate is lower-is-better, so rank ascends.
    named = [c for c in NAMED_COMMUNITIES if c in rate_by]
    if len(named) >= 4:
        rank, n, tier, _ = community_rank(rate_by, higher_is_better=False)
    else:
        rank, n, tier = 0, 0, "bad"
    pairs = sorted([(COMMUNITY_LABEL[c], rate_by[c], c == "muslim") for c in named],
                   key=lambda b: b[1])
    labels = [p[0] for p in pairs]
    values = [round(p[1], 1) for p in pairs]
    mhex = TIER_HEX.get(tier, "#991B1B")
    colors = [mhex if p[2] else "#D8DEE2" for p in pairs]
    h = len(pairs) * 28 + 28
    chart_html = f'<div class="card-chartwrap" style="height:{h}px"><canvas id="{cvid}"></canvas></div>'
    ref = json.dumps(round(allr, 1)) if allr is not None else "null"
    js = (f'hbar("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, {json.dumps(colors)}, '
          f'"", 1, {ref}, "All-India");')
    comps = _comp("vs Hindu rate", f"{ratio}×", f"{r['muslim']['count']:,} held", "bad")
    if rank:
        comps += _comp("Among communities", f"{_ordinal(rank)} of {n}", _tier_word(tier), tier)
    else:
        comps += _comp("Muslims held", f"{r['muslim']['count']:,}", "absolute count", "neutral")
    return _card_shell(label, f"{muslim:.1f}", CAPTION.get(mid, "per 100k"), 2022,
                       "lower is better", chart_html, comps, src, csv_href), js


def _card_timeseries(mid, label, unit, src, csv_href, cvid):
    rows = sorted([r for r in load_metric(mid) if r["geography_level"] == "national"],
                  key=lambda r: int(r["year"]))
    latest = rows[-1] if rows else None
    val = float(latest["value"]) if latest else None
    headline = fmt_num(val, unit) if val is not None else "—"
    gap = (val - MUSLIM_POP_SHARE) if val is not None else 0
    comps = _comp("vs population", f"{gap:+.1f}pp", "vs 14.2% pop share", "bad" if gap < 0 else "good")
    chart_html, js = "", None
    if len(rows) >= 2:
        labels = [int(r["year"]) for r in rows]
        values = [round(float(r["value"]), 2) for r in rows]
        chart_html = f'<div class="card-chartwrap" style="height:150px"><canvas id="{cvid}"></canvas></div>'
        js = f'lineChart("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, "#2b6cb0", "%");'
        comps += _comp("trend", f"{labels[0]}–{labels[-1]}", f"{values[0]:.1f}% → {values[-1]:.1f}%", "neutral")
    else:
        st = sorted([(state_label(r["geography_code"]), float(r["value"]))
                     for r in load_metric(mid) if r["geography_level"] == "state"],
                    key=lambda x: -x[1])
        if st:
            h = len(st) * 26 + 20
            chart_html = f'<div class="card-chartwrap" style="height:{h}px"><canvas id="{cvid}"></canvas></div>'
            js = (f'hbar("{cvid}", {json.dumps([s[0] for s in st])}, '
                  f'{json.dumps([round(s[1], 2) for s in st])}, '
                  f'{json.dumps(["#2b6cb0"] * len(st))}, "%", 1);')
        comps += _comp("national agg", headline, "across assemblies", "neutral")
    return _card_shell(label, headline, CAPTION.get(mid, ""), latest["year"] if latest else "",
                       "", chart_html, comps, src, csv_href), js


def _card_ts_count(mid, label, src, csv_href, cvid):
    rows = sorted([r for r in load_metric(mid) if r["geography_level"] == "national"],
                  key=lambda r: int(r["year"]))
    latest = rows[-1] if rows else None
    val = int(float(latest["value"])) if latest else 0
    comps = ""
    chart_html, js = "", None
    if len(rows) >= 2:
        labels = [int(r["year"]) for r in rows]
        values = [int(float(r["value"])) for r in rows]
        chart_html = f'<div class="card-chartwrap" style="height:150px"><canvas id="{cvid}"></canvas></div>'
        js = f'lineChart("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, "#7b1d22", "");'
        comps += _comp("trend", f"{labels[0]}–{labels[-1]}", f"{values[0]:,} → {val:,}", "neutral")
    comps += _comp("latest year", str(latest["year"]) if latest else "—", "national count", "neutral")
    return _card_shell(label, f"{val:,}", CAPTION.get(mid, "events"), latest["year"] if latest else "",
                       "lower is better", chart_html, comps, src, csv_href), js


def render_all_clusters():
    """Group live metrics into the SECTION_GROUPS display sections and render each
    as a card grid. Within a section, cards order by scorecard `order`.

    Returns (clusters_html, charts_js).
    """
    from collections import defaultdict
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        man = _yaml.safe_load(f)
    by_cluster: dict[str, list] = defaultdict(list)
    for m in man["metrics"]:
        disp = m.get("display", {}).get("scorecard")
        if not disp or disp.get("include", True) is False:
            continue
        by_cluster[m["cluster"]].append(m)

    grids, charts = [], []
    for name, cluster_ids in SECTION_GROUPS:
        ms = [m for cid in cluster_ids for m in by_cluster.get(cid, [])]
        if not ms:
            continue
        ms.sort(key=lambda m: m["display"]["scorecard"].get("order", 999))
        cards = []
        for m in ms:
            card_html, js = render_metric_card(m)
            cards.append(card_html)
            if js:
                charts.append(js)
        grids.append(f'<h2 class="cluster-header">{html.escape(name)}</h2>\n'
                     f'<div class="cards">\n{"".join(cards)}\n</div>')
    return "\n\n".join(grids), "\n".join(charts)


if __name__ == "__main__":
    build()
