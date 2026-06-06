"""
L4 dashboard build: reads canonical/*.csv + manifest/metrics.yaml, writes
docs/index.html (the published site at muslimdata.in), docs/js/analytics.js
(GA4 + Clarity loader, IDs substituted from constants below), docs/about/
index.html (the About page), and docs/m/{mid}/index.html (one OG stub page
per live metric).

Output is a fully pre-rendered static site: every chart's data is inlined
into the page script blocks at build time; the browser never fetches data.

Usage:
  python dashboard/build.py
  open docs/index.html

Re-runs idempotently. Cloudflare Workers (Static Assets) auto-deploys
on every push to main, so a `git push` ships the new build in ~1-2 min.
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import json
import pathlib

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # Pillow is in requirements.txt; this guard keeps non-OG builds working.
    Image = None
    ImageDraw = None
    ImageFont = None

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

# Total districts enumerated in Census 2011. Sourced from this project's own
# canonical provenance: the district-concentration-top100 row records "640
# districts considered" (computed across all state MDDS C-1 files). Used to
# frame how concentrated the top-100 figure is (100 of 640 ≈ 16% of districts).
TOTAL_DISTRICTS_2011 = 640

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

# One-line intro shown under each section header, telling a new visitor what
# story to expect in the cards below. Written by hand against current data;
# update when the data changes the direction. Indian-English spelling.
SECTION_INTROS = {
    "Demographics": "India's largest religious minority at 14.2% of the population (Census 2011), more urban than the national average, concentrated in a handful of districts in the north and east.",
    "Education & Employment": "Muslims trail on literacy, higher-education enrolment, and salaried work. Labour-force and worker-population ratios run near the national average.",
    "Health & Housing": "Muslim infant mortality is below the national average and women's anaemia is the lowest of any community, but under-5 stunting is the highest. Toilet-facility access is now close to par.",
    "Representation": "Muslim share of elected seats sits well below their share of the population, both in the Lok Sabha (4.4% of MPs vs 14.2% of population) and across state assemblies (6.0%).",
    "Justice & Civic": "Muslims are over-represented in the prison and undertrial populations on a per-100k-of-community basis. Official NCRB communal-incident counts diverge from civic-society compilations.",
}


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


def _load_metric_meta() -> dict:
    """Return {mid: full metric dict from manifest/metrics.yaml}. Loaded once;
    consumed by card / modal rendering for fields like definition and
    methodology_notes that don't live in SCORECARD_SPEC."""
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        data = _yaml.safe_load(f)
    return {m["id"]: m for m in data["metrics"]}


METRIC_META = _load_metric_meta()


def render_scorecard_rows() -> str:
    """Compute one HTML <tr> per metric showing Muslim/Hindu/All and gap vs
    reference, sorted by relative gap size (largest first). Cross-unit
    comparability comes from |muslim − comparator| / comparator — a 9.8pp
    gap on a 14.23% population baseline beats a 4.4pp gap on a 73% literacy
    baseline. Metrics with no usable comparator (muslim-only cards and the
    pure-count incident counters) land at the bottom."""
    rows: list[tuple[tuple[int, float], str]] = []
    for cluster, mid, name, unit, ref, higher_better in SCORECARD_SPEC:

        # Special case: time-series count metrics (communal-incidents-govt + -civic)
        if mid in ("communal-incidents-govt", "communal-incidents-civic"):
            data = load_metric(mid)
            if not data:
                continue
            latest = max(data, key=lambda r: int(r["year"]))
            val = int(float(latest["value"]))
            year = latest["year"]
            row_html = (
                f'<tr>'
                f'<td>{html.escape(name)}</td>'
                f'<td>{year}</td>'
                f'<td colspan="3" style="text-align:left">{val:,} (national aggregate)</td>'
                f'<td class="gap-neutral">{"NCRB tally; civic counts higher" if mid == "communal-incidents-govt" else "IHL: hate speech events, not riots"}</td>'
                f'</tr>'
            )
            rows.append(((1, 0.0), row_html))
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
            row_html = (
                f'<tr>'
                f'<td>{html.escape(name)}</td>'
                f'<td>{year}</td>'
                f'<td>{m_val:.2f}%</td>'
                f'<td>n/a</td>'
                f'<td>n/a</td>'
                f'<td class="{"gap-bad" if gap < 0 else "gap-good"}">{sign}{gap:.2f}pp vs 14.23% pop</td>'
                f'</tr>'
            )
            rows.append(((0, -abs(gap) / MUSLIM_POP_SHARE), row_html))
            continue

        # National rows for the LATEST year only — without this filter,
        # canonical files sorted year-DESC (e.g. imr.csv) would leak older
        # values into the dict and the row would compare across years.
        nat = [r for r in load_metric(mid) if r["geography_level"] == "national"]
        if not nat:
            continue
        latest_year = max(int(r["year"]) for r in nat)
        year = str(latest_year)
        by_rel = {r["religion"]: float(r["value"])
                  for r in nat if int(r["year"]) == latest_year}
        m_val = by_rel.get("muslim")
        h_val = by_rel.get("hindu")
        a_val = by_rel.get("all")
        muslim_str = fmt_num(m_val, unit) if m_val is not None else "n/a"
        hindu_str = fmt_num(h_val, unit) if h_val is not None else "n/a"
        all_str = fmt_num(a_val, unit) if a_val is not None else "n/a"

        # Gap computation (display) and sort key (cross-unit relative gap).
        gap_str = "n/a"
        gap_class = "gap-neutral"
        sort_key: tuple[int, float] = (1, 0.0)
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
                # Sort key uses relative gap so different units compare fairly.
                # comp_val can be 0 for edge-case metrics; guard with max().
                sort_key = (0, -abs(diff) / max(abs(comp_val), 1e-9))
        elif mid == "muslim-higher-ed-enrolment":
            gap_str = "n/a (no Hindu count in source)"
            gap_class = "gap-neutral"
        elif mid == "pop-share":
            gap_str = "baseline"
            gap_class = "gap-neutral"

        row_html = (
            f'<tr>'
            f'<td>{html.escape(name)}</td>'
            f'<td>{year}</td>'
            f'<td>{html.escape(muslim_str)}</td>'
            f'<td>{html.escape(hindu_str)}</td>'
            f'<td>{html.escape(all_str)}</td>'
            f'<td class="{gap_class}">{html.escape(gap_str)}</td>'
            f'</tr>'
        )
        rows.append((sort_key, row_html))
    rows.sort(key=lambda kv: kv[0])
    return "\n    ".join(html_row for _, html_row in rows)


def _and_join(items: list[str]) -> str:
    """English-join a short list with an Oxford comma. ['A','B','C'] -> 'A, B, and C'."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _compute_headline_stats() -> dict:
    """Walk carded metrics and return (n_behind, n_ahead, n_total_comparable,
    top_behind_names, top_ahead_names) for the headline-finding paragraph.

    'Behind' counts a metric whose Muslim value is on the bad side of polarity
    (higher_is_better True/False), OR where Muslim falls below MUSLIM_POP_SHARE
    on the representation metrics (ls-share / mla-share — the framing is "vs
    population share"). Muslim-only cards and the pure-count incident counters
    are excluded from the count because they have no directional comparator."""
    behind: list[tuple[float, str]] = []   # (abs_relative_gap, short_label)
    ahead: list[tuple[float, str]] = []
    for _cluster, mid, label, _unit, _ref, higher_better in SCORECARD_SPEC:
        # No comparator → skip from the count entirely.
        if mid in ("communal-incidents-govt", "communal-incidents-civic"):
            continue
        if mid in ("pop-share", "district-concentration-top100",
                   "muslim-higher-ed-enrolment"):
            continue
        # Representation metrics compare vs population share, not vs all-India.
        if mid in ("ls-share", "mla-share"):
            rows = [r for r in load_metric(mid) if r["geography_level"] == "national"]
            if not rows:
                continue
            latest = max(rows, key=lambda r: int(r["year"]))
            val = float(latest["value"])
            gap = val - MUSLIM_POP_SHARE
            sev = abs(gap) / MUSLIM_POP_SHARE
            (behind if gap < 0 else ahead).append((sev, label))
            continue
        # Default: compare Muslim to all-India (preferred) or Hindu. Use
        # _nat_by_religion so the comparison is within a single year (avoids
        # the multi-year-collision bug that bit the old scorecard helper).
        by_rel = _nat_by_religion(mid)
        m_val = by_rel.get("muslim")
        comp_val = by_rel.get("all") if by_rel.get("all") is not None else by_rel.get("hindu")
        if m_val is None or comp_val is None or higher_better is None:
            continue
        diff = m_val - comp_val
        is_behind = (diff < 0 and higher_better) or (diff > 0 and not higher_better)
        is_ahead = (diff > 0 and higher_better) or (diff < 0 and not higher_better)
        sev = abs(diff) / max(abs(comp_val), 1e-9)
        if is_behind:
            behind.append((sev, label))
        elif is_ahead:
            ahead.append((sev, label))
    behind.sort(reverse=True)
    ahead.sort(reverse=True)
    return {
        "n_behind": len(behind),
        "n_ahead": len(ahead),
        "n_total_comparable": len(behind) + len(ahead),
        "top_behind_names": [n for _, n in behind[:3]],
        "top_ahead_names": [n for _, n in ahead[:3]],
    }


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
<meta property="og:image" content="{site_url}/og/default.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="muslimdata.in: the state of Muslim India, in data. 21 indicators with Hindu and all-India comparison baselines.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{site_title}">
<meta name="twitter:description" content="{site_description}">
<meta name="twitter:image" content="{site_url}/og/default.png">
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
  .masthead { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px 16px; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--rule); }
  .masthead-brand { font-size: 14px; font-weight: 600; color: var(--accent); text-decoration: none; letter-spacing: -0.01em; }
  .masthead-brand:hover { text-decoration: underline; }
  .masthead-nav { display: flex; gap: 14px; margin-right: auto; margin-left: 24px; }
  .masthead-nav a { font-size: 13px; color: var(--fg); text-decoration: none; font-weight: 500; }
  .masthead-nav a:hover { color: var(--accent); }
  .masthead-meta { margin: 0; font-size: 12px; color: var(--muted); }
  .masthead-meta a { color: var(--muted); }
  .headline-finding { font-size: 16px; line-height: 1.55; color: var(--fg); margin: 0 0 24px; max-width: 70em; }
  .headline-finding em { font-style: normal; color: var(--accent); font-weight: 600; }
  .headline-method {
    display: inline-block; margin-left: 6px;
    color: var(--muslim); text-decoration: none;
    font-size: 14px; font-weight: 500; white-space: nowrap;
  }
  .headline-method:hover { text-decoration: underline; }
  .compare-toggle {
    display: inline-flex; align-items: center; gap: 8px; margin: 6px 0 20px;
    padding: 6px 10px 6px 14px; border: 1px solid var(--rule); border-radius: 999px;
    background: var(--card); font-size: 12px;
  }
  .compare-toggle-label { color: var(--muted); }
  .compare-toggle-btn {
    border: 1px solid var(--rule); background: var(--bg); color: var(--fg);
    font-size: 12px; font-weight: 500; padding: 4px 12px; border-radius: 999px;
    cursor: pointer; transition: background .15s, border-color .15s, color .15s;
  }
  .compare-toggle-btn:hover { border-color: var(--accent); color: var(--accent); }
  .compare-toggle-btn.active {
    background: var(--accent); border-color: var(--accent); color: #fff;
  }
  /* Default: hide vs-Hindu pills. The compare toggle adds .compare-hindu to
     <body>, which swaps which alternate is shown. */
  .card-comp[data-comp-type="vs-hindu"] { display: none; }
  body.compare-hindu .card-comp[data-comp-type="vs-all"] { display: none; }
  body.compare-hindu .card-comp[data-comp-type="vs-hindu"] { display: block; }
  h2 { font-size: 20px; margin: 0 0 4px; letter-spacing: -0.01em; font-weight: 600; }
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
  .methodology {
    font-size: 12.5px; color: var(--muted); margin: 14px 0 0;
    border-left: 3px solid var(--rule); padding-left: 12px;
  }
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
    margin: 32px 0 6px; padding: 6px 0 0;
    border-top: 1px solid var(--rule);
  }
  .cluster-intro {
    margin: 0 0 14px; max-width: 70em;
    font-size: 14px; color: var(--muted); line-height: 1.5;
  }
  /* Scorecard moved below the cards (Commit BP); collapsed-by-default
     <details> wrapper so a new visitor sees the card story first and the
     dense table view is one click away for power users. */
  .scorecard-details {
    margin: 40px 0 24px;
    border: 1px solid var(--rule); border-radius: 8px;
    background: var(--card);
  }
  .scorecard-details summary {
    list-style: none; cursor: pointer;
    padding: 14px 18px;
    display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
    border-radius: 8px;
  }
  .scorecard-details summary::-webkit-details-marker { display: none; }
  .scorecard-details summary::before {
    content: "▸"; color: var(--accent); font-size: 14px;
    margin-right: 4px; transition: transform 0.15s;
    display: inline-block;
  }
  .scorecard-details[open] summary::before { content: "▾"; }
  .scorecard-details summary:hover { background: #faf7f0; }
  .scorecard-summary-title { font-size: 16px; font-weight: 600; color: var(--fg); }
  .scorecard-summary-detail { font-size: 13px; color: var(--muted); }
  .scorecard-content { padding: 4px 18px 18px; }
  .scorecard table { font-size: 13px; }
  .scorecard-table tbody tr:hover { background: #faf7f0; }
  .scorecard-search-wrap { margin-top: 10px; }
  .scorecard-search {
    width: 100%; max-width: 320px;
    padding: 7px 12px; font-size: 13px; font-family: inherit;
    border: 1px solid var(--rule); border-radius: 6px; background: var(--card);
    color: var(--fg);
  }
  .scorecard-search:focus { outline: 2px solid var(--accent); outline-offset: 1px; border-color: var(--accent); }
  .scorecard-search::placeholder { color: var(--muted); }
  .scorecard-table tbody tr.search-hidden { display: none; }
  .scorecard-table th.sortable {
    cursor: pointer; user-select: none;
  }
  .scorecard-table th.sortable:hover { color: var(--accent); }
  .scorecard-table th.sortable::after {
    content: " ⇅"; font-size: 10px; color: var(--rule);
  }
  .scorecard-table th.sorted-asc::after { content: " ↑"; color: var(--accent); }
  .scorecard-table th.sorted-desc::after { content: " ↓"; color: var(--accent); }
  /* Generic sortable tables (e.g. the top-100 districts drill-down). Click a
     header to sort; numeric columns carry data-sort raw values so "4.71M" /
     "502k" sort by magnitude, not string. */
  .sortable-table th.sortable { cursor: pointer; user-select: none; white-space: nowrap; }
  .sortable-table th.sortable:hover { color: var(--accent); }
  .sortable-table th.sortable::after { content: " ⇅"; font-size: 9px; color: var(--muted); }
  .sortable-table th.sorted-asc::after { content: " ↑"; color: var(--accent); }
  .sortable-table th.sorted-desc::after { content: " ↓"; color: var(--accent); }
  .scorecard-table .gap-bad { color: var(--accent); font-weight: 600; }
  .scorecard-table .gap-good { color: #2d6a3e; font-weight: 600; }
  .scorecard-table .gap-neutral { color: var(--muted); }
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
  .card-polarity {
    font-size: 11px; color: var(--muted); margin: -2px 0 8px;
    font-weight: 500; letter-spacing: 0.01em; text-transform: uppercase;
  }
  .card-polarity span { color: #2d6a3e; margin-right: 2px; font-weight: 600; }
  .card-polarity.polarity-down span { color: var(--accent); }
  .card-expand {
    position: absolute; top: 12px; right: 14px;
    font-size: 13px; color: var(--rule); pointer-events: none;
    transition: color .15s;
  }
  .card { position: relative; }
  .card:hover .card-expand { color: var(--accent); }
  .modal-body .card-expand { display: none; }
  .card-method { display: none; }
  .modal-body .card-method {
    display: block; margin-top: 18px; padding-top: 16px;
    border-top: 1px solid var(--rule);
  }
  .modal-body .card-method-title {
    margin: 0 0 8px; font-size: 14px; color: var(--muted);
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
  }
  .modal-body .card-method p {
    margin: 0 0 10px; font-size: 14px; color: var(--fg); line-height: 1.55;
    max-width: 56em; white-space: pre-line;
  }
  .modal-body .card-method b { color: var(--accent); font-weight: 600; }
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
  /* Kicker line above the note (e.g. "the top 10 districts alone hold 14%"):
     full width, accent-coloured, the card's punchiest single takeaway. */
  .comp-kicker { grid-column: 1 / -1; text-align: left; font-size: var(--t-sm); color: var(--accent); font-weight: 600; line-height: 1.4; margin-bottom: 4px; }
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
  /* Horizontal scroll wrapper for the scorecard table so the table can stay
     wide enough to show every column without forcing horizontal scroll on the
     whole page (which broke the mobile layout). */
  .scorecard-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  @media (max-width: 560px) {
    .cards { grid-template-columns: 1fr; }
    h1 { font-size: 24px; }
    .headline-finding { font-size: 14px; }
    /* Drop the methodology callout to its own line on narrow screens so it
       doesn't wrap awkwardly inside the headline-finding paragraph. */
    .headline-method { display: block; margin: 10px 0 0; }
    .masthead { gap: 6px 12px; }
    .masthead-nav { margin-left: 0; gap: 10px; }
    .masthead-nav a { padding: 12px 4px; min-height: 44px; display: inline-flex; align-items: center; }
    .compare-toggle { flex-wrap: wrap; padding: 8px 12px; }
    .compare-toggle-label { width: 100%; margin-bottom: 4px; }
    .compare-toggle-btn { padding: 0 16px; font-size: 13px; min-height: 44px; }
    .scorecard-search { padding: 0 14px; font-size: 14px; min-height: 44px; }
    .scorecard-table { font-size: 12px; }
    .scorecard-table th, .scorecard-table td { padding: 6px 4px; }
    /* Section intros: lighter on mobile so they don't dominate. */
    .cluster-intro { font-size: 13px; }
    /* Pill labels carry the comparator value now (Commit BP). On narrow
       cards the 3-pill row gets tight, so tighten typography and pad. */
    .comp-label { font-size: 10.5px; line-height: 1.2; }
    .comp-verdict { font-size: 12.5px; }
    .comp-detail { font-size: 9.5px; }
    .card-comp { padding: 4px 3px; }
    /* Modal actions: 4 buttons (prev, next, share, close) need to fit at
       375px. Hide text labels on the prev/next/share buttons, leaving
       chevrons + share-icon as compact controls. */
    .modal-nav-label { display: none; }
    .modal-nav { padding: 0 10px; }
    .modal-share-label { display: none; }
    .modal-share { padding: 0 10px; gap: 0; }
  }

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
  .modal-close, .modal-share, .modal-nav {
    background: var(--card); border: 1px solid var(--rule); border-radius: 6px;
    cursor: pointer; color: var(--muted); padding: 0;
    -webkit-appearance: none; appearance: none;
    line-height: 1; white-space: nowrap;
    transition: background .15s, border-color .15s, color .15s;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .modal-close { width: 34px; height: 34px; font-size: 22px; }
  .modal-share { height: 34px; padding: 0 12px; gap: 6px; font-size: 13px; font-weight: 500; }
  .modal-nav { height: 34px; padding: 0 10px; font-size: 13px; font-weight: 500; }
  .modal-nav span[aria-hidden] { font-size: 16px; line-height: 1; }
  .modal-close:hover, .modal-share:hover, .modal-nav:hover {
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
  <nav class="masthead-nav">
    <a href="/about/">About</a>
    <a href="https://github.com/iqbash1/indian-muslims-dashboard">GitHub</a>
  </nav>
  <p class="masthead-meta">Last updated {timestamp}</p>
</div>
<h1>The state of Muslim India, in data</h1>

<p class="headline-finding">
  India's roughly 200 million Muslims, or <em>14.2%</em> of the population
  (Census 2011), trail the all-India average on <em>{n_behind} of
  {n_total_comparable}</em> living-conditions indicators tracked here.
  The biggest gaps are on <em>{top_behind_joined}</em>.{ahead_clause}
  Scroll down to see where and by how much.
  <a class="headline-method" href="/about/">How are these measured? →</a>
</p>

<section class="intro">
  <p>Each card compares the latest Muslim figure to Hindu and all-India
  baselines, drawn from primary government surveys. Click any card for
  a larger view with the full methodology. Every card also links to its
  source CSV.</p>
</section>
<div class="status-bar">
  <span><b>{n_metrics}</b> indicators</span>
  <span><b>{n_sources}</b> primary sources</span>
  <span><b>{n_rows}</b> data points</span>
</div>
<div class="compare-toggle" role="radiogroup" aria-label="Choose comparison baseline for every card">
  <span class="compare-toggle-label">Compare Muslim outcomes to:</span>
  <button id="compare-all" class="compare-toggle-btn active" role="radio" aria-checked="true" type="button">all-India</button>
  <button id="compare-hindu" class="compare-toggle-btn" role="radio" aria-checked="false" type="button">Hindu only</button>
</div>

{cluster_grids}

<!-- SCORECARD: moved below the cards (Commit BP) so a new visitor sees the
     visual story before the dense table view. Collapsed by default; the
     summary doubles as both the title and the click-to-expand affordance. -->
<details class="scorecard-details">
  <summary class="scorecard-summary">
    <span class="scorecard-summary-title">All {n_metrics} indicators in one table</span>
    <span class="scorecard-summary-detail">sorted by gap size · click to expand</span>
  </summary>
  <div class="scorecard-content">
    <div class="scorecard-search-wrap">
      <input type="search" id="scorecard-search" class="scorecard-search"
        placeholder="Search metrics…" aria-label="Search metrics in the scorecard">
    </div>
    <div class="scorecard-scroll">
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
    </div>
    <p class="methodology">"Gap" is the Muslim value minus the reference baseline (Hindu where
    available, otherwise all-India). Red means the Muslim outcome is worse than the reference;
    green means it is better. For justice metrics, cells show the absolute count alongside the
    incarceration rate per 100,000 people of that religion, and the gap is the Muslim-to-Hindu
    rate ratio (1.0× means parity; above 1.0× means Muslims are overrepresented).</p>
  </div>
</details>

<div class="modal-overlay" id="modal-overlay" hidden role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <div class="modal" role="document">
    <div class="modal-actions">
      <button class="modal-nav" id="modal-prev" aria-label="Previous metric" title="Previous metric (←)">
        <span aria-hidden="true">‹</span><span class="modal-nav-label"> Prev</span>
      </button>
      <button class="modal-nav" id="modal-next" aria-label="Next metric" title="Next metric (→)">
        <span class="modal-nav-label">Next </span><span aria-hidden="true">›</span>
      </button>
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

// Scorecard search: filters table rows by case-insensitive substring match
// against the metric name column. Empty input restores all rows.
(function setupScorecardSearch() {
  const input = document.getElementById('scorecard-search');
  const table = document.getElementById('scorecard');
  if (!input || !table) return;
  const rows = Array.from(table.querySelectorAll('tbody tr'));
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    rows.forEach(r => {
      const name = r.querySelector('td')?.textContent.toLowerCase() || '';
      r.classList.toggle('search-hidden', q.length > 0 && !name.includes(q));
    });
  });
})();

// Generic sortable tables (the top-100 districts drill-down). Uses event
// delegation off document so it works for tables cloned into the modal too
// (cloneNode does not copy listeners). Per-table sort state is stashed on the
// table's dataset. Numeric columns (data-type="num") sort descending on first
// click, for a "top districts" table you want the biggest first; text
// columns sort ascending first. Cells carry data-sort raw values so formatted
// strings like "4.71M" / "502k" sort by magnitude rather than by string.
(function setupSortableTables() {
  document.addEventListener('click', (e) => {
    const h = e.target.closest('table.sortable-table th.sortable');
    if (!h) return;
    const table = h.closest('table');
    const col = parseInt(h.dataset.col);
    const numeric = h.dataset.type === 'num';
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    const prevCol = parseInt(table.dataset.sortCol ?? '-1');
    const prevDir = parseInt(table.dataset.sortDir ?? '1');
    const dir = (prevCol === col) ? -prevDir : (numeric ? -1 : 1);
    const key = (cell) => {
      const ds = cell.getAttribute('data-sort');
      if (ds !== null && ds !== '') return parseFloat(ds);
      return cell.textContent.trim().toLowerCase();
    };
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {
      const ka = key(a.cells[col]), kb = key(b.cells[col]);
      if (ka < kb) return -dir;
      if (ka > kb) return dir;
      return 0;
    });
    rows.forEach((r) => tbody.appendChild(r));
    table.querySelectorAll('th.sortable').forEach((x) =>
      x.classList.remove('sorted-asc', 'sorted-desc'));
    h.classList.add(dir === 1 ? 'sorted-asc' : 'sorted-desc');
    table.dataset.sortCol = col;
    table.dataset.sortDir = dir;
  });
})();

// --- Card-grid chart helpers (generated card initialisers call these) ---
function _valueLabels(decimals, suffix) {
  return { id: 'vl', afterDatasetsDraw(chart) {
    const { ctx } = chart; const meta = chart.getDatasetMeta(0);
    ctx.save(); ctx.font = '600 11px -apple-system, system-ui, sans-serif';
    ctx.textBaseline = 'middle'; ctx.fillStyle = '#555';
    meta.data.forEach((bar, i) => { const v = chart.data.datasets[0].data[i];
      // Integer-count labels get thousands separators ("1,165"); decimal
      // labels (percentages, rates) keep fixed precision ("73.3%").
      const label = (decimals === 0 ? Math.round(v).toLocaleString() : v.toFixed(decimals)) + suffix;
      ctx.fillText(label, bar.x + 6, bar.y); });
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

function hbar(id, labels, values, colors, suffix, decimals, refValue, refLabel, beginAtZero) {
  _spec(id, 'hbar', Array.from(arguments).slice(1));
  // beginAtZero defaults to false (house style: bars hug the data so
  // community differences stay visible). Pass true when the bars are a
  // magnitude comparison where a non-zero baseline would exaggerate the
  // ratio (e.g. a 2-year count: 668 vs 1,165 must read as "nearly double").
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 3, barPercentage: 0.82, categoryPercentage: 0.86 }] },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false, animation: false,
      layout: { padding: { right: 46, top: 14 } },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => c.parsed.x.toFixed(decimals) + suffix } } },
      scales: { x: { display: false, grace: '8%', beginAtZero: beginAtZero === true }, y: { grid: { display: false }, border: { display: false }, ticks: { font: { size: 11 } } } },
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

// Cumulative concentration curve: cumulative share of a population (y) against
// rank-ordered units (x), e.g. "% of all Indian Muslims" vs "top-N districts".
// points = [[rank, cumPct], …]; x is a true linear axis so the concave shape
// reads honestly (steep early = front-loaded concentration). markN highlights
// one rank (the kicker anchor) with a solid dot. Y is pinned at 0 here (unlike
// the house no-forced-zero rule, which targets comparison charts): a CUMULATIVE
// share genuinely builds from zero, and letting grace pad below 0 would draw a
// meaningless negative-share region.
function concentrationCurve(id, points, markN, suffix) {
  _spec(id, 'concentrationCurve', Array.from(arguments).slice(1));
  const curve = points.map((p) => ({ x: p[0], y: p[1] }));
  const datasets = [{
    data: curve, borderColor: '#7b1d22', backgroundColor: 'rgba(123,29,34,.10)',
    fill: true, tension: 0.25, pointRadius: 0, borderWidth: 2, order: 2,
  }];
  const mark = markN ? points.find((p) => p[0] === markN) : null;
  if (mark) datasets.push({
    data: [{ x: mark[0], y: mark[1] }], borderColor: '#7b1d22',
    backgroundColor: '#7b1d22', pointRadius: 4, pointHoverRadius: 6,
    showLine: false, order: 1,
  });
  const maxX = points.length ? points[points.length - 1][0] : 100;
  new Chart(document.getElementById(id), {
    type: 'line',
    data: { datasets: datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        title: (items) => 'Top ' + items[0].parsed.x + ' districts',
        label: (c) => c.parsed.y.toFixed(1) + suffix + ' of all Muslims',
      } } },
      scales: {
        x: { type: 'linear', min: 1, max: maxX, grid: { display: false },
             ticks: { font: { size: 10 }, maxTicksLimit: 6 },
             title: { display: true, text: 'top-N districts (ranked by Muslim population)',
                      font: { size: 10 }, color: '#666' } },
        y: { min: 0, grace: '6%',
             ticks: { font: { size: 10 }, callback: (v) => v + suffix } },
      },
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
    // Modal view crowds 5+ labels into the same right edge, so dial the
    // weight back to medium so the stack reads less aggressive. Cards
    // typically only label the Muslim line (mode='card'), so keep the
    // bolder weight there for emphasis.
    const weight = chart._mode === 'modal' ? '500' : '600';
    ctx.font = weight + ' 10px -apple-system, system-ui, sans-serif';
    ctx.textBaseline = 'middle';

    // Collect each dataset's natural label position at its terminal point.
    const items = [];
    chart.data.datasets.forEach((d, i) => {
      // _isRefline marks aggregates like All-India. In modal mode they are
      // suppressed (the per-community labels already cover the field). In
      // card mode the chart only carries Muslim + the All-India refline, so
      // labelling All-India is what gives the dashed grey line a name.
      if (d._isRefline && chart._mode !== 'card') return;
      if (d._noEndLabel) return;
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
function trendChart(id, years, seriesMap, allSeries, suffix, hasBreak, refLine, dashedExtras, mode) {
  mode = mode || 'card';
  _spec(id, 'trendChart', Array.from(arguments).slice(1));
  const ds = [];
  for (const rel of TREND_ORDER) {
    if (!seriesMap[rel]) continue;
    // Card view shows only the Muslim line; the smaller real-estate can't
    // carry five non-overlapping community labels. Modal re-render passes
    // mode='modal' to surface the full community comparison.
    if (mode === 'card' && rel !== 'muslim') continue;
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
    // allSeries may be a raw array (legacy) or {values, label} when the
    // build wants to flag a non-default label (e.g. "Community median"
    // when source all-India was sparse).
    const values = Array.isArray(allSeries) ? allSeries : allSeries.values;
    const labelText = Array.isArray(allSeries) ? 'All-India' : (allSeries.label || 'All-India');
    const allDs = {
      label: labelText, data: values, borderColor: '#9e9e9e', backgroundColor: 'transparent',
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
  const chart = new Chart(document.getElementById(id), {
    type: 'line',
    data: { labels: years, datasets: ds },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      layout: { padding: { right: 64, top: 6 } },
      // Hovering anywhere along the x-axis selects every line at that year,
      // so the tooltip surfaces the full point-in-time community comparison
      // (Muslim 40, Hindu 28, Christian 25, ...) instead of just one line.
      interaction: { mode: 'index', intersect: false, axis: 'x' },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: 'index', intersect: false,
          itemSort: (a, b) => b.parsed.y - a.parsed.y,
          // Drop null years (lines that don't have data at this x). Keep
          // refline datasets (All-India / median) so a card-view tooltip
          // shows both the Muslim line AND the comparison reference.
          filter: (item) => item.parsed.y != null,
          callbacks: { label: (c) => c.dataset.label + ': ' + c.parsed.y + suffix },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { beginAtZero: false, grace: '12%', grid: { color: '#f0ede4', drawTicks: false },
             border: { display: false }, ticks: { font: { size: 10 }, color: '#999' } },
      },
    },
    plugins: [_endLabels()],
  });
  chart._mode = mode;  // endLabels plugin reads this to dial back font-weight in modal
  return chart;
}

{card_charts}

// Chart.js sizes its canvas to the parent at construction. Viewport changes
// (mobile rotation, desktop->mobile resize) leave the canvas at its original
// width and stretch the card with it. On every resize, clear each canvas's
// inline dimensions so the card collapses to its true grid track width, then
// call Chart.resize() to re-measure. Debounced so a slow drag doesn't fire
// hundreds of times.
(function resizeChartsOnViewportChange() {
  let pending = null;
  window.addEventListener('resize', () => {
    if (pending) clearTimeout(pending);
    pending = setTimeout(() => {
      pending = null;
      const charts = Object.keys(CHART_SPECS).map(Chart.getChart).filter(Boolean);
      // Phase 1: clear every canvas's inline size so each card collapses to
      // its true grid track width. Done in a single pass so the layout reflow
      // (forced by reading offsetWidth below) settles for all cards at once.
      for (const c of charts) {
        c.canvas.style.width = '';
        c.canvas.style.height = '';
        c.canvas.removeAttribute('width');
        c.canvas.removeAttribute('height');
      }
      void document.body.offsetWidth;  // force layout reflow
      // Phase 2: now that the grid tracks have re-sized, Chart.js measures the
      // (correctly-sized) parent and resizes the canvas to fit.
      for (const c of charts) c.resize();
    }, 120);
  });
})();

// Compare toggle: flips every comparison pill on the page between vs all-India
// (default) and vs Hindu. Setting persists across sessions via localStorage so
// the visitor's last choice is honoured on the next visit.
(function compareToggle() {
  const allBtn = document.getElementById('compare-all');
  const hinduBtn = document.getElementById('compare-hindu');
  if (!allBtn || !hinduBtn) return;
  function set(mode) {
    const hindu = mode === 'hindu';
    document.body.classList.toggle('compare-hindu', hindu);
    allBtn.classList.toggle('active', !hindu);
    hinduBtn.classList.toggle('active', hindu);
    allBtn.setAttribute('aria-checked', String(!hindu));
    hinduBtn.setAttribute('aria-checked', String(hindu));
    try { localStorage.setItem('md_compare', mode); } catch (e) { /* private mode */ }
    if (typeof gtag === 'function') gtag('event', 'compare_toggle', { mode });
  }
  allBtn.addEventListener('click', () => set('all'));
  hinduBtn.addEventListener('click', () => set('hindu'));
  let stored = 'all';
  try { stored = localStorage.getItem('md_compare') || 'all'; } catch (e) { /* private */ }
  set(stored);
})();

// Modal: clicking a card opens a larger view of the same chart by cloning
// the card into the modal body and re-rendering the chart on a fresh canvas
// using the spec captured by _spec() in the factory functions. Shareable via
// per-metric stub pages at /m/{slug}/ that redirect into /#{slug}.
(function modalSetup() {
  const overlay = document.getElementById('modal-overlay');
  const body = document.getElementById('modal-body');
  const closeBtn = document.getElementById('modal-close');
  const shareBtn = document.getElementById('modal-share');
  const prevBtn = document.getElementById('modal-prev');
  const nextBtn = document.getElementById('modal-next');
  const factories = { hbar, lineChart, trendChart, concentrationCurve };
  let modalChart = null;
  let activeMid = null;

  // Ordered list of metric IDs in card-grid order, built once at setup so
  // prev/next navigation cycles through cards in the same sequence the
  // visitor sees them on the page (and wraps at both ends).
  const cardOrder = Array.from(document.querySelectorAll('.cards .card'))
    .map((c) => c.getAttribute('data-metric-id'))
    .filter(Boolean);

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
        // trendChart's signature is (id, years, seriesMap, allSeries, suffix,
        // hasBreak, refLine, dashedExtras, mode). Most call sites omit the
        // trailing optional args, so we pad to length 7 before forcing
        // mode='modal' at position 7 so it lands in the correct slot rather
        // than overwriting refLine.
        let args = spec.args;
        if (spec.fnName === 'trendChart') {
          args = spec.args.slice(0, 7);
          while (args.length < 7) args.push(undefined);
          args.push('modal');
        }
        factories[spec.fnName](modalId, ...args);
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

  // Prev/next navigation: cycle through cardOrder with wrap-around, so a
  // visitor who opens the first card sees prev land on the last (rather
  // than being a dead end). Calls openByMid which rebuilds the modal body
  // for the new metric and updates the URL hash.
  function nav(delta) {
    if (!activeMid || cardOrder.length === 0) return;
    const i = cardOrder.indexOf(activeMid);
    if (i < 0) return;
    const j = (i + delta + cardOrder.length) % cardOrder.length;
    openByMid(cardOrder[j]);
  }

  closeBtn.addEventListener('click', closeModal);
  prevBtn.addEventListener('click', () => nav(-1));
  nextBtn.addEventListener('click', () => nav(1));
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !overlay.hidden) {
      closeModal();
      return;
    }
    // Arrow keys navigate between metrics when the modal is open. Skip if
    // focus is in an editable element (don't hijack typing in the share
    // tooltip or a future inline input).
    if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && !overlay.hidden) {
      const t = document.activeElement;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      nav(e.key === 'ArrowLeft' ? -1 : 1);
      e.preventDefault();
      return;
    }
    // Focus trap: cycle Tab focus only among interactive elements inside the
    // open modal so screen-reader / keyboard users can't tab into the page
    // behind the overlay.
    if (e.key === 'Tab' && !overlay.hidden) {
      const focusables = overlay.querySelectorAll(
        'a[href], button:not([disabled]), input, select, textarea, summary, [tabindex]:not([tabindex="-1"])'
      );
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });

  // Share: copy the per-metric permalink to clipboard. The /m/{slug}/ stub
  // path carries the per-metric OG meta so social cards render properly.
  shareBtn.addEventListener('click', () => {
    if (!activeMid) return;
    const card = body.querySelector('.card');
    const name = card?.getAttribute('data-metric-name') || activeMid;
    const url = location.origin + '/m/' + encodeURIComponent(activeMid) + '/';
    const text = 'muslimdata.in: ' + name + '\\n' + url;
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
<meta property="og:image" content="{site_url}/og/{mid}.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{og_image_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{site_url}/og/{mid}.png">
<meta http-equiv="refresh" content="0; url={site_url}/#{mid}">
<script>location.replace({redirect_target});</script>
<style>body{{font:14px -apple-system,system-ui,sans-serif;color:#666;padding:40px;text-align:center}}</style>
</head>
<body>
<p>Redirecting to <a href="{site_url}/#{mid}">muslimdata.in</a>...</p>
</body>
</html>
"""


# ----- Open Graph / Twitter Card image renderer -----
# 1200x630 PNG per metric, written to docs/og/{mid}.png, referenced from the
# matching stub page's <meta og:image>. Reuses the same hero + comparison
# helpers the card grid uses so social previews match the live card values.

OG_W, OG_H = 1200, 630
_OG_FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
_OG_FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
_OG_BG = (250, 250, 247)      # site bg cream
_OG_FG = (26, 26, 26)         # body fg
_OG_MUTED = (102, 102, 102)   # site --muted
_OG_ACCENT = (123, 29, 34)    # site --accent maroon
_OG_TIER = {                  # match TIER_HEX for the comp pill color
    "good": (6, 95, 70),
    "bad": (153, 27, 27),
    "mid": (85, 85, 85),
    "neutral": (85, 85, 85),
}


def _og_font(size: int, bold: bool = False):
    path = _OG_FONT_BOLD if bold else _OG_FONT_REGULAR
    try:
        return ImageFont.truetype(path, size)
    except (OSError, AttributeError):
        return ImageFont.load_default()


def _og_wrap(draw, text: str, font, max_w: int, max_lines: int = 2) -> list[str]:
    """Greedy word-wrap by pixel width. Last line is ellipsised if it overflows."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = (cur + " " + w).strip()
        if draw.textlength(cand, font=font) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_w:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        lines[-1] = last + "…"
    return lines


def _og_data_for_metric(m: dict):
    """Compute the OG payload for one metric using the same data path the
    card grid uses. Returns None when the metric has no carded display."""
    disp = m.get("display", {}).get("scorecard")
    if not disp or disp.get("include", True) is False:
        return None
    mid = m["id"]
    name = m.get("name", disp.get("label", mid))
    unit = disp["unit_format"]
    hib = disp.get("higher_is_better", m.get("higher_is_better"))
    special = disp.get("special_render")
    caption = CAPTION.get(mid, "")
    polarity = "Higher is better" if hib is True else ("Lower is better" if hib is False else "")

    if special == "time_series_count":
        rows = sorted([r for r in load_metric(mid) if r["geography_level"] == "national"],
                      key=lambda r: int(r["year"]))
        if not rows:
            return None
        val = int(float(rows[-1]["value"]))
        comp_label = comp_value = ""
        if len(rows) >= 2:
            first = int(float(rows[0]["value"]))
            comp_label = f"{rows[0]['year']} → {rows[-1]['year']}"
            comp_value = f"{first:,} → {val:,}"
        return dict(name=name, hero=f"{val:,}", caption=caption or "events",
                    year=str(rows[-1]["year"]), comp_label=comp_label,
                    comp_value=comp_value, comp_class="mid",
                    polarity="Lower is better")

    if special == "time_series_latest":
        rows = sorted([r for r in load_metric(mid) if r["geography_level"] == "national"],
                      key=lambda r: int(r["year"]))
        if not rows:
            return None
        val = float(rows[-1]["value"])
        gap = val - MUSLIM_POP_SHARE
        cls = "bad" if gap < 0 else ("good" if gap > 0 else "mid")
        return dict(name=name, hero=fmt_num(val, unit), caption=caption,
                    year=str(rows[-1]["year"]),
                    comp_label="vs population", comp_value=f"{gap:+.1f}pp",
                    comp_class=cls, polarity=polarity)

    # muslim-only cards (no community comparator)
    if mid in ("pop-share", "district-concentration-top100", "muslim-higher-ed-enrolment"):
        muslim = _nat_by_religion(mid).get("muslim")
        if muslim is None:
            return None
        year = _year_of(mid)
        return dict(name=name, hero=fmt_num(muslim, unit), caption=caption,
                    year=str(year) if year else "", comp_label="",
                    comp_value="", comp_class="mid", polarity=polarity)

    # default comparison card — mirror _card_comparison()
    nat = _nat_by_religion(mid)
    muslim = nat.get("muslim")
    if muslim is None:
        return None
    all_v = nat.get("all")
    years, series, _ = _nat_trend(mid)
    comp_label = "vs all-India"
    if years:
        all_series, _, pill_label = _comparison_series(series, years)
        if all_series:
            latest = next((v for v in reversed(all_series) if v is not None), None)
            if latest is not None:
                all_v = latest
                comp_label = pill_label or comp_label
    comp_value = ""
    comp_class = "mid"
    if all_v is not None:
        gap = muslim - all_v
        cls = _verdict(gap, hib)
        comp_value = f"{_gap_str(gap, unit)} {_verdict_word(cls)}"
        comp_class = cls
    year = _year_of(mid)
    return dict(name=name, hero=fmt_num(muslim, unit), caption=caption,
                year=str(year) if year else "",
                comp_label=comp_label if comp_value else "",
                comp_value=comp_value, comp_class=comp_class, polarity=polarity)


def _render_og_image(out_path: pathlib.Path, payload: dict) -> None:
    """Draw a 1200x630 PNG to out_path from the OG payload."""
    img = Image.new("RGB", (OG_W, OG_H), _OG_BG)
    draw = ImageDraw.Draw(img)
    margin = 64
    # Top accent rule + brand row.
    draw.rectangle([(0, 0), (OG_W, 12)], fill=_OG_ACCENT)
    draw.text((margin, 36), "muslimdata.in", font=_og_font(28, bold=True), fill=_OG_ACCENT)
    # Polarity badge (top-right).
    if payload.get("polarity"):
        pol_font = _og_font(20, bold=True)
        pol_text = payload["polarity"].upper()
        pol_w = draw.textlength(pol_text, font=pol_font)
        draw.text((OG_W - margin - pol_w, 42), pol_text, font=pol_font, fill=_OG_MUTED)
    # Metric name, up to 2 lines.
    name_font = _og_font(56, bold=True)
    name_lines = _og_wrap(draw, payload["name"], name_font, OG_W - 2 * margin, max_lines=2)
    for i, line in enumerate(name_lines):
        draw.text((margin, 130 + i * 68), line, font=name_font, fill=_OG_FG)
    # Hero number (left half).
    hero_y = 310
    hero_font = _og_font(180, bold=True)
    draw.text((margin, hero_y), payload["hero"], font=hero_font, fill=_OG_ACCENT)
    cap_y = hero_y + 200
    if payload.get("caption"):
        draw.text((margin, cap_y), payload["caption"], font=_og_font(28), fill=_OG_FG)
        cap_y += 40
    if payload.get("year"):
        draw.text((margin, cap_y), payload["year"], font=_og_font(24), fill=_OG_MUTED)
    # Comparison block (right half), only when there's something to compare.
    if payload.get("comp_label") and payload.get("comp_value"):
        right_x = OG_W - margin
        label_font = _og_font(28)
        val_font = _og_font(54, bold=True)
        label_w = draw.textlength(payload["comp_label"], font=label_font)
        val_w = draw.textlength(payload["comp_value"], font=val_font)
        draw.text((right_x - label_w, hero_y + 40),
                  payload["comp_label"], font=label_font, fill=_OG_MUTED)
        draw.text((right_x - val_w, hero_y + 90),
                  payload["comp_value"], font=val_font,
                  fill=_OG_TIER.get(payload.get("comp_class", "mid"), _OG_MUTED))
    # Footer.
    foot = "The state of Muslim India, in data · Hindu and all-India comparison baselines"
    draw.text((margin, OG_H - 60), foot, font=_og_font(22), fill=_OG_MUTED)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)


def _render_og_default(out_path: pathlib.Path) -> None:
    """Generic site OG card — used by the homepage and About page."""
    img = Image.new("RGB", (OG_W, OG_H), _OG_BG)
    draw = ImageDraw.Draw(img)
    margin = 64
    draw.rectangle([(0, 0), (OG_W, 12)], fill=_OG_ACCENT)
    draw.text((margin, 36), "muslimdata.in", font=_og_font(28, bold=True), fill=_OG_ACCENT)
    title_font = _og_font(86, bold=True)
    title_lines = _og_wrap(draw, "The state of Muslim India, in data.",
                           title_font, OG_W - 2 * margin, max_lines=2)
    y = 180
    for line in title_lines:
        draw.text((margin, y), line, font=title_font, fill=_OG_FG)
        y += 104
    draw.text((margin, y + 20), "21 indicators across 6 themes.",
              font=_og_font(32), fill=_OG_FG)
    draw.text((margin, y + 70), "Hindu and all-India comparison baselines on every metric.",
              font=_og_font(32), fill=_OG_MUTED)
    draw.text((margin, OG_H - 60),
              "Census · NFHS · PLFS · AISHE · NCRB · PRS-ECI · India Hate Lab",
              font=_og_font(22), fill=_OG_MUTED)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)


def _emit_og_images(out_dir: pathlib.Path) -> int:
    """Generate a 1200x630 PNG per live metric at /og/{mid}.png plus a
    /og/default.png for the homepage and About page. Returns the count."""
    if Image is None:
        print("WARN: Pillow not installed; skipping OG image generation")
        return 0
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        data = _yaml.safe_load(f)
    og_dir = out_dir / "og"
    og_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for m in data["metrics"]:
        payload = _og_data_for_metric(m)
        if not payload:
            continue
        _render_og_image(og_dir / f"{m['id']}.png", payload)
        written += 1
    _render_og_default(og_dir / "default.png")
    return written


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
            og_image_alt=html.escape(f"{name}: Indian Muslims vs Hindu and all-India baselines on muslimdata.in"),
            redirect_target=json.dumps(f"{SITE_URL}/#{mid}"),
        )
        stub_dir = stubs_root / mid
        stub_dir.mkdir(exist_ok=True)
        (stub_dir / "index.html").write_text(page)
        written += 1
    return written


ABOUT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>About muslimdata.in</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="About muslimdata.in: mission, methodology, sources, and how to contribute or report errors.">
<link rel="canonical" href="{site_url}/about/">
<meta property="og:title" content="About muslimdata.in">
<meta property="og:description" content="A scorecard of living-conditions indicators for India's Muslim population, with Hindu and all-India comparison baselines on every metric.">
<meta property="og:url" content="{site_url}/about/">
<meta property="og:type" content="article">
<meta property="og:image" content="{site_url}/og/default.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="muslimdata.in: the state of Muslim India, in data. 21 indicators with Hindu and all-India comparison baselines.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="About muslimdata.in">
<meta name="twitter:description" content="A scorecard of living-conditions indicators for India's Muslim population, with Hindu and all-India comparison baselines on every metric.">
<meta name="twitter:image" content="{site_url}/og/default.png">
<script src="/js/analytics.js" defer></script>
<style>
  :root {{
    --fg: #1a1a1a; --muted: #666; --bg: #fafaf7; --card: #ffffff;
    --rule: #e6e3da; --accent: #7b1d22;
  }}
  body {{
    font: 16px/1.6 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    color: var(--fg); background: var(--bg); margin: 0; padding: 0;
  }}
  .page {{ max-width: 760px; margin: 0 auto; padding: 36px 24px 64px; }}
  .masthead {{
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 8px 16px; margin-bottom: 14px; padding-bottom: 10px;
    border-bottom: 1px solid var(--rule);
  }}
  .masthead-brand {{ font-size: 14px; font-weight: 600; color: var(--accent); text-decoration: none; }}
  .masthead-nav {{ display: flex; gap: 14px; margin-right: auto; margin-left: 24px; }}
  .masthead-nav a {{ font-size: 13px; color: var(--fg); text-decoration: none; font-weight: 500; }}
  .masthead-nav a:hover {{ color: var(--accent); }}
  .masthead-meta {{ margin: 0; font-size: 12px; color: var(--muted); }}
  h1 {{ font-size: 30px; margin: 16px 0 8px; letter-spacing: -0.01em; line-height: 1.2; }}
  .lede {{ font-size: 17px; color: var(--muted); margin: 0 0 28px; }}
  h2 {{ font-size: 20px; margin: 36px 0 12px; }}
  p, li {{ font-size: 15px; line-height: 1.65; }}
  a {{ color: var(--accent); }}
  ul.sources-list {{ list-style: none; padding: 0; margin: 12px 0; }}
  ul.sources-list li {{
    border-bottom: 1px solid var(--rule); padding: 12px 0;
  }}
  ul.sources-list li:last-child {{ border-bottom: none; }}
  .source-name {{ font-weight: 600; color: var(--fg); }}
  .source-meta {{ font-size: 13px; color: var(--muted); margin-top: 2px; }}
  .source-meta code {{ background: var(--card); padding: 1px 5px; border-radius: 3px; font-size: 12px; }}
  hr {{ border: none; border-top: 1px solid var(--rule); margin: 36px 0; }}
  footer {{ font-size: 13px; color: var(--muted); margin-top: 48px; }}
</style>
</head>
<body>
<div class="page">

<div class="masthead">
  <a class="masthead-brand" href="/">muslimdata.in</a>
  <nav class="masthead-nav">
    <a href="/">Dashboard</a>
    <a href="/about/">About</a>
    <a href="https://github.com/iqbash1/indian-muslims-dashboard">GitHub</a>
  </nav>
  <p class="masthead-meta">Last updated {timestamp}</p>
</div>

<h1>About muslimdata.in</h1>
<p class="lede">A scorecard of living-conditions indicators for India's Muslim
population, with Hindu and all-India comparison baselines on every metric.</p>

<h2>Why this exists</h2>
<p>The Sachar Committee report (2006) remains India's most-cited assessment of
Muslim socio-economic status. Nearly two decades later, no single public
resource keeps that lens current: the data exists, scattered across the
Census of India, NCRB, NFHS, AISHE, PLFS, and other primary sources, but it
is not assembled in one place, with comparison baselines, in a form that a
non-specialist can read in five minutes.</p>
<p>muslimdata.in is an attempt at that single place. Every number is sourced
from a primary public dataset, traced back to its original file, and shown
alongside the Hindu and all-India comparison so the reader can judge the gap
without having to compute it.</p>

<h2>What's on the dashboard</h2>
<p>{n_metrics} indicators across six themes (population, education,
employment, health, representation, justice), drawn from {n_sources}
primary sources. Every card covers one indicator. It shows the latest
figure for India's Muslims, where that figure ranks across religious
communities, and how it has shifted over time when the source has more
than one survey round.</p>
<p>Click any card to open a larger view with the full methodology notes for
that indicator, including period covered, cut-offs, sample design, and known
caveats. Every card also links to the downloadable CSV of the underlying
data.</p>

<h2>How the data is handled</h2>
<p>Every published value follows the same four-stage pipeline:</p>
<ol>
<li><b>Source.</b> The original file (Census table, NFHS chapter PDF, NCRB
Crime in India volume, AISHE all-India report, PLFS unit-level data,
candidate-affidavit compilations, etc.) is downloaded from the publishing
agency, fingerprinted with a SHA-256 checksum, and archived in this repo's
<code>/sources</code> directory so any reader can reproduce the extract.</li>
<li><b>Extract.</b> A per-source script reads the original file and produces
a cleaned table.</li>
<li><b>Canonicalise.</b> Cleaned tables are reshaped into a long
schema-validated CSV per indicator (one row per geography × religion ×
year), stored in <code>/canonical</code>. These are the files linked from
every card footer.</li>
<li><b>Publish.</b> The dashboard you are reading is generated from those
CSVs, with no live API calls. The build re-runs whenever the canonical
files change, and the deployed site is rebuilt automatically on every push
to the main branch.</li>
</ol>
<p>The point of this discipline is that any number on the page can be
independently verified, end-to-end, by anyone with a browser and a
spreadsheet program.</p>

<h2>Primary sources</h2>
<p>The {n_sources} sources currently feeding the dashboard, with their
publishers and release cadence:</p>
<ul class="sources-list">
{sources_html}
</ul>

<h2>Limitations</h2>
<ul>
<li>The most recent census is 2011. The 2021 round has been indefinitely
delayed, so every Census-derived indicator (population share, sex ratio,
literacy, urban share, district concentration) is dated and will remain so
until the next round is released.</li>
<li>Several Muslim-disadvantage indicators commonly cited in news coverage,
including share of central civil services intake, share of judicial
appointments, and share of corporate-board seats, are not yet on the
dashboard because the data is not publicly released in religion-disaggregated
form. Where civil-society compilations exist, we are evaluating them for
inclusion.</li>
<li>NCRB's "communal incidents" series is a count of police-registered
rioting cases under IPC Sec.147-151. Several states stopped recording
'communal' as a separate sub-category after ~2017, which deflates the
official totals. Civil-society compilations (India Hate Lab,
Documentation of the Oppressed) report substantially higher counts.</li>
<li>For metrics like the MLA share, religion is not officially tabulated
by the Election Commission. Numbers rely on candidate-affidavit
classification by journalists.</li>
</ul>

<h2>Contributing or reporting an error</h2>
<p>The repository is open source on
<a href="https://github.com/iqbash1/indian-muslims-dashboard">GitHub</a>.
Issues and pull requests are welcome:</p>
<ul>
<li>If a number looks wrong, open an issue with the metric, the page URL,
and the number you expected. The pipeline preserves the full source chain
so a correction is traceable to its origin.</li>
<li>If you want a metric added, open an issue with the indicator definition
and the publicly accessible primary source. We prioritise metrics where
religion-disaggregated data is officially released.</li>
<li>If you spot a stale Census date or out-of-date methodology note,
flagging it as an issue is the fastest fix.</li>
</ul>

<hr>

<footer>
<p>muslimdata.in is independent and non-commercial. The project, the
manifest, the canonical CSVs, and this site are all open source under the
MIT licence. Last updated {timestamp}.</p>
</footer>

</div>
</body>
</html>
"""


def _emit_about_page(out_dir: pathlib.Path, timestamp: str) -> None:
    """Render the About page from manifest/sources.yaml plus the static
    template above. Sources are listed in the order they appear in the
    manifest, deduplicated by publisher to avoid listing all 36 Census
    state-MDDS targets as separate sources."""
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "sources.yaml").open() as f:
        sources_data = _yaml.safe_load(f)

    # Collect only sources that actually feed a live metric (i.e. appear in
    # canonical/*.csv) so the about page lists what's truly in use.
    used_source_ids = set()
    for cpath in sorted(CANONICAL_DIR.glob("*.csv")):
        with cpath.open() as f:
            for row in csv.DictReader(f):
                if row.get("source_id"):
                    used_source_ids.add(row["source_id"])

    sources_items = []
    seen = set()
    for s in sources_data.get("sources", []):
        sid = s.get("id", "")
        if sid not in used_source_ids:
            continue
        if sid in seen:
            continue
        seen.add(sid)
        name = s.get("name", sid)
        publisher = s.get("publisher", "")
        home_url = s.get("home_url", "")
        cadence = s.get("cadence", "")
        name_html = (f'<a href="{html.escape(home_url)}">{html.escape(name)}</a>'
                     if home_url else html.escape(name))
        meta_bits = []
        if publisher:
            meta_bits.append(html.escape(publisher))
        if cadence:
            # Cadence comes in as raw strings like "10-year", "annual",
            # "~5-year", "annual + quarterly-urban". Render each naturally.
            c = cadence.lower().strip()
            if c == "annual":
                pretty = "released annually"
            elif c == "decadal":
                pretty = "released every decade"
            elif c.endswith("-year"):
                pretty = f"released every {c[:-len('-year')]} years".replace(" ~ ", " ~")
            else:
                pretty = f"cadence: {cadence}"
            meta_bits.append(html.escape(pretty))
        sources_items.append(
            f'<li><div class="source-name">{name_html}</div>'
            f'<div class="source-meta">{" · ".join(meta_bits)}</div></li>'
        )

    page = ABOUT_TEMPLATE.format(
        site_url=SITE_URL,
        timestamp=timestamp,
        n_metrics=len(SCORECARD_SPEC),
        n_sources=len(seen),
        sources_html="\n".join(sources_items),
    )
    about_dir = out_dir / "about"
    about_dir.mkdir(exist_ok=True)
    (about_dir / "index.html").write_text(page)
    print(f"wrote {(about_dir / 'index.html').relative_to(REPO_ROOT)} ({len(page):,} bytes)")


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

    stats = _compute_headline_stats()
    # Strip the parenthetical qualifier the scorecard labels carry (e.g.
    # "Lok Sabha Muslim share (2024)" → "Lok Sabha Muslim share") and the
    # leading "Muslim " prefix when present (the surrounding sentence is
    # already about Muslims, so "Muslim share of …" repeats it) — but keep
    # the natural casing so proper nouns stay proper.
    import re as _re

    PROPER_NOUNS = {
        "Lok", "Sabha", "MLA", "MLAs", "NCRB", "AISHE", "NFHS", "PLFS",
        "Hindu", "Muslim", "Census", "India", "All-India",
    }

    def _prose_label(n: str) -> str:
        # Strip trailing scorecard qualifier like " (2024)" or " (all states)".
        n = _re.sub(r"\s*\([^)]*\)\s*$", "", n)
        # Lowercase every word that isn't a known proper noun, so "Infant
        # Mortality Rate" → "infant mortality rate" but "Lok Sabha Muslim
        # share" keeps its capitals.
        return " ".join(w if w in PROPER_NOUNS else w.lower() for w in n.split())

    top_behind_joined = _and_join([_prose_label(n) for n in stats["top_behind_names"]])
    top_ahead_joined = _and_join([_prose_label(n) for n in stats["top_ahead_names"]])
    ahead_clause = (
        f" They run ahead on a handful (<em>{top_ahead_joined}</em>)."
        if stats["n_ahead"] > 0 else ""
    )

    substitutions = {
        "{timestamp}": dt.datetime.now().strftime("%-d %B %Y"),
        "{n_metrics}": str(n_metrics),
        "{n_sources}": str(n_sources),
        "{n_rows}": str(n_rows),
        "{n_behind}": str(stats["n_behind"]),
        "{n_total_comparable}": str(stats["n_total_comparable"]),
        "{top_behind_joined}": top_behind_joined,
        "{ahead_clause}": ahead_clause,
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

    # Emit per-metric 1200x630 OG cards at /og/{mid}.png (referenced by the
    # stub pages below) and a /og/default.png used by the homepage + About.
    _emit_og_images(OUT_PATH.parent)

    # Emit per-metric stub pages at /m/{mid}/index.html. Each carries the
    # metric-specific OG meta tags so social previews show the right
    # title/description when a user shares the link; the body then
    # client-redirects to the main page's hash for the modal to auto-open.
    _emit_metric_stubs(OUT_PATH.parent)

    # Emit the About page at /about/index.html.
    _emit_about_page(OUT_PATH.parent, substitutions["{timestamp}"])

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


def _comparison_series(series: dict, years: list[int]):
    """Return (values, label, pill_label) for the dashed comparison line.

    Prefers the source-published "all" aggregate when it's populated across
    every year in the trend; otherwise falls back to the per-year median of
    available community values so the Muslim line always has a benchmark.
    Labels are honest about which calculation was used so the chart legend
    and the comp pill don't claim "All-India" when the line is actually a
    community median."""
    import statistics as _stats
    source_all = [series.get("all", {}).get(y) for y in years]
    if source_all and all(v is not None for v in source_all):
        return source_all, "All-India", "vs all-India"
    community_keys = [c for c in NAMED_COMMUNITIES if c in series]
    if not community_keys:
        return None, None, None
    values = []
    for y in years:
        vals = [series[c].get(y) for c in community_keys if series[c].get(y) is not None]
        values.append(_stats.median(vals) if vals else None)
    if not any(v is not None for v in values):
        return None, None, None
    return values, "All religions (median)", "vs all religions (median)"
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
    "ger-higher-ed": "of 18-23-year-olds",
    "sex-ratio": "females per 1,000 males",
    "lfpr-15plus": "in the labour force, 15+",
    "wpr-15plus": "working, 15+",
    "salaried-share": "in regular salaried work",
    "imr": "deaths per 1,000 live births",
    "inst-delivery": "of births in a facility",
    "women-anemia": "of women 15-49 anaemic",
    "improved-sanitation": "of households",
    "pop-share": "of all Indians",
    "district-concentration-top100": "of all Indian Muslims",
    "muslim-higher-ed-enrolment": "students",
    "ls-share": "of 543 Lok Sabha seats",
    "mla-share": "of state-assembly seats (agg.)",
    "prison-rate-per-100k": "prisoners per 100k of community",
    "undertrial-rate-per-100k": "undertrials per 100k of community",
    "communal-incidents-govt": "incidents",
    "communal-incidents-civic": "events",
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


def _comp(label: str, verdict: str, detail: str, cls: str, comp_type: str | None = None) -> str:
    attr = f' data-comp-type="{comp_type}"' if comp_type else ""
    return (f'<div class="card-comp {cls}"{attr}><div class="comp-label">{html.escape(label)}</div>'
            f'<div class="comp-verdict">{html.escape(verdict)}</div>'
            f'<div class="comp-detail">{html.escape(detail)}</div></div>')


PLAIN_DEFINITION = {
    "pop-share": "How much of India's population is Muslim, by the latest census.",
    "urban-share": "What share of each community lives in towns and cities rather than villages.",
    "sex-ratio": "Higher means more women relative to men; a low value signals a gender imbalance favouring males.",
    "district-concentration-top100": "How geographically concentrated India's Muslims are, measured by the share living in their 100 most-populous districts.",
    "lit-7plus": "Of people aged 7 and older, what share can read and write. The Census uses 7+ as the standard cutoff to exclude very young children.",
    "ger-higher-ed": "Of every 100 young people in the typical college-going age band (18 to 23), how many are enrolled in higher education.",
    "muslim-higher-ed-enrolment": "Total number of Muslim students enrolled in higher education across India in the latest year.",
    "lfpr-15plus": "Of people aged 15 and older, what share is in the workforce, either working or actively looking for work.",
    "wpr-15plus": "Of people aged 15 and older, what share is currently working.",
    "salaried-share": "Of all workers, what share has regular salaried jobs (as opposed to self-employment or casual labour).",
    "imr": "Of every 1,000 babies born, how many die before their first birthday.",
    "stunting-u5": "Of children under 5, what share is too short for their age, a long-term sign of chronic undernutrition.",
    "inst-delivery": "Of recent live births, what share took place at a hospital or health facility rather than at home.",
    "women-anemia": "Of women in childbearing age (15 to 49), what share has anaemia (low haemoglobin).",
    "improved-sanitation": "What share of households has a toilet of any type.",
    "ls-share": "Of the 543 seats in India's national parliament (Lok Sabha), what share is held by Muslim MPs.",
    "mla-share": "Across all 30 state and UT legislative assemblies that hold elections, what share of MLA seats is held by Muslims.",
    "prison-rate-per-100k": "For every 100,000 people of a religion, how many are in prison. Allows fair comparison across communities of different size.",
    "undertrial-rate-per-100k": "For every 100,000 people of a religion, how many are in prison awaiting trial (not yet convicted).",
    "communal-incidents-govt": "Number of communal or religious rioting incidents recorded in police records each year (NCRB).",
    "communal-incidents-civic": "In-person events (rallies, religious gatherings, political speeches) where Muslims are targeted with hateful rhetoric.",
}


def _card_shell(mid, label, value, unit_txt, year, polarity, chart_html, comps_html,
                src, csv_href, details_html="") -> str:
    # `polarity` carries the "higher is better"/"lower is better" hint when the
    # metric direction is unambiguous (e.g. literacy higher is good, IMR lower
    # is good). Rendered as a small caption under the hero so a reader can tell
    # at a glance whether the gap colour they're looking at is good or bad news.
    polarity_html = ""
    if polarity == "higher is better":
        polarity_html = '<p class="card-polarity"><span aria-hidden="true">↑</span> higher is better</p>'
    elif polarity == "lower is better":
        polarity_html = '<p class="card-polarity polarity-down"><span aria-hidden="true">↓</span> lower is better</p>'
    yr = f'<span class="card-year">({html.escape(str(year))})</span>' if year else ""
    plain = PLAIN_DEFINITION.get(mid, "")
    plain_html = f'<p class="card-plain">{html.escape(plain)}</p>' if plain else ""
    expand_html = '<span class="card-expand" aria-hidden="true" title="Click for larger view">↗</span>'

    # "About this measurement" block: visible only when the card is cloned
    # into the modal (display:none on the card grid via CSS). Pulls the
    # technical definition and methodology notes from manifest/metrics.yaml
    # so the modal has the full provenance + caveats without crowding the
    # card.
    meta = METRIC_META.get(mid, {})
    method_html = ""
    def_text = (meta.get("definition") or "").strip()
    notes_text = (meta.get("methodology_notes") or "").strip()
    if def_text or notes_text:
        parts = []
        if def_text:
            parts.append(f'<p><b>Definition.</b> {html.escape(def_text)}</p>')
        if notes_text:
            parts.append(f'<p><b>Methodology.</b> {html.escape(notes_text)}</p>')
        method_html = (
            '<div class="card-method">'
            '<h3 class="card-method-title">About this measurement</h3>'
            + "".join(parts) +
            '</div>'
        )
    return (
        f'<section class="card" data-metric-id="{html.escape(mid)}" data-metric-name="{html.escape(label)}">'
        f'{expand_html}'
        f'<div class="card-metric">{html.escape(label)}</div>'
        f'{plain_html}'
        f'<div class="card-hero"><span class="card-value">{value}</span>'
        f'<span class="card-unit">{html.escape(unit_txt)}</span>{yr}</div>'
        f'{polarity_html}{chart_html}'
        f'<div class="card-comparisons">{comps_html}</div>'
        f'{method_html}'
        f'{details_html}'
        # The source NAME is the hyperlink (target = the canonical CSV); the raw
        # path is not shown. Built directly here — no post-processing linkifier.
        f'<div class="card-foot">'
        f'<a href="{html.escape(csv_href)}">{html.escape(src)}</a>'
        f'</div>'
        '</section>'
    )


def _parse_district_rows(metric_id: str):
    """Parse per-district rows for the concentration metric into tuples
    (rank, name, state_abbrev, muslim_count, pct_of_district), rank-sorted.
    The canonicalizer stamps `rank=N; name=...; muslim_pct_of_district=...`
    into each row's methodology_note."""
    out = []
    for r in load_metric(metric_id):
        if r["geography_level"] != "district":
            continue
        meta = {}
        for part in (r.get("methodology_note") or "").split(";"):
            if "=" in part:
                k, _, v = part.partition("=")
                meta[k.strip()] = v.strip()
        try:
            rank = int(meta.get("rank", "0") or 0)
        except ValueError:
            rank = 0
        try:
            pct = float(meta.get("muslim_pct_of_district", "0"))
        except ValueError:
            pct = 0.0
        out.append((rank, meta.get("name", ""), state_abbrev(r["geography_code"]),
                    int(float(r["value"])), pct))
    out.sort(key=lambda x: x[0])
    return out


def _national_muslim_total(metric_id: str) -> int:
    """National Muslim total for the concentration metric, from its national
    row. The denominator field carries 'national_muslim_pop_<N>'; sample_size
    holds the same number as a fallback."""
    import re as _re
    for r in load_metric(metric_id):
        if r["geography_level"] == "national":
            m = _re.search(r"national_muslim_pop_(\d+)", r.get("denominator") or "")
            if m:
                return int(m.group(1))
            if r.get("sample_size"):
                try:
                    return int(float(r["sample_size"]))
                except ValueError:
                    pass
    return 0


def _district_cumulative(metric_id: str):
    """Return (points, top10_share) where points is [[rank, cumulative_pct], …]
    for rank 1..N — the cumulative share of the *national* Muslim population
    held by the top-rank districts. Feeds the concentration curve + the kicker."""
    parsed = _parse_district_rows(metric_id)
    nat_total = _national_muslim_total(metric_id) or 1
    points, cum, top10 = [], 0, 0.0
    for rank, _name, _st, mcount, _pct in parsed:
        cum += mcount
        share = cum / nat_total * 100
        points.append([rank, round(share, 2)])
        if rank == 10:
            top10 = share
    return points, top10


def _top100_districts_table(metric_id: str) -> str:
    """Sortable, scrollable # | District (ST) | Muslims | % of district table.
    Built from _parse_district_rows. Each numeric cell carries a `data-sort`
    raw value so the client sort is correct (text like "4.71M" / "501k" would
    sort wrong by string); headers are click-sortable (see setupSortableTables
    JS). Default order = rank ascending."""
    parsed = _parse_district_rows(metric_id)
    if not parsed:
        return ""
    trs = []
    for rank, name, st, muslim, pct in parsed:
        # Compact Muslim population ("4.71M" / "502k"); data-sort keeps the raw
        # count so descending sort puts the most-populous district first.
        mil = muslim / 1_000_000
        mil_str = f"{mil:.2f}M" if mil >= 1 else f"{mil*1000:.0f}k"
        trs.append(
            f"<tr>"
            f'<td style="text-align:right" data-sort="{rank}">{rank}</td>'
            f"<td>{html.escape(name)} <span style=\"color:var(--muted);font-size:11px\">({html.escape(st)})</span></td>"
            f'<td style="text-align:right;font-feature-settings:&quot;tnum&quot;" data-sort="{muslim}">{mil_str}</td>'
            f'<td style="text-align:right;font-feature-settings:&quot;tnum&quot;" data-sort="{pct:.4f}">{pct:.1f}%</td>'
            f"</tr>"
        )
    return (
        f'<details><summary>See the full ranked list (top {len(parsed)} districts)</summary>'
        f'<div class="scroll-table">'
        f'<table class="sortable-table">'
        f'<thead><tr>'
        f'<th class="sortable" data-col="0" data-type="num" style="text-align:right">#</th>'
        f'<th class="sortable" data-col="1">District (ST)</th>'
        f'<th class="sortable" data-col="2" data-type="num" style="text-align:right">Muslims</th>'
        f'<th class="sortable" data-col="3" data-type="num" style="text-align:right">% of district</th>'
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

    years, series, has_break = _nat_trend(mid)
    # Compute the chart's comparison line once and reuse its latest-year
    # value for the comparison pill so the pill number matches the dashed
    # line on the chart. When source "all" is sparse, both fall back to
    # the per-year median across communities (and the pill label changes
    # to "vs community median" to stay honest about what's being compared).
    if years:
        all_series, all_line_label, all_pill_label = _comparison_series(series, years)
    else:
        all_series, all_line_label, all_pill_label = None, None, "vs all-India"
    if all_series:
        latest = next((v for v in reversed(all_series) if v is not None), None)
        if latest is not None:
            all_v = latest

    # Comparison block: default to "vs all-India" (or "vs community median"
    # when source all-India is sparse). Render "vs Hindu" alongside (marked
    # data-comp-type="vs-hindu") so a page-level toggle can swap the visible
    # pill when a viewer wants the inter-community read. The comparator's
    # actual value is appended to the pill label so the reader doesn't have
    # to do mental math between the card hero (Muslim) and the gap (verdict).
    comps = ""
    if all_v is not None and muslim is not None:
        gap = muslim - all_v
        cls = _verdict(gap, hib)
        base_label = all_pill_label or "vs all-India"
        comps += _comp(f"{base_label} · {fmt_num(all_v, unit)}",
                       _gap_str(gap, unit), _verdict_word(cls), cls,
                       comp_type="vs-all")
    if hindu is not None:
        gap = muslim - hindu
        cls = _verdict(gap, hib)
        comps += _comp(f"vs Hindu · {fmt_num(hindu, unit)}",
                       _gap_str(gap, unit), _verdict_word(cls), cls,
                       comp_type="vs-hindu")
    if rank:
        comps += _comp("among communities", f"{_ordinal(rank)} of {n}", _tier_word(tier), tier)
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
        # all_series was computed at the top of the function so the comp pill
        # and the chart's dashed line share the same comparator (source "all"
        # when populated; median across communities otherwise). Pass it as an
        # object so the chart's end-of-line label matches the pill label.
        chart_html = f'<div class="card-chartwrap" style="height:200px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
        all_arg = {"values": all_series, "label": all_line_label} if all_series else None
        js = (f'trendChart("{cvid}", {json.dumps(years)}, {json.dumps(series_map)}, '
              f'{json.dumps(all_arg)}, {json.dumps(suffix)}, {json.dumps(bool(has_break))});')
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
            chart_html = f'<div class="card-chartwrap" style="height:{h}px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
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
    kicker_html = ""
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
        chart_html = f'<div class="card-chartwrap" style="height:200px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
        # No All-India series (shares already sum to ~100%); no refLine.
        js = (f'trendChart("{cvid}", {json.dumps(years)}, {json.dumps(series_map)}, '
              f'null, "%", false);')
        note = (f"Share of each community in India's population by census. Hindu's share "
                f"drifted from {hindu_first:.1f}% in 1961 to {hindu_last:.1f}% in 2011, "
                f"omitted from the chart so the Muslim and minor-community trends are legible. "
                f"All values from primary RGI religion volumes 1961-2011; 1981 excludes "
                f"Assam, 1991 excludes Jammu & Kashmir.")
    elif mid == "district-concentration-top100":
        # Cumulative concentration curve: cumulative share of India's Muslim
        # population (y) as you add districts ranked by Muslim population (x).
        # The steep-then-flat shape shows how front-loaded the concentration
        # is; the top-10 point is highlighted to anchor the kicker line. The
        # full ranked list is in the sortable table below — see
        # _top100_districts_table().
        points, top10 = _district_cumulative(mid)
        chart_html = f'<div class="card-chartwrap" style="height:150px"><canvas id="{cvid}" role="img" aria-label="Cumulative share of India\'s Muslim population held by the top-ranked districts; values listed in the table below."></canvas></div>'
        js = f'concentrationCurve("{cvid}", {json.dumps(points)}, 10, "%");'
        kicker_html = (f'<div class="comp-kicker">The top 10 districts alone are home to '
                       f'{top10:.0f}% of all Indian Muslims.</div>')
        note = (f"India had {TOTAL_DISTRICTS_2011} districts in 2011, yet the 100 most "
                f"Muslim-populous, just {100 / TOTAL_DISTRICTS_2011 * 100:.0f}% of them, are "
                f"home to {muslim:.1f}% of all Indian Muslims. This is a geographic-"
                f"concentration measure, not a community comparison.")
    else:  # muslim-higher-ed-enrolment
        # Top-8 states by Muslim enrolment, shown in thousands (the national
        # headline is the absolute total; no community comparator exists).
        st = [(state_label(r["geography_code"]), float(r["value"]))
              for r in load_metric(mid) if r["geography_level"] == "state"]
        st.sort(key=lambda x: -x[1])
        st = st[:8]
        if st:
            chart_html = f'<div class="card-chartwrap" style="height:{len(st) * 26 + 20}px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
            labels = [s[0] for s in st]
            vals = [round(s[1] / 1000) for s in st]
            js = (f'hbar("{cvid}", {json.dumps(labels)}, {json.dumps(vals)}, '
                  f'{json.dumps(["#2b6cb0"] * len(st))}, "k", 0, null, "");')
        note = ("No community ranking. AISHE tabulates “Muslim Minority” enrolment separately; "
                "other communities are not enumerated in the same table. Top-8 states shown (thousands).")
    comps = kicker_html + f'<div class="comp-note">{html.escape(note)}</div>'
    # Metric-specific drill-down (collapsed by default). For district-concentration
    # we surface the full top-100 list; for others, state-level data if available.
    if mid == "district-concentration-top100":
        details = _top100_districts_table(mid)
    else:
        details = _state_details(mid, unit)
    return _card_shell(mid, label, headline, CAPTION.get(mid, ""), _year_of(mid), "",
                       chart_html, comps, src, csv_href, details), js


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
        chart_html = f'<div class="card-chartwrap" style="height:150px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
        js = f'lineChart("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, "#2b6cb0", "%");'
        comps += _comp("trend", f"{labels[0]}-{labels[-1]}", f"{values[0]:.1f}% → {values[-1]:.1f}%", "neutral")
    else:
        st = sorted([(state_label(r["geography_code"]), float(r["value"]))
                     for r in load_metric(mid) if r["geography_level"] == "state"],
                    key=lambda x: -x[1])
        if st:
            inner_h = len(st) * 26 + 20
            max_h = 240
            inner = (f'<div class="card-chartwrap" style="height:{inner_h}px">'
                     f'<canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>')
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
        chart_html = f'<div class="card-chartwrap" style="height:150px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
        js = f'lineChart("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, "#7b1d22", "");'
        comps += _comp("trend", f"{labels[0]}-{labels[-1]}", f"{values[0]:,} → {val:,}", "neutral")
    elif len(rows) == 2:
        # Only two rounds: a 2-point line is just a sloped segment, so show the
        # two years as side-by-side bars instead, so the year-on-year jump
        # reads at a glance. Zero-based (beginAtZero=True) so bars are honest:
        # 668 vs 1,165 must look like "nearly double", not "triple". The later
        # bar is coloured by direction (red if it rose, since lower is better).
        first, last = int(float(rows[0]["value"])), val
        delta = last - first
        pct = (delta / first * 100) if first else 0
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        cls = "bad" if delta > 0 else ("good" if delta < 0 else "mid")
        y0, y1 = str(rows[0]["year"]), str(latest["year"])
        bar_hex = "#991B1B" if delta > 0 else ("#065F46" if delta < 0 else "#555555")
        chart_html = (f'<div class="card-chartwrap" style="height:104px"><canvas id="{cvid}" '
                      f'role="img" aria-label="Bar comparison of {y0} versus {y1}; values listed in the card above."></canvas></div>')
        js = (f'hbar("{cvid}", {json.dumps([y0, y1])}, {json.dumps([first, last])}, '
              f'{json.dumps(["#C9CFD3", bar_hex])}, "", 0, null, "", true);')
        noun = CAPTION.get(mid, "events")
        comps += _comp(f"vs {y0}", f"{arrow} {abs(pct):.0f}%", f"{delta:+,} {noun}", cls)
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
        intro = SECTION_INTROS.get(name, "")
        intro_html = (f'<p class="cluster-intro">{html.escape(intro)}</p>\n'
                      if intro else "")
        grids.append(f'<h2 class="cluster-header">{html.escape(name)}</h2>\n'
                     f'{intro_html}'
                     f'<div class="cards">\n{"".join(cards)}\n</div>')
    return "\n\n".join(grids), "\n".join(charts)


if __name__ == "__main__":
    build()
