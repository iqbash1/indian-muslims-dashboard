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

# ----- Site identity (used in <title>, canonical URL, JSON-LD, sitemap) -----
SITE_DOMAIN = "muslimdata.in"
SITE_URL = f"https://{SITE_DOMAIN}"
SITE_TITLE = "muslimdata.in: the state of Muslim India, in data"
SITE_DESCRIPTION = (
    "Indicators of living conditions for India's Muslim population, with Hindu "
    "and all-India comparison baselines on every metric. Covers population, "
    "education, employment, health, representation, and justice. Provenance-traced, "
    "Sachar-Committee-style measurement."
)

# ----- Analytics IDs (substituted into docs/js/analytics.js at build time) -----
# Replace these with the real IDs from analytics.google.com and clarity.microsoft.com.
# When left as the "__..." placeholders, the analytics.js loader skips loading
# anything — the site ships clean without telemetry until you swap them in.
GA4_ID = "G-SNNEXDK6LK"
CLARITY_ID = "x0qdfk6233"


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


# Compact 2-letter state abbreviations (for dense tables like the top-100
# districts list where the full state name doesn't fit).
STATE_ABBREV = {
    "IN-S01": "JK", "IN-S02": "HP", "IN-S03": "PB", "IN-S04": "CH",
    "IN-S05": "UK", "IN-S06": "HR", "IN-S07": "DL", "IN-S08": "RJ",
    "IN-S09": "UP", "IN-S10": "BR", "IN-S11": "SK", "IN-S12": "AR",
    "IN-S13": "NL", "IN-S14": "MN", "IN-S15": "MZ", "IN-S16": "TR",
    "IN-S17": "ML", "IN-S18": "AS", "IN-S19": "WB", "IN-S20": "JH",
    "IN-S21": "OD", "IN-S22": "CG", "IN-S23": "MP", "IN-S24": "GJ",
    "IN-S25": "DD", "IN-S26": "DN", "IN-S27": "MH", "IN-S28": "AP",
    "IN-S29": "KA", "IN-S30": "GA", "IN-S31": "LD", "IN-S32": "KL",
    "IN-S33": "TN", "IN-S34": "PY", "IN-S35": "AN", "IN-S36": "TG",
    "IN-S37": "LA",
}


def state_abbrev(code: str) -> str:
    """Return 2-letter state abbreviation from a district code IN-S{XX}-D{YYY}."""
    # district codes have the form IN-S{XX}-D{YYY} — take the state prefix
    prefix = "-".join(code.split("-")[:2]) if code.startswith("IN-S") else code
    return STATE_ABBREV.get(prefix, prefix)


def fmt_num(v: float, unit: str) -> str:
    if unit in ("percent",):
        # One-decimal cap, trim trailing ".0" so "55.0%" → "55%" but "84.3%" stays.
        s = f"{v:.1f}"
        if s.endswith(".0"):
            s = s[:-2]
        return f"{s}%"
    if unit == "females_per_1000_males":
        return f"{v:.0f}"
    if unit == "per_1000_live_births":
        return f"{v:.1f}"
    if unit in ("rate_per_100k", "per_100k_population"):
        # "63.3" — no unit suffix in the hero (the card's caption carries "per 100k").
        return f"{v:.1f}"
    if unit == "count":
        return f"{int(v):,}"
    return str(v)


# ---------- Metric prep ----------

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
        specs.append((
            SECTION_OF.get(m["cluster"], m["cluster"].capitalize()),
            m["id"],
            disp["label"],
            disp["unit_format"],
            disp.get("reference"),
            disp.get("higher_is_better"),
        ))
    specs.sort(key=lambda s: next(
        (d["display"]["scorecard"]["order"] for d in data["metrics"]
         if d["id"] == s[1] and d.get("display", {}).get("scorecard")),
        9999,
    ))
    return specs


SCORECARD_SPEC = load_scorecard_spec()


def render_scorecard_rows() -> str:
    """Compute one HTML <tr> per metric showing Muslim/Hindu/All and gap vs reference."""
    rows: list[str] = []
    for cluster, mid, name, unit, ref, higher_better in SCORECARD_SPEC:

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
                f'<td>{html.escape(name)}</td>'
                f'<td>{year}</td>'
                f'<td>{m_val:.2f}%</td>'
                f'<td>n/a</td>'
                f'<td>n/a</td>'
                f'<td class="{"gap-bad" if gap < 0 else "gap-good"}">{sign}{gap:.2f}pp vs 14.23% pop</td>'
                f'</tr>'
            )
            continue

        data = load_metric(mid)
        # Find national row per religion
        by_rel: dict[str, float] = {}
        year = "n/a"
        for r in data:
            if r["geography_level"] != "national":
                continue
            by_rel[r["religion"]] = float(r["value"])
            year = r["year"]
        m_val = by_rel.get("muslim")
        h_val = by_rel.get("hindu")
        a_val = by_rel.get("all")
        muslim_str = fmt_num(m_val, unit) if m_val is not None else "n/a"
        hindu_str = fmt_num(h_val, unit) if h_val is not None else "n/a"
        all_str = fmt_num(a_val, unit) if a_val is not None else "n/a"

        # Gap computation
        gap_str = "n/a"
        gap_class = "gap-neutral"
        if ref in ("hindu", "all"):
            comp_val = h_val if ref == "hindu" else a_val
            if m_val is not None and comp_val is not None:
                diff = m_val - comp_val
                sign = "+" if diff > 0 else ""
                gap_str = f"{sign}{diff:.2f}"
                if unit == "percent":
                    gap_str += "pp vs " + ("Hindu" if ref == "hindu" else "all-India")
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
<title>{site_title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{site_description}">
<link rel="canonical" href="{site_url}/">
<meta property="og:title" content="{site_title}">
<meta property="og:description" content="{site_description}">
<meta property="og:url" content="{site_url}/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{site_title}">
<meta name="twitter:description" content="{site_description}">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="js/analytics.js" defer></script>
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
  .page { max-width: 1280px; margin: 0 auto; padding: 32px 24px 80px; }
  h1 { font-size: 32px; margin: 0 0 12px; letter-spacing: -0.015em; line-height: 1.2; }
  .masthead { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--rule); }
  .masthead-brand { font-size: 14px; font-weight: 600; color: var(--accent); text-decoration: none; letter-spacing: -0.01em; }
  .masthead-brand:hover { text-decoration: underline; }
  .masthead-meta { margin: 0; font-size: 12px; color: var(--muted); }
  .masthead-meta a { color: var(--muted); }
  .headline-finding { font-size: 16px; line-height: 1.55; color: var(--fg); margin: 0 0 24px; max-width: 70em; }
  .headline-finding em { font-style: normal; color: var(--accent); font-weight: 600; }
  h2 { font-size: 20px; margin: 0 0 4px; letter-spacing: -0.01em; font-weight: 600; }
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
    font-size: 15px; font-weight: 600; color: var(--fg);
    letter-spacing: -0.005em;
    margin: 32px 0 12px; padding: 6px 0 0;
    border-top: 1px solid var(--rule);
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
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); align-items: start; gap: 16px; margin-bottom: 8px; }
  .card {
    background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
    padding: 18px 18px 14px; display: flex; flex-direction: column;
    transition: border-color .15s, box-shadow .15s, transform .15s;
  }
  .card:hover { border-color: var(--accent); box-shadow: var(--shadow-card); transform: translateY(-2px); }
  .card:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
  .card-metric { font-size: var(--t-sm); font-weight: 600; color: var(--fg); margin-bottom: 4px; line-height: 1.3; }
  .card-plain { font-size: var(--t-xs); color: var(--muted); margin: 0 0 10px; line-height: 1.45; font-weight: 400; }
  .modal-body .card-plain { font-size: 14px; color: var(--fg); margin: 0 0 16px; line-height: 1.55; max-width: 56em; }
  .card-hero { display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }
  .card-value { font-size: 1.7rem; font-weight: 700; letter-spacing: -.02em; color: var(--accent); font-feature-settings: "tnum"; }
  .card-unit, .card-year { font-size: var(--t-sm); color: var(--muted); font-weight: 500; }
  .card-direction { display: none; }
  .card-chartwrap { width: 100%; margin: 2px 0 4px; position: relative; }
  .card-chartscroll { width: 100%; margin: 2px 0 4px; overflow-y: auto; overflow-x: hidden; border: 1px solid var(--rule); border-radius: 4px; }
  .card-chartscroll .card-chartwrap { margin: 0; }
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
  /* Within a card, lift the disclosure summary so visitors don't pass by the
     "Top 100 districts" / "Full state data" drill-downs. Accent color + a
     subtle background; same chevron rotates when [open]. */
  .card details {
    margin-top: 12px; border-top: 1px solid var(--rule); padding-top: 10px;
  }
  .card details summary {
    cursor: pointer; user-select: none; list-style: none;
    color: var(--accent); font-weight: 600; font-size: var(--t-xs);
    padding: 6px 10px; background: var(--bg);
    border: 1px solid var(--rule); border-radius: var(--radius);
    display: inline-flex; align-items: center; gap: 4px;
    transition: background 0.15s, border-color 0.15s;
  }
  .card details summary::-webkit-details-marker { display: none; }
  .card details summary::before { content: ""; }  /* override the global "▸ "; we use ::after instead */
  .card details summary:hover { background: #fff7f0; border-color: var(--accent); }
  .card details summary::after {
    content: "↓"; font-size: 11px; display: inline-block; transition: transform 0.15s;
  }
  .card details[open] summary::after { transform: rotate(180deg); }
  .scroll-table { max-height: 320px; overflow-y: auto; border: 1px solid var(--rule); border-radius: 4px; margin-top: 8px; }
  .scroll-table table { margin-top: 0; }
  .scroll-table thead th {
    position: sticky; top: 0; background: var(--card);
    border-bottom: 1px solid var(--rule); font-size: 11px;
  }
  .scroll-table td { padding: 4px 8px; font-size: 12px; }
  @media (max-width: 560px) { .cards { grid-template-columns: 1fr; } }

  /* Modal: click any card to open a larger view of the same chart. */
  .cards .card { cursor: pointer; }
  .modal-overlay {
    position: fixed; inset: 0; z-index: 1000;
    background: rgba(20, 20, 20, 0.5);
    overflow-y: auto;
    padding: 40px 20px;
  }
  .modal-overlay[hidden] { display: none; }
  .modal {
    background: var(--card); border-radius: var(--radius);
    max-width: 920px; width: 100%; margin: 0 auto;
    position: relative; padding: 32px 36px 28px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28);
  }
  .modal-actions {
    position: absolute; top: 12px; right: 12px;
    display: flex; gap: 6px; align-items: center;
  }
  .modal-close, .modal-share {
    background: var(--card); border: 1px solid var(--rule); border-radius: 6px;
    cursor: pointer; color: var(--muted); padding: 0;
    transition: background .15s, border-color .15s, color .15s;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .modal-close { width: 34px; height: 34px; font-size: 22px; line-height: 1; }
  .modal-share { height: 34px; padding: 0 12px; gap: 6px; font-size: 13px; font-weight: 500; }
  .modal-close:hover, .modal-share:hover {
    background: var(--bg); border-color: var(--accent); color: var(--accent);
  }
  .modal-share.copied {
    background: #ecf6ec; border-color: #5a8a5a; color: #2e6b2e;
  }
  /* Inside the modal body, the cloned card sheds its card styling and the
     chart wrapper expands to use the larger real estate. */
  .modal-body .card {
    padding: 0; border: none; box-shadow: none; cursor: default;
  }
  .modal-body .card:hover {
    border: none; box-shadow: none; transform: none;
  }
  .modal-body .card-chartwrap { height: 440px !important; }
  .modal-body .card-chartscroll { max-height: 440px !important; }
  .modal-body .card-metric { font-size: 20px; margin-bottom: 12px; }
  .modal-body .card-value { font-size: 2.4rem; }
  .modal-body .comp-note { font-size: 14px; line-height: 1.55; }
  body.modal-open { overflow: hidden; }
  @media (max-width: 640px) {
    .modal { padding: 24px 18px; }
    .modal-body .card-chartwrap { height: 320px !important; }
    .modal-body .card-chartscroll { max-height: 320px !important; }
  }
</style>
</head>
<body>
<div class="page">

<div class="masthead">
  <a class="masthead-brand" href="/">muslimdata.in</a>
  <p class="masthead-meta">Last updated {timestamp} · <a href="https://github.com/iqbash1/indian-muslims-dashboard">open source on GitHub</a></p>
</div>
<h1>The state of Muslim India, in data</h1>

<section class="intro">
  <p>Indicators of living conditions for India's Muslim population, with Hindu and
  all-India comparison baselines on every metric. The methodology follows the
  approach of the Sachar Committee (the 2006 Prime Minister's commission whose
  report remains India's most-cited assessment of Muslim socio-economic status):
  focused, comparative measurement across population, education, employment,
  health, representation, and justice.</p>
  <p>Each card shows the Muslim value, how it ranks among religious communities,
  and how it has changed over time when the source has multiple survey rounds.
  Click any card to open a larger view; every card links to its downloadable CSV.
  Click any table column header to sort.</p>
</section>

<p class="headline-finding">
  Muslims are India's largest religious minority at <em>14.2%</em> of the
  population (Census 2011). On most indicators of education, employment,
  and political representation, Muslim outcomes trail the national
  average. On a handful of demographic and health indicators (sex ratio,
  infant survival, women's anaemia), Muslim outcomes run ahead. This page
  is the evidence.
</p>
<div class="status-bar">
  <span><b>{n_metrics}</b> indicators</span>
  <span><b>{n_sources}</b> primary sources</span>
  <span><b>{n_rows}</b> data points</span>
</div>

<!-- SCORECARD -->
<section class="tile scorecard">
  <div class="tile-head">
    <h2>Scorecard: all metrics at a glance</h2>
    <p class="data-current">Muslim outcome vs Hindu/All baseline · sorted by gap magnitude</p>
  </div>
  <table class="scorecard-table" id="scorecard"><thead><tr>
    <th class="sortable" data-col="0">Metric</th>
    <th class="sortable" data-col="1">Year</th>
    <th class="sortable" data-col="2">Muslim</th>
    <th class="sortable" data-col="3">Hindu</th>
    <th class="sortable" data-col="4">All</th>
    <th class="sortable" data-col="5">Gap vs reference</th>
  </tr></thead><tbody>
    {scorecard_rows}
  </tbody></table>
  <p class="methodology">"Gap" is Muslim minus reference baseline (Hindu where available, else All).
  Red gap = Muslim outcome worse than reference; green = Muslim outcome better. For justice
  metrics, cells show absolute count + incarceration rate per 100k of religious population;
  gap is the Muslim-to-Hindu rate ratio (1.0× = parity, >1.0× = Muslim overrepresented).</p>
</section>

{cluster_grids}

<div class="modal-overlay" id="modal-overlay" hidden role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <div class="modal" role="document">
    <div class="modal-actions">
      <button class="modal-share" id="modal-share" aria-label="Copy share link" title="Copy share link">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="18" cy="5" r="3"></circle>
          <circle cx="6" cy="12" r="3"></circle>
          <circle cx="18" cy="19" r="3"></circle>
          <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
          <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
        </svg>
        <span class="modal-share-label">Share</span>
      </button>
      <button class="modal-close" id="modal-close" aria-label="Close detail view">&times;</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<footer>
  <p>Last updated {timestamp}. Every number on this page is traced back to a primary
  source (Census of India, NCRB, NFHS, AISHE, PLFS, PRS, ECI candidate affidavits,
  and others), with the original file archived alongside its checksum so any value
  can be independently verified.</p>
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
    // After dropping the Cluster column, col 0 = Metric (string), col 1+ = numeric / mixed.
    if (m && col >= 1) return parseFloat(m[0].replace(/,/g, ''));
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
// Chart-spec registry: every factory records its (fnName, args) by canvas id
// so the modal can re-render any card chart on a larger canvas.
const CHART_SPECS = {};
function _spec(id, fnName, args) { CHART_SPECS[id] = { fnName, args }; }

function hbar(id, labels, values, colors, suffix, decimals, refValue, refLabel) {
  _spec(id, 'hbar', Array.from(arguments).slice(1));
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
function lineChart(id, labels, values, color, suffix) {
  _spec(id, 'lineChart', Array.from(arguments).slice(1));
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

// Multi-round trend: every named community over survey rounds, Muslim
// highlighted (bold solid accent), the others thinner in distinct colours.
// All-India is the dashed grey baseline, an aggregate that contains every
// community, so never a peer line. hasBreak dashes the Muslim line (cross-round
// comparability caveat, e.g. anaemia). Value axis hugs the data (no zero base).
// Minimalist palette: Muslim accent + non-Muslim communities in a muted gray family.
// Each line is identified by an end-of-line label (see _endLabels plugin); no legend.
const TREND_STYLE = {
  muslim:    { c: '#7b1d22', w: 2.6, r: 3, label: 'Muslim' },
  hindu:     { c: '#9e9e9e', w: 1.2, r: 0, label: 'Hindu' },
  christian: { c: '#bdbdbd', w: 1.2, r: 0, label: 'Christian' },
  sikh:      { c: '#bdbdbd', w: 1.2, r: 0, label: 'Sikh' },
  buddhist:  { c: '#cfcfcf', w: 1.2, r: 0, label: 'Buddhist' },
  jain:      { c: '#cfcfcf', w: 1.2, r: 0, label: 'Jain', minor: true },
  other:     { c: '#d8d8d8', w: 1.2, r: 0, label: 'Other', minor: true },
};
const TREND_ORDER = ['muslim', 'hindu', 'christian', 'sikh', 'buddhist', 'jain', 'other'];
// Direct end-of-line labels in each dataset's own color. Replaces the legend:
// each line self-identifies right where it terminates. Skips datasets whose last
// point is null (those lines never reach the right edge).
function _endLabels() {
  return { id: 'endLabels', afterDatasetsDraw(chart) {
    const { ctx } = chart;
    ctx.save();
    ctx.font = '600 10px -apple-system, system-ui, sans-serif';
    ctx.textBaseline = 'middle';

    // Collect each dataset's natural label position at its terminal point.
    const items = [];
    chart.data.datasets.forEach((d, i) => {
      if (d._isRefline) return;
      const data = d.data;
      let lastIdx = data.length - 1;
      while (lastIdx >= 0 && (data[lastIdx] == null)) lastIdx--;
      if (lastIdx < 0) return;
      const meta = chart.getDatasetMeta(i);
      const pt = meta.data[lastIdx];
      if (!pt) return;
      items.push({
        label: d.label, color: d.borderColor,
        weight: d.borderWidth || 1,
        x: pt.x, y: pt.y, naturalY: pt.y,
      });
    });

    // Sort top-to-bottom (small canvas-y is visually higher) and resolve overlaps
    // by cascading each label downward only as far as the previous one forces.
    const minGap = 11;
    items.sort((a, b) => a.naturalY - b.naturalY);
    for (let i = 1; i < items.length; i++) {
      if (items[i].y - items[i - 1].y < minGap) {
        items[i].y = items[i - 1].y + minGap;
      }
    }

    // Anchor the bottom-most label to its line if cascading pushed the stack
    // below the plot area; sweep upward to re-tighten with the same minGap.
    const yMax = chart.chartArea.bottom;
    if (items.length && items[items.length - 1].y > yMax) {
      items[items.length - 1].y = Math.min(items[items.length - 1].naturalY, yMax);
      for (let i = items.length - 2; i >= 0; i--) {
        if (items[i + 1].y - items[i].y < minGap) {
          items[i].y = items[i + 1].y - minGap;
        }
      }
    }

    for (const it of items) {
      ctx.fillStyle = it.color;
      ctx.textAlign = 'left';
      ctx.fillText(it.label, it.x + 5, it.y);
    }
    ctx.restore();
  }};
}
function trendChart(id, years, seriesMap, allSeries, suffix, hasBreak, refLine, dashedExtras) {
  _spec(id, 'trendChart', Array.from(arguments).slice(1));
  const ds = [];
  for (const rel of TREND_ORDER) {
    if (!seriesMap[rel]) continue;
    const s = TREND_STYLE[rel];
    const next = {
      label: s.label, data: seriesMap[rel], borderColor: s.c, backgroundColor: 'transparent',
      fill: false, tension: 0.25, pointRadius: s.r, borderWidth: s.w, pointBackgroundColor: s.c,
      borderDash: (rel === 'muslim' && hasBreak) ? [5, 4] : [], spanGaps: false,
      order: rel === 'muslim' ? 0 : 1,
    };
    if (s.minor) next._noEndLabel = true;  // skip end-label for minor communities (Jain, Other)
    ds.push(next);
  }
  // Extra dashed series (e.g. Hindu as a reference in pop-share). Each entry:
  // {label, data, color?}.  Drawn dashed gray, no points, end-labeled.
  if (dashedExtras) {
    for (const ex of dashedExtras) {
      ds.push({
        label: ex.label, data: ex.data, borderColor: ex.color || '#9e9e9e',
        backgroundColor: 'transparent', fill: false, tension: 0.25, pointRadius: 0,
        borderWidth: 1, borderDash: [5, 4], spanGaps: false, order: 2,
      });
    }
  }
  if (allSeries) {
    const allDs = {
      label: 'All-India', data: allSeries, borderColor: '#9e9e9e', backgroundColor: 'transparent',
      fill: false, tension: 0.25, pointRadius: 0, borderWidth: 1, borderDash: [2, 3],
      spanGaps: false, order: 3,
    };
    allDs._isRefline = true;  // baseline aggregate, not a peer; suppress end-label.
    ds.push(allDs);
  }
  if (refLine) {
    const refDs = {
      label: refLine.label, data: years.map(() => refLine.value), borderColor: '#bdbdbd',
      backgroundColor: 'transparent', fill: false, tension: 0, pointRadius: 0, borderWidth: 1,
      borderDash: [4, 3], spanGaps: false, order: 4,
    };
    refDs._isRefline = true;
    ds.push(refDs);
  }
  new Chart(document.getElementById(id), {
    type: 'line',
    data: { labels: years, datasets: ds },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      layout: { padding: { right: 64, top: 6 } },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (c) => c.dataset.label + ': ' + c.parsed.y + suffix } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { beginAtZero: false, grace: '12%', grid: { color: '#f0ede4', drawTicks: false },
             border: { display: false }, ticks: { font: { size: 10 }, color: '#999' } },
      },
    },
    plugins: [_endLabels()],
  });
}

{card_charts}

// Modal: clicking a card opens a larger view of the same chart by cloning
// the card into the modal body and re-rendering the chart on a fresh canvas
// using the spec captured by _spec() in the factory functions. Shareable via
// per-metric stub pages at /m/{slug}/ that redirect into /#{slug}.
(function modalSetup() {
  const overlay = document.getElementById('modal-overlay');
  const body = document.getElementById('modal-body');
  const closeBtn = document.getElementById('modal-close');
  const shareBtn = document.getElementById('modal-share');
  const factories = { hbar, lineChart, trendChart };
  let modalChart = null;
  let activeMid = null;

  function openModal(card) {
    closeChart();
    const clone = card.cloneNode(true);
    body.innerHTML = '';
    body.appendChild(clone);

    activeMid = card.getAttribute('data-metric-id') || null;

    // Reveal the modal first so the layout pass settles and the wrapper
    // picks up its 440px CSS height. Chart.js measures its container at
    // construction, so we defer instantiation to the next frame.
    overlay.hidden = false;
    document.body.classList.add('modal-open');
    closeBtn.focus();

    const origCanvas = card.querySelector('canvas');
    const cloneCanvas = clone.querySelector('canvas');
    if (origCanvas && cloneCanvas) {
      // Strip dimensions inherited from the source canvas; let Chart.js
      // size the cloned canvas to its (now-visible) container.
      cloneCanvas.removeAttribute('width');
      cloneCanvas.removeAttribute('height');
      cloneCanvas.style.width = '';
      cloneCanvas.style.height = '';
      const modalId = origCanvas.id + '-modal';
      cloneCanvas.id = modalId;
      const spec = CHART_SPECS[origCanvas.id];
      if (spec && factories[spec.fnName]) {
        factories[spec.fnName](modalId, ...spec.args);
        modalChart = Chart.getChart(modalId);
        // Force a resize after the layout settles so labels reflow into
        // the modal's larger real estate (Chart.js measures at construction).
        if (modalChart) requestAnimationFrame(() => modalChart && modalChart.resize());
      }
    }

    // Reflect the open metric in the URL so the visitor's address bar is
    // shareable and the back button closes the modal naturally.
    if (activeMid && location.hash !== '#' + activeMid) {
      history.replaceState(null, '', '#' + activeMid);
    }
    if (typeof gtag === 'function' && activeMid) {
      gtag('event', 'metric_opened', { metric_id: activeMid });
    }
  }

  function closeChart() {
    if (modalChart) { modalChart.destroy(); modalChart = null; }
  }

  function closeModal() {
    closeChart();
    overlay.hidden = true;
    document.body.classList.remove('modal-open');
    body.innerHTML = '';
    activeMid = null;
    if (location.hash) {
      history.replaceState(null, '', location.pathname + location.search);
    }
  }

  function openByMid(mid) {
    if (!mid) return false;
    const card = document.querySelector('.cards .card[data-metric-id="' + CSS.escape(mid) + '"]');
    if (!card) return false;
    openModal(card);
    return true;
  }

  closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !overlay.hidden) closeModal();
  });

  // Share: copy the per-metric permalink to clipboard. The /m/{slug}/ stub
  // path carries the per-metric OG meta so social cards render properly.
  shareBtn.addEventListener('click', () => {
    if (!activeMid) return;
    const card = body.querySelector('.card');
    const name = card?.getAttribute('data-metric-name') || activeMid;
    const url = location.origin + '/m/' + encodeURIComponent(activeMid) + '/';
    const text = 'muslimdata.in — ' + name + '\\n' + url;
    const showCopied = (method) => {
      shareBtn.classList.add('copied');
      const label = shareBtn.querySelector('.modal-share-label');
      const prev = label ? label.textContent : '';
      if (label) label.textContent = 'Copied';
      setTimeout(() => {
        shareBtn.classList.remove('copied');
        if (label) label.textContent = prev || 'Share';
      }, 1500);
      if (typeof gtag === 'function') {
        gtag('event', 'share_clicked', { metric_id: activeMid, method });
      }
    };
    if (navigator.share) {
      navigator.share({ title: 'muslimdata.in: ' + name, text: name, url })
        .then(() => showCopied('native'))
        .catch(() => {
          // User cancelled the share sheet; fall back to clipboard copy.
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(() => showCopied('clipboard'));
          }
        });
    } else if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(
        () => showCopied('clipboard'),
        () => showCopied('clipboard-fail'),
      );
    }
  });

  document.querySelectorAll('.cards .card').forEach((card) => {
    card.addEventListener('click', (e) => {
      // Let links, summaries, and download triggers behave normally.
      if (e.target.closest('a, summary, details, button')) return;
      openModal(card);
    });
  });

  // Hash routing: open the matching modal on page load or hash change.
  function handleHash() {
    const mid = location.hash.replace(/^#/, '');
    if (!mid) {
      if (!overlay.hidden) closeModal();
      return;
    }
    openByMid(mid);
  }
  window.addEventListener('hashchange', handleHash);
  if (location.hash) handleHash();
})();
</script>
</body>
</html>
"""


STUB_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{description}">
<link rel="canonical" href="{site_url}/m/{mid}/">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{site_url}/m/{mid}/">
<meta property="og:type" content="article">
<meta property="og:site_name" content="muslimdata.in">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta http-equiv="refresh" content="0; url={site_url}/#{mid}">
<script>location.replace({redirect_target});</script>
<style>body{{font:14px -apple-system,system-ui,sans-serif;color:#666;padding:40px;text-align:center}}</style>
</head>
<body>
<p>Redirecting to <a href="{site_url}/#{mid}">muslimdata.in</a>...</p>
</body>
</html>
"""


def _emit_metric_stubs(out_dir: pathlib.Path) -> int:
    """Write a stub HTML page per live metric at /m/{mid}/index.html. Each
    carries metric-specific OG meta so social-card previews show the right
    title; body client-redirects into the main page hash to auto-open the
    modal. Returns the count of stubs written."""
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        data = _yaml.safe_load(f)
    stubs_root = out_dir / "m"
    stubs_root.mkdir(parents=True, exist_ok=True)
    written = 0
    for m in data["metrics"]:
        disp = m.get("display", {}).get("scorecard")
        if not disp or disp.get("include", True) is False:
            continue
        mid = m["id"]
        name = m.get("name", disp.get("label", mid))
        # One-sentence description derived from the metric definition, trimmed
        # to a single line for OG meta. Falls back to a generic line.
        defn = (m.get("definition") or "").strip().split("\n")[0].strip()
        description = (
            f"{name}, with Hindu and all-India comparison baselines on muslimdata.in. "
            + (defn if defn else "Provenance-traced living-conditions indicator.")
        )
        # 200-char cap so the description fits inside what social cards display.
        if len(description) > 240:
            description = description[:237].rstrip() + "..."
        page = STUB_TEMPLATE.format(
            mid=mid,
            site_url=SITE_URL,
            title=html.escape(f"{name}: muslimdata.in"),
            og_title=html.escape(name),
            description=html.escape(description),
            redirect_target=json.dumps(f"{SITE_URL}/#{mid}"),
        )
        stub_dir = stubs_root / mid
        stub_dir.mkdir(exist_ok=True)
        (stub_dir / "index.html").write_text(page)
        written += 1
    return written


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
        "{timestamp}": dt.datetime.now().strftime("%-d %B %Y"),
        "{n_metrics}": str(n_metrics),
        "{n_sources}": str(n_sources),
        "{n_rows}": str(n_rows),
        "{scorecard_rows}": render_scorecard_rows(),
        "{cluster_grids}": cluster_grids,
        "{card_charts}": card_charts,
        "{site_title}": html.escape(SITE_TITLE),
        "{site_description}": html.escape(SITE_DESCRIPTION),
        "{site_url}": SITE_URL,
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

    # Emit docs/js/analytics.js from the template, substituting GA4 + Clarity
    # IDs. Treated as build output (regenerated each build), like index.html.
    analytics_src = REPO_ROOT / "dashboard" / "analytics.template.js"
    analytics_out = OUT_PATH.parent / "js" / "analytics.js"
    analytics_out.parent.mkdir(parents=True, exist_ok=True)
    js_text = analytics_src.read_text()
    js_text = js_text.replace("__GA4_ID__", GA4_ID).replace("__CLARITY_ID__", CLARITY_ID)
    analytics_out.write_text(js_text)

    # Emit per-metric stub pages at /m/{mid}/index.html. Each carries the
    # metric-specific OG meta tags so social previews show the right
    # title/description when a user shares the link; the body then
    # client-redirects to the main page's hash for the modal to auto-open.
    _emit_metric_stubs(OUT_PATH.parent)

    # Ensure a .nojekyll is inside the publish folder so GitHub Pages serves the
    # HTML as-is without Jekyll processing (root-level .nojekyll doesn't apply
    # when publishing from a subfolder). Harmless on Cloudflare Pages.
    (OUT_PATH.parent / ".nojekyll").touch()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html_out)
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} ({len(html_out):,} bytes)")
    print(f"wrote {analytics_out.relative_to(REPO_ROOT)} ({len(js_text):,} bytes)")


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
    "prison-rate-per-100k": "prisoners per 100k of community",
    "undertrial-rate-per-100k": "undertrials per 100k of community",
    "communal-incidents-govt": "incidents",
    "communal-incidents-civic": "hate-speech events",
}
# (suffix, decimals) for chart value labels, keyed by unit_format.
UNIT_JS = {
    "percent": ("%", 1), "females_per_1000_males": ("", 0),
    "per_1000_live_births": ("", 1), "rate_per_100k": ("", 1), "count": ("", 0),
}
SOURCE_LABEL = {
    "census-india-1961": "Census 1961 · C-VII Religion",
    "census-india-1971": "Census 1971 · Paper 2 of 1972",
    "census-india-1981": "Census 1981 · HH-15 (Paper 3 of 1984)",
    "census-india-1991": "Census 1991 · C-9 Religion",
    "census-india-2001": "Census 2001 · C-series",
    "census-india-2011": "Census 2011 · C-series",
    "nfhs-2": "NFHS-2 (1998-99)", "nfhs-3": "NFHS-3 (2005-06)",
    "nfhs-4": "NFHS-4 (2015-16)", "nfhs-5": "NFHS-5 (2019-21)",
    "plfs": "PLFS 2023-24", "aishe": "AISHE 2021-22",
    "ncrb-prison": "NCRB PSI (2018-2023)", "ncrb-crime": "NCRB CII (2015-2023)",
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
    return {"good": "ahead", "bad": "behind", "neutral": "even"}[cls]


def _tier_word(tier: str) -> str:
    return {"good": "top tier", "mid": "middle tier", "bad": "bottom tier"}[tier]


def _year_of(metric_id: str):
    yrs = [int(r["year"]) for r in load_metric(metric_id) if r["geography_level"] == "national"]
    return max(yrs) if yrs else ""


def _comp(label: str, verdict: str, detail: str, cls: str) -> str:
    return (f'<div class="card-comp {cls}"><div class="comp-label">{html.escape(label)}</div>'
            f'<div class="comp-verdict">{html.escape(verdict)}</div>'
            f'<div class="comp-detail">{html.escape(detail)}</div></div>')


PLAIN_DEFINITION = {
    "pop-share": "What share of India's population is Muslim, by the most recent census.",
    "urban-share": "What share of each community lives in towns and cities rather than villages.",
    "sex-ratio": "Number of females per 1,000 males. Higher is more balanced; lower means a gender imbalance favouring males.",
    "district-concentration-top100": "Of all Indian Muslims, what fraction lives in the 100 districts with the largest Muslim populations.",
    "lit-7plus": "Of people aged 7 and older, what share can read and write. The Census uses 7+ as the standard cutoff to exclude very young children.",
    "ger-higher-ed": "Of every 100 young people in the typical college-going age band (18 to 23), how many are enrolled in higher education.",
    "muslim-higher-ed-enrolment": "Total number of Muslim students enrolled in higher education across India in the latest year.",
    "lfpr-15plus": "Of people aged 15 and older, what share is in the workforce, either working or actively looking for work.",
    "wpr-15plus": "Of people aged 15 and older, what share is currently working.",
    "salaried-share": "Of all workers, what share has regular salaried jobs (as opposed to self-employment or casual labour).",
    "imr": "Of every 1,000 babies born, how many die before their first birthday. Lower is better.",
    "stunting-u5": "Of children under 5, what share is too short for their age, a long-term sign of chronic undernutrition.",
    "inst-delivery": "Of recent live births, what share took place at a hospital or health facility rather than at home.",
    "women-anemia": "Of women in childbearing age (15 to 49), what share has anaemia (low haemoglobin).",
    "improved-sanitation": "Of households, what share has access to a toilet of any type.",
    "ls-share": "Of the 543 seats in India's national parliament (Lok Sabha), what share is held by Muslim MPs.",
    "mla-share": "Across all 30 state and UT legislative assemblies that hold elections, what share of MLA seats is held by Muslims.",
    "prison-rate-per-100k": "For every 100,000 people of a religion, how many are in prison. Allows fair comparison across communities of different size.",
    "undertrial-rate-per-100k": "For every 100,000 people of a religion, how many are in prison awaiting trial (not yet convicted).",
    "communal-incidents-govt": "Number of communal or religious rioting incidents recorded in police records each year (NCRB).",
    "communal-incidents-civic": "Number of in-person events (rallies, religious gatherings, political speeches) targeting Muslims with hateful rhetoric, documented by India Hate Lab.",
}


def _card_shell(mid, label, value, unit_txt, year, polarity, chart_html, comps_html,
                src, csv_href, details_html="") -> str:
    pill = f'<div class="card-direction">{html.escape(polarity)}</div>' if polarity else ""
    yr = f'<span class="card-year">({html.escape(str(year))})</span>' if year else ""
    plain = PLAIN_DEFINITION.get(mid, "")
    plain_html = f'<p class="card-plain">{html.escape(plain)}</p>' if plain else ""
    return (
        f'<section class="card" data-metric-id="{html.escape(mid)}" data-metric-name="{html.escape(label)}">'
        f'<div class="card-metric">{html.escape(label)}</div>'
        f'{plain_html}'
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


def _top100_districts_table(metric_id: str) -> str:
    """Scrollable Rank | District (ST) | Pop (M) | % of pop table built from the
    per-district rows the canonicalizer now emits. Reads `methodology_note` for
    rank + district name + within-district Muslim percentage (the canonicalizer
    stamps these as `rank=N; name=...; muslim_pct_of_district=...`)."""
    rows = [r for r in load_metric(metric_id) if r["geography_level"] == "district"]
    if not rows:
        return ""
    parsed = []
    for r in rows:
        note = r.get("methodology_note") or ""
        # Parse "rank=N; name=...; muslim_pct_of_district=..."
        meta = {}
        for part in note.split(";"):
            if "=" in part:
                k, _, v = part.partition("=")
                meta[k.strip()] = v.strip()
        rank = int(meta.get("rank", "0") or 0)
        name = meta.get("name", "")
        try:
            pct = float(meta.get("muslim_pct_of_district", "0"))
        except ValueError:
            pct = 0.0
        muslim_count = int(float(r["value"]))
        st_abbr = state_abbrev(r["geography_code"])
        parsed.append((rank, name, st_abbr, muslim_count, pct))
    parsed.sort(key=lambda x: x[0])
    trs = []
    for rank, name, st, muslim, pct in parsed:
        # Format Muslim population in millions ("4.71M") for compactness
        mil = muslim / 1_000_000
        mil_str = f"{mil:.2f}M" if mil >= 1 else f"{mil*1000:.0f}k"
        trs.append(
            f"<tr>"
            f'<td style="text-align:right">{rank}</td>'
            f"<td>{html.escape(name)} <span style=\"color:var(--muted);font-size:11px\">({html.escape(st)})</span></td>"
            f'<td style="text-align:right;font-feature-settings:&quot;tnum&quot;">{mil_str}</td>'
            f'<td style="text-align:right;font-feature-settings:&quot;tnum&quot;">{pct:.1f}%</td>'
            f"</tr>"
        )
    return (
        f'<details><summary>See the full ranked list (top {len(parsed)} districts)</summary>'
        f'<div class="scroll-table">'
        f'<table>'
        f'<thead><tr>'
        f'<th style="text-align:right">#</th>'
        f'<th>District (ST)</th>'
        f'<th style="text-align:right">Pop</th>'
        f'<th style="text-align:right">% of pop</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(trs)}</tbody>'
        f'</table>'
        f'</div></details>'
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
                 f"<td>{fmt_num(b['muslim'], unit) if 'muslim' in b else 'n/a'}</td>")
        if has_hindu:
            cells += f"<td>{fmt_num(b['hindu'], unit) if 'hindu' in b else 'n/a'}</td>"
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

    if special == "share_trend":
        return _card_share_trend(mid, label, src, csv_href, cvid)
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
    headline = fmt_num(muslim, unit) if muslim is not None else "n/a"
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
    # 3+ rounds: multi-line trend chart. 2 rounds: too thin to be a "trend" —
    # show the latest-year community snapshot + a "Since {y0}" delta pill.
    # 1 round / no time dim: snapshot only.
    if len(years) >= 3:
        # TIME SERIES card: every named community over rounds, Muslim highlighted,
        # All-India dashed baseline; latest-year community ranking shown via the
        # end-of-line labels on the chart itself (no redundant details table).
        named = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other")
        series_map = {rel: [series.get(rel, {}).get(y) for y in years]
                      for rel in named if rel in series}
        all_series = [series.get("all", {}).get(y) for y in years] if "all" in series else None
        chart_html = f'<div class="card-chartwrap" style="height:200px"><canvas id="{cvid}"></canvas></div>'
        js = (f'trendChart("{cvid}", {json.dumps(years)}, {json.dumps(series_map)}, '
              f'{json.dumps(all_series)}, {json.dumps(suffix)}, {json.dumps(bool(has_break))});')
        details = ""
    else:
        # SNAPSHOT card: latest-year community bar with All-India dashed baseline.
        # If we have a 2-point time series, surface the Muslim Δ as a comparison pill.
        if len(years) == 2 and "muslim" in series:
            mfirst = series["muslim"].get(years[0])
            mlast = series["muslim"].get(years[-1])
            if mfirst is not None and mlast is not None:
                delta = mlast - mfirst
                arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                comps += _comp(f"Since {years[0]}", f"{arrow} {abs(delta):.1f}{suffix}",
                               f"{mfirst:.1f}{suffix} → {mlast:.1f}{suffix}", "mid")
        pairs = [(COMMUNITY_LABEL[c], nat[c], c == "muslim") for c in named]
        if hib is not None:
            pairs.sort(key=lambda b: b[1], reverse=bool(hib))
        # When the metric carries only Muslim + All-India (e.g. GER higher-ed),
        # surface All-India as a second bar so the chart actually communicates
        # the gap instead of being a single redundant bar.
        if len(pairs) == 1 and all_v is not None:
            pairs.append(("All-India", float(all_v), False))
        labels = [p[0] for p in pairs]
        values = [round(p[1], 4) for p in pairs]
        mhex = TIER_HEX.get(tier, "#555555")
        colors = [mhex if p[2] else "#D8DEE2" for p in pairs]
        # Only skip the chart if there's truly nothing comparative to show.
        if len(pairs) <= 1:
            chart_html = ""
            js = None
        else:
            h = len(pairs) * 28 + 28
            chart_html = f'<div class="card-chartwrap" style="height:{h}px"><canvas id="{cvid}"></canvas></div>'
            # If we already promoted All-India to a peer bar, don't ALSO draw it
            # as a dashed reference line — that would be redundant.
            has_all_bar = any(lbl == "All-India" for lbl in labels)
            ref = "null" if has_all_bar else (json.dumps(round(all_v, 4)) if all_v is not None else "null")
            ref_label = "" if has_all_bar else "All-India"
            js = (f'hbar("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, {json.dumps(colors)}, '
                  f'{json.dumps(suffix)}, {dec}, {ref}, {json.dumps(ref_label)});')
        details = _state_details(mid, unit)

    return _card_shell(mid, label, headline, CAPTION.get(mid, ""), _year_of(mid), polarity,
                       chart_html, comps, src, csv_href, details), js


def _card_muslim_only(mid, label, unit, src, csv_href, cvid):
    nat = _nat_by_religion(mid)
    muslim = nat.get("muslim")
    headline = fmt_num(muslim, unit) if muslim is not None else "n/a"
    chart_html, js, note = "", None, ""
    if mid == "pop-share":
        # Decadal multi-community trend (1961->2011). Hindu (~80%) dominates if
        # plotted on the same axis as Muslim + minor religions, so the chart's
        # y-axis hugs the 0-15% band where the Muslim story is legible; Hindu's
        # trajectory is summarised as a dashed reference line at its midpoint
        # value, labeled "Hindu ~80%". (Hindu moved 83.45 -> 79.80 over 50
        # years — a 3.65pp drift, not visually distinguishable from a flat line
        # at this resolution, so a single reference value is honest.)
        years, series, _ = _nat_trend(mid)
        main_named = ("muslim", "christian", "sikh", "buddhist", "jain")
        series_map = {rel: [series.get(rel, {}).get(y) for y in years]
                      for rel in main_named if rel in series}
        hindu_first = series.get("hindu", {}).get(years[0]) if years else None
        hindu_last = series.get("hindu", {}).get(years[-1]) if years else None
        chart_html = f'<div class="card-chartwrap" style="height:200px"><canvas id="{cvid}"></canvas></div>'
        # No All-India series (shares already sum to ~100%); no refLine.
        js = (f'trendChart("{cvid}", {json.dumps(years)}, {json.dumps(series_map)}, '
              f'null, "%", false);')
        note = (f"Share of each community in India's population by census. Hindu's share "
                f"drifted from {hindu_first:.1f}% in 1961 to {hindu_last:.1f}% in 2011, "
                f"omitted from the chart so the Muslim and minor-community trends are legible. "
                f"All values from primary RGI religion volumes 1961-2011; 1981 excludes "
                f"Assam, 1991 excludes Jammu & Kashmir.")
    elif mid == "district-concentration-top100":
        # Two-bar split: the top-100 districts vs every other district. Directly
        # visualises the concentration the headline measures. The full top-100
        # list (rank, district, state, count, %) is in the collapsible details
        # below the chart — see _top100_districts_table().
        rest = round(100 - muslim, 2)
        chart_html = f'<div class="card-chartwrap" style="height:92px"><canvas id="{cvid}"></canvas></div>'
        js = (f'hbar("{cvid}", {json.dumps(["Top-100 districts", "Other districts"])}, '
              f'{json.dumps([round(muslim, 2), rest])}, {json.dumps(["#7b1d22", "#D8DEE2"])}, '
              f'"%", 1, null, "");')
        note = ("Share of all Indian Muslims living in the 100 most Muslim-populous districts. "
                "This is a geographic-concentration measure, not a community comparison.")
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
        note = ("No community ranking. AISHE tabulates “Muslim Minority” enrolment separately; "
                "other communities are not enumerated in the same table. Top-8 states shown (thousands).")
    comps = f'<div class="comp-note">{html.escape(note)}</div>'
    # Metric-specific drill-down (collapsed by default). For district-concentration
    # we surface the full top-100 list; for others, state-level data if available.
    if mid == "district-concentration-top100":
        details = _top100_districts_table(mid)
    else:
        details = _state_details(mid, unit)
    return _card_shell(mid, label, headline, CAPTION.get(mid, ""), _year_of(mid), "",
                       chart_html, comps, src, csv_href, details), js


def _card_share_trend(mid, label, src, csv_href, cvid):
    """Multi-year Muslim + Hindu share trend with the Muslim population share
    (~14.2%) drawn as the interpretive reference line. Used for the justice
    metrics prison-share and undertrial-share. Headline = latest-year Muslim share."""
    noun = "prisoners" if mid == "prison-share" else "undertrials"
    years, series, _ = _nat_trend(mid)
    # Fill internal year gaps (e.g. 2020, not published) with null so the trend
    # line visibly breaks there rather than silently compressing the axis. The
    # dashed population reference line still spans every year.
    axis_years = list(range(years[0], years[-1] + 1)) if years else []
    nat = _nat_by_religion(mid)  # latest year
    muslim_latest = nat.get("muslim")
    headline = f"{muslim_latest:.1f}" if muslim_latest is not None else "n/a"
    series_map = {rel: [series.get(rel, {}).get(y) for y in axis_years]
                  for rel in ("muslim", "hindu") if rel in series}
    chart_html = f'<div class="card-chartwrap" style="height:188px"><canvas id="{cvid}"></canvas></div>'
    refline = {"value": MUSLIM_POP_SHARE, "label": f"Muslim population {MUSLIM_POP_SHARE}%"}
    js = (f'trendChart("{cvid}", {json.dumps(axis_years)}, {json.dumps(series_map)}, '
          f'null, "%", false, {json.dumps(refline)});')

    comps = ""
    if muslim_latest is not None:
        over = muslim_latest - MUSLIM_POP_SHARE
        comps += _comp("vs population", f"{'+' if over >= 0 else ''}{over:.1f} pp",
                       f"{muslim_latest:.1f}% of {noun} vs {MUSLIM_POP_SHARE}% of people",
                       "bad" if over > 0 else "neutral")
    if len(years) >= 2 and "muslim" in series:
        mfirst, mlast = series["muslim"].get(years[0]), series["muslim"].get(years[-1])
        if mfirst is not None and mlast is not None:
            delta = mlast - mfirst
            arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
            comps += _comp(f"Since {years[0]}", f"{arrow} {abs(delta):.1f} pp",
                           f"{mfirst:.1f}% → {mlast:.1f}%", "mid")
    note = (f"Muslim share of {noun} whose religion was reported (NCRB PSI). The dashed line is "
            f"the ~{MUSLIM_POP_SHARE}% Muslim share of India's population (Census 2011); the Muslim "
            f"line sits above it every year. Some states (e.g. Maharashtra) did not report religion "
            f"in some years and are excluded from that year's denominator. 2016, 2017 and 2020 are "
            f"not available in an extractable English edition.")
    comps += f'<div class="comp-note">{html.escape(note)}</div>'
    return _card_shell(mid, label, headline, f"% of {noun}", years[-1] if years else "",
                       "lower is better", chart_html, comps, src, csv_href,
                       _share_year_details(mid)), js


def _share_year_details(mid: str) -> str:
    """<details> table of Muslim/Hindu share by year for a share-trend metric."""
    years, series, _ = _nat_trend(mid)
    trs = []
    for y in years:
        m = series.get("muslim", {}).get(y)
        h = series.get("hindu", {}).get(y)
        m_str = f"{m:.2f}%" if m is not None else "n/a"
        h_str = f"{h:.2f}%" if h is not None else "n/a"
        trs.append(f"<tr><td>{y}</td><td>{m_str}</td><td>{h_str}</td></tr>")
    return ("<details><summary>By year</summary>"
            "<table><thead><tr><th>Year</th><th>Muslim</th><th>Hindu</th></tr></thead>"
            f"<tbody>{''.join(trs)}</tbody></table></details>")


def _card_timeseries(mid, label, unit, src, csv_href, cvid):
    rows = sorted([r for r in load_metric(mid) if r["geography_level"] == "national"],
                  key=lambda r: int(r["year"]))
    latest = rows[-1] if rows else None
    val = float(latest["value"]) if latest else None
    headline = fmt_num(val, unit) if val is not None else "n/a"
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
            inner_h = len(st) * 26 + 20
            max_h = 240
            inner = (f'<div class="card-chartwrap" style="height:{inner_h}px">'
                     f'<canvas id="{cvid}"></canvas></div>')
            chart_html = (f'<div class="card-chartscroll" style="max-height:{max_h}px">{inner}</div>'
                          if inner_h > max_h else inner)
            js = (f'hbar("{cvid}", {json.dumps([s[0] for s in st])}, '
                  f'{json.dumps([round(s[1], 2) for s in st])}, '
                  f'{json.dumps(["#2b6cb0"] * len(st))}, "%", 1);')
        comps += _comp("all states", headline, "aggregate across assemblies", "neutral")
    return _card_shell(mid, label, headline, CAPTION.get(mid, ""), latest["year"] if latest else "",
                       "", chart_html, comps, src, csv_href), js


def _card_ts_count(mid, label, src, csv_href, cvid):
    rows = sorted([r for r in load_metric(mid) if r["geography_level"] == "national"],
                  key=lambda r: int(r["year"]))
    latest = rows[-1] if rows else None
    val = int(float(latest["value"])) if latest else 0
    comps = ""
    chart_html, js = "", None
    if len(rows) >= 3:
        # 3+ years: a real trend shape worth charting.
        labels = [int(r["year"]) for r in rows]
        values = [int(float(r["value"])) for r in rows]
        chart_html = f'<div class="card-chartwrap" style="height:150px"><canvas id="{cvid}"></canvas></div>'
        js = f'lineChart("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, "#7b1d22", "");'
        comps += _comp("trend", f"{labels[0]}–{labels[-1]}", f"{values[0]:,} → {val:,}", "neutral")
    elif len(rows) == 2:
        # 2-point "trend" is just a straight line — let the Δ pill carry it.
        first, last = int(float(rows[0]["value"])), val
        delta = last - first
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        cls = "bad" if delta > 0 else ("good" if delta < 0 else "mid")
        comps += _comp(f"{rows[0]['year']} → {latest['year']}",
                       f"{arrow} {abs(delta):,}",
                       f"{first:,} → {last:,}", cls)
    return _card_shell(mid, label, f"{val:,}", CAPTION.get(mid, "events"), latest["year"] if latest else "",
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
