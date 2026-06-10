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
import re

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


def load_metric(name: str, *, sex: str | None = "all") -> list[dict]:
    """Canonical rows for a metric. By DEFAULT returns only the both-sexes
    aggregate (sex='all'); rows with a missing/empty sex column are treated as
    'all' (back-compat). Pass sex=None for every row (incl. male/female), or
    sex='male'/'female' to select one. This single choke point keeps every
    existing consumer aggregate-only when gender rows are added to a metric."""
    rows: list[dict] = []
    p = CANONICAL_DIR / f"{name}.csv"
    if not p.exists():
        return rows
    with p.open() as f:
        for row in csv.DictReader(f):
            if not row.get("sex"):
                row["sex"] = "all"
            rows.append(row)
    if sex is None:
        return rows
    return [r for r in rows if r["sex"] == sex]


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


# Display precision per unit. ONE decimal place for the decimal-bearing units
# (percent, rates, years); whole numbers for counts/currency/sex-ratio. Values
# are ROUNDED to nearest (half up) to this precision, so the display matches the
# published source figures (e.g. NFHS institutional delivery 88.6%). Full
# precision is preserved in the canonical CSVs and the data-sort attributes; only
# the visible number is rounded.
_DISP_DP = {
    "percent": 1, "per_1000_live_births": 1, "rate_per_100k": 1,
    "per_100k_population": 1, "years": 1, "females_per_1000_males": 0,
    "count": 0, "inr_per_month": 0, "inr_per_year": 0, "inr": 0,
}


def _disp_dp(unit: str) -> int:
    return _DISP_DP.get(unit, 1)


def _round_dp(v: float, dp: int = 1) -> float:
    """Round half-up to `dp` decimals. Pre-snaps to 9dp first so IEEE noise from
    subtraction (55.0 - 60.9 = -5.89999...) can't flip a half-boundary; genuine
    data is <=4dp so the 9dp snap is lossless."""
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(round(float(v), 9)))
    return float(d.quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP))


def _round_str(v: float, dp: int = 1) -> str:
    """Fixed-width rounded string: _round_str(55.0)->'55.0', _round_str(88.58)->'88.6'."""
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(round(float(v), 9)))
    return str(d.quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP))


def fmt_num(v: float, unit: str) -> str:
    if unit == "percent":
        return f"{_round_str(v, 1)}%"
    if unit == "females_per_1000_males":
        return _round_str(v, 0)
    if unit in ("per_1000_live_births", "rate_per_100k", "per_100k_population", "years"):
        return _round_str(v, 1)
    if unit == "count":
        return f"{int(v):,}"
    if unit in ("inr_per_month", "inr_per_year", "inr"):
        return f"Rs {int(v):,}"
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
#
# Sequence rationale (deliberate -- keep it): context -> foundational wellbeing
# -> life chances -> civic standing, building to the most acute content.
#   - Demographics (who & where) opens as neutral scene-setting.
#   - Health & Housing (survival & living conditions) leads the outcomes as the
#     most foundational human needs.
#   - Education, work & income (income now carries the live MPCE metric; the
#     Finance cluster is still stub) follows as life chances.
#   - The civic block closes: Representation (voice) then Justice & Civic, which
#     ends on the sharpest material (over-incarceration, communal violence).
#   Don't lead with a gap section or with Justice (that editorialises the order);
#   keep Justice & Civic last. The per-metric `order` in metrics.yaml is numbered
#   to match this render order so the two never drift apart.
SECTION_GROUPS = [
    ("Demographics", ["demographics"]),
    ("Health & Housing", ["health", "housing"]),
    ("Education, work & income", ["education", "employment", "income"]),
    ("Finance", ["finance"]),
    ("Representation", ["representation"]),
    ("Justice & Civic", ["justice", "civic"]),
]
SECTION_OF = {cid: name for name, cids in SECTION_GROUPS for cid in cids}

# One-line intro shown under each section header, telling a new visitor what
# story to expect in the cards below. Written by hand against current data;
# update when the data changes the direction. Indian-English spelling.
SECTION_INTROS = {
    "Demographics": "India's largest religious minority, more urban than the national average and concentrated in a handful of districts in the north and east.",
    "Education, work & income": "Behind on literacy, higher-education enrolment, salaried work and monthly spending; near the national average on workforce participation.",
    "Health & Housing": "Lower infant mortality and the lowest anaemia of any community, but the highest under-5 stunting; toilet access now close to par.",
    "Representation": "Far fewer elected seats than their share of the population, both in the Lok Sabha and across the state assemblies.",
    "Justice & Civic": "Over-represented in the prison and undertrial populations per head of community, alongside police-recorded communal incidents.",
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
                f'<td>{_round_str(m_val, 1)}%</td>'
                f'<td>n/a</td>'
                f'<td>n/a</td>'
                f'<td class="{"gap-bad" if gap < 0 else "gap-good"}">{sign}{_round_str(gap, 1)}pp vs {_round_str(MUSLIM_POP_SHARE, 1)}% pop</td>'
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
                gap_str = f"{sign}{_round_str(diff, _disp_dp(unit))}"
                if unit == "percent":
                    gap_str += "pp vs " + ("Hindu" if ref == "hindu" else "all communities")
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
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#fafaf7">
<meta property="og:title" content="{site_title}">
<meta property="og:description" content="{site_description}">
<meta property="og:url" content="{site_url}/">
<meta property="og:type" content="website">
<meta property="og:image" content="{site_url}/og/default.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="muslimdata.in: the state of Muslim India, in data. {n_metrics} indicators with Hindu and all-India comparison baselines.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{site_title}">
<meta name="twitter:description" content="{site_description}">
<meta name="twitter:image" content="{site_url}/og/default.png">
{home_jsonld}
<script src="/js/chart.umd.min.js" integrity="sha384-e6nUZLBkQ86NJ6TVVKAeSaK8jWa3NhkYWZFomE39AvDbQWeie9PlQqM3pmYW5d1g"></script>
<script src="js/analytics.js" defer></script>
<style>
  :root {
    --fg: #1a1a1a;
    --muted: #555;
    --bg: #fafaf7;
    --card: #ffffff;
    --rule: #e6e3da;
    --muslim: #7b1d22;  /* Muslim data series + the headline Muslim figure */
    --hindu:  #b76a2b;
    --all:    #5a6a5d;
    --accent: #2c5f8a;  /* UI accent: links, emphasis, hover, active, focus */
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
  .masthead-brand { font-size: 14px; font-weight: 600; color: var(--fg); text-decoration: none; letter-spacing: -0.01em; }
  .masthead-brand:hover { color: var(--accent); }
  .masthead-brand:hover { text-decoration: underline; }
  .masthead-nav { display: flex; gap: 14px; margin-right: auto; margin-left: 24px; }
  .masthead-nav a { font-size: 13px; color: var(--fg); text-decoration: none; font-weight: 500; }
  .masthead-nav a:hover { color: var(--accent); }
  .masthead-meta { margin: 0; font-size: 12px; color: var(--muted); }
  .masthead-meta a { color: var(--muted); }
  .headline-finding { font-size: 16px; line-height: 1.55; color: var(--fg); margin: 0 0 24px; max-width: 70em; }
  .headline-finding em { font-style: normal; color: var(--accent); font-weight: 600; }
  .preamble-note { font-size: 14px; line-height: 1.5; color: var(--muted); margin: 0 0 22px; max-width: 64em; }
  .preamble-note b { color: var(--fg); font-weight: 600; }
  .preamble-note a { color: var(--accent); text-decoration: none; font-weight: 500; white-space: nowrap; }
  .preamble-note a:hover { text-decoration: underline; }
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
  /* A metric with no Hindu figure (e.g. AISHE higher-ed GER) would otherwise go
     blank in "Hindu only" mode; keep its all-India gap visible as a fallback. */
  body.compare-hindu .card-comp[data-comp-type="vs-all"][data-comp-fallback] { display: block; }
  h2 { font-size: 20px; margin: 0 0 4px; letter-spacing: -0.01em; font-weight: 600; }
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
  .scorecard-table .gap-bad { color: var(--negative); font-weight: 600; }
  .scorecard-table .gap-good { color: var(--positive); font-weight: 600; }
  .scorecard-table .gap-neutral { color: var(--muted); }
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
    --t-2xs: .75rem; --t-xs: .75rem; --t-sm: .82rem; --t-base: .88rem;
  }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); align-items: start; gap: 16px; margin-bottom: 8px; }
  .card {
    background: var(--card); border: 1px solid var(--rule); border-radius: var(--radius);
    padding: 18px 18px 14px; display: flex; flex-direction: column;
    transition: border-color .15s, box-shadow .15s, transform .15s;
  }
  .card:hover { border-color: var(--accent); box-shadow: var(--shadow-card); transform: translateY(-2px); }
  .card:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
  .card-metric { font-size: 15px; font-weight: 600; color: var(--fg); margin-bottom: 4px; line-height: 1.3; }
  .card-plain { font-size: 14px; color: var(--muted); margin: 0 0 10px; line-height: 1.45; font-weight: 400; }
  .modal-body .card-plain { font-size: 14px; color: var(--fg); margin: 0 0 16px; line-height: 1.55; max-width: 56em; }
  .card-hero { display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }
  .card-value { font-size: 1.7rem; font-weight: 700; letter-spacing: -.02em; color: var(--muslim); font-feature-settings: "tnum"; }
  .card-unit, .card-year { font-size: var(--t-sm); color: var(--muted); font-weight: 500; }
  .card-polarity {
    font-size: 11px; color: var(--muted); margin: -2px 0 8px;
    font-weight: 500; letter-spacing: 0.01em; text-transform: uppercase;
  }
  .card-polarity span { color: var(--positive); margin-right: 2px; font-weight: 600; }
  .card-polarity.polarity-down span { color: var(--positive); }
  .card-expand {
    position: absolute; top: 12px; right: 14px;
    font-size: 15px; color: var(--muted); pointer-events: none;
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
    max-width: 56em; white-space: normal;
  }
  .modal-body .card-method b { color: var(--accent); font-weight: 600; }
  .view-provenance, .card-reproduce { font-size: 12px; color: var(--muted); line-height: 1.5; margin: 10px 0 0; }
  .view-provenance b, .card-reproduce b { color: var(--fg); font-weight: 600; }
  .view-provenance a, .card-reproduce a { color: var(--accent); text-decoration: none; }
  .view-provenance a:hover, .card-reproduce a:hover { text-decoration: underline; }
  .card-chartwrap { width: 100%; margin: 2px 0 4px; position: relative; }
  .card-chartscroll { width: 100%; margin: 2px 0 4px; overflow-y: auto; overflow-x: hidden; border: 1px solid var(--rule); border-radius: 4px; }
  .card-chartscroll .card-chartwrap { margin: 0; }
  .card-comparisons { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: auto; padding-top: 10px; border-top: 1px solid var(--rule); }
  .card-comp { text-align: center; padding: 5px 4px; border-radius: 6px; }
  .comp-label { font-size: var(--t-xs); color: var(--muted); font-weight: 500; margin-bottom: 2px; }
  .comp-verdict { font-size: var(--t-base); font-weight: 700; font-feature-settings: "tnum"; }
  .comp-detail { font-size: var(--t-2xs); color: var(--muted); margin-top: 1px; }
  .card-comp.good .comp-verdict { color: var(--positive); }
  .card-comp.bad .comp-verdict { color: var(--negative); }
  .card-comp.neutral .comp-verdict, .card-comp.mid .comp-verdict { color: var(--neutral); }
  .comp-note { grid-column: 1 / -1; text-align: left; font-size: var(--t-xs); color: var(--muted); line-height: 1.45; }
  /* Kicker line above the note (e.g. "the top 10 districts alone hold 14%"):
     full width, accent-coloured, the card's punchiest single takeaway. */
  .comp-kicker { grid-column: 1 / -1; text-align: left; font-size: var(--t-sm); color: var(--accent); font-weight: 600; line-height: 1.4; margin-bottom: 4px; }
  .card-foot { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--rule); display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: var(--t-2xs); color: var(--muted); }
  .card-foot a { color: var(--accent); text-decoration: none; font-weight: 500; }
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
  /* Phablet / small-tablet band: between the single-column mobile layout and
     the width where the auto-fill grid naturally fits two 330px columns, the
     grid would otherwise show one over-wide stretched column. Force two. */
  @media (min-width: 561px) and (max-width: 767px) {
    .cards { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 560px) {
    .cards { grid-template-columns: 1fr; }
    h1 { font-size: 24px; }
    .headline-finding { font-size: 16px; }
    .masthead { gap: 6px 12px; }
    .masthead-nav { margin-left: 0; gap: 10px; }
    .masthead-nav a { padding: 12px 4px; min-height: 44px; display: inline-flex; align-items: center; }
    .compare-toggle { flex-wrap: wrap; padding: 8px 12px; }
    .compare-toggle-label { width: 100%; margin-bottom: 4px; }
    .compare-toggle-btn { padding: 0 16px; font-size: 13px; min-height: 44px; }
    .scorecard-search { padding: 0 14px; font-size: 14px; min-height: 44px; }
    .scorecard-table { font-size: 13px; }
    .scorecard-table th, .scorecard-table td { padding: 6px 4px; }
    /* Section intros: keep at the desktop size on mobile for 60+ legibility. */
    .cluster-intro { font-size: 14px; }
    /* Pill labels carry the comparator value now (Commit BP). On narrow
       cards the 3-pill row gets tight, so tighten typography and pad. */
    .comp-label { font-size: 12px; line-height: 1.2; }
    .comp-verdict { font-size: 12.5px; }
    .comp-detail { font-size: 12px; }
    .card-comp { padding: 4px 3px; }
    /* Modal actions: 4 buttons (prev, next, share, close) need to fit at
       375px. Hide text labels on the prev/next/share buttons, leaving
       chevrons + share-icon as compact controls. */
    .modal-share-label { display: none; }
    .modal-share { padding: 0; gap: 0; min-width: 44px; }
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
    position: absolute; top: 12px; right: 12px; z-index: 2;
    display: flex; gap: 6px; align-items: center;
  }
  .modal-close, .modal-share {
    border-radius: 6px; cursor: pointer; padding: 0;
    -webkit-appearance: none; appearance: none;
    line-height: 1; white-space: nowrap;
    transition: background .15s, border-color .15s, color .15s;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .modal-close {
    width: 44px; height: 44px; font-size: 22px;
    background: var(--card); border: 1px solid var(--rule); color: var(--muted);
  }
  .modal-close:hover { background: var(--bg); border-color: var(--accent); color: var(--accent); }
  /* Share = a solid slate-blue primary button (Hawaii-dashboard style), white
     icon + label. It is UI chrome, so accent, never maroon. */
  .modal-share {
    height: 44px; padding: 0 16px; gap: 7px; font-size: 13px; font-weight: 600;
    background: var(--accent); border: 1px solid var(--accent); color: #fff;
  }
  .modal-share svg { stroke: #fff; }
  .modal-share:hover { background: #234c70; border-color: #234c70; }
  /* Inside the modal body, the cloned card sheds its card styling and the
     chart wrapper expands to use the larger real estate. */
  .modal-body .card {
    padding: 0; border: none; box-shadow: none; cursor: default; position: static;
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
    /* Tabs scroll horizontally instead of wrapping, and shed their sub-labels,
       so a 3-tab bar stays one tidy row on a phone (Hawaii-dashboard pattern). */
    .modal-tabs { flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none; }
    .modal-tabs::-webkit-scrollbar { display: none; }
    .modal-tab { padding: 8px 12px; white-space: nowrap; flex-shrink: 0; min-height: 44px; }
    .modal-tab .tab-sub { display: none; }
  }
  @media (max-width: 767px) {
    /* Reserve room at the top of the modal for the absolutely-positioned
       action bar (prev/next/share/close), so a long metric title never runs
       underneath the buttons on a narrow screen. */
    .modal { padding-top: 60px; }
  }

  /* --- Metric "views" as modal tabs (Hawaii-dashboard pattern) ---
     A metric's drill-downs (by state, by sex, by district) live in the card
     DOM but are HIDDEN on the card face; the modal lifts each into its own
     tab so the homepage stays uncluttered. Tabs are UI chrome, so the active
     tab uses the slate-blue accent, never maroon. */
  .card-views { display: none; }                 /* card face: drill-downs hidden; modal JS lifts them into tabs */
  .card-download { display: none; }               /* district-CSV CTA: modal-only (mirror of .card-method) */
  .modal-body .card-download { display: block; margin: 12px 0 0; font-size: 13px; color: var(--muted); }
  .modal-body .card-download a { color: var(--accent); font-weight: 500; }
  /* Minimal card-face cue that more views wait in the detail modal. */
  .card-views-hint {
    margin: 12px 0 0; padding-top: 9px; border-top: 1px dashed var(--rule);
    font-size: var(--t-xs); color: var(--muted); line-height: 1.5;
  }
  .card-views-hint:empty { display: none; }
  .modal-body .card-views-hint { display: none; }
  .card-view-link {
    font: inherit; background: none; border: none; padding: 0;
    color: var(--accent); font-weight: 600; cursor: pointer;
  }
  .card-view-link:hover { text-decoration: underline; }
  /* Persistent context header: metric name + definition stay above the tab bar
     on every tab, so a drill-down chart keeps its "what is this" context. */
  .modal-context { margin: 0 0 6px; }
  .modal-context .card-metric { margin-bottom: 6px; }
  .modal-context .card-plain { margin-bottom: 0; }
  .modal-tabs {
    display: flex; flex-wrap: wrap; gap: 0; margin: 6px 0 0; padding: 0;
    border-bottom: 2px solid var(--rule);
  }
  .modal-tab {
    font: inherit; font-size: var(--t-sm); font-weight: 600; color: var(--muted);
    background: none; border: none; border-bottom: 3px solid transparent;
    border-radius: 0; padding: 8px 15px 9px; margin-bottom: -2px; cursor: pointer;
    display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
    transition: color .15s, border-color .15s;
  }
  .modal-tab .tab-sub { font-size: var(--t-2xs); font-weight: 400; color: var(--muted); letter-spacing: .01em; line-height: 1; }
  .modal-tab:hover { color: var(--fg); border-bottom-color: var(--rule); }
  .modal-tab:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
  .modal-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .modal-tab.active .tab-sub { color: var(--accent); opacity: .75; }
  .modal-panel { display: none; }
  .modal-panel.active { display: block; }
  .modal-panel-view { padding-top: 6px; }
  .modal-panel-view table { margin-top: 0; }

  /* Share popover (Hawaii-dashboard pattern): a small menu under the Share
     button with Copy / Email / X / LinkedIn / Bluesky. Chrome only, so hover /
     focus use the slate-blue accent, never maroon. */
  .share-menu {
    position: fixed; z-index: 1100; min-width: 212px;
    background: var(--card); border: 1px solid var(--rule); border-radius: 10px;
    box-shadow: 0 12px 32px rgba(0,0,0,.18); padding: 6px;
    display: flex; flex-direction: column;
  }
  .share-menu-item {
    display: flex; align-items: center; gap: 11px; width: 100%;
    padding: 9px 12px; border: none; background: none; border-radius: 7px;
    font: inherit; font-size: 14px; color: var(--fg); text-decoration: none;
    cursor: pointer; text-align: left;
  }
  .share-menu-item svg { width: 17px; height: 17px; flex-shrink: 0; color: var(--muted); }
  .share-menu-item:hover, .share-menu-item:focus-visible {
    background: var(--bg); color: var(--accent); outline: none;
  }
  .share-menu-item:hover svg, .share-menu-item:focus-visible svg { color: var(--accent); }
  .share-menu-item.copied, .share-menu-item.copied svg { color: var(--positive); }

  /* Respect a reduced-motion preference: kill the card hover lift, chart/modal
     transitions and any animation for visitors who ask the OS to minimise motion. */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
    .card:hover { transform: none !important; }
  }
</style>
</head>
<body>
<div class="page">

<div class="masthead">
  <a class="masthead-brand" href="/">muslimdata.in</a>
  <nav class="masthead-nav">
    <a href="/about/">About</a>
  </nav>
  <p class="masthead-meta">Last updated {timestamp}</p>
</div>
<h1>The state of Muslim India, in data</h1>

<p class="headline-finding">
  India's roughly 20 crore (200 million) Muslims, or 14.2% of the population
  (Census 2011), trail the all-India average on <em>{n_behind} of the
  {n_total_comparable}</em> indicators that allow a direct comparison, widest on
  {top_behind_joined}.{ahead_clause}
</p>

<p class="preamble-note">
  Each card sets the latest Muslim figure beside Hindu and all-India baselines, drawn from <b>{n_sources}</b> primary government sources. Open any card for its chart, method and source. <a href="/about/">How these are measured →</a>
</p>
<div class="compare-toggle" role="radiogroup" aria-label="Choose comparison baseline for every card">
  <span class="compare-toggle-label">Compare Muslim outcomes to:</span>
  <button id="compare-all" class="compare-toggle-btn active" role="radio" aria-checked="true" type="button">all communities</button>
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
      <th data-col="3">Hindu</th>
      <th class="sortable" data-col="4">All</th>
      <th class="sortable" data-col="5">Gap vs reference</th>
    </tr></thead><tbody>
      {scorecard_rows}
    </tbody></table>
    </div>
    <p class="methodology">"Gap" is the Muslim value minus the reference baseline (Hindu where
    available, otherwise all communities). Red means the Muslim outcome is worse than the reference;
    green means it is better. For justice metrics, cells show the absolute count alongside the
    incarceration rate per 100,000 people of that religion, and the gap is the Muslim-to-Hindu
    rate ratio (1.0× means parity; above 1.0× means Muslims are overrepresented).</p>
  </div>
</details>

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
        // Aggregate rows (hate-speech, communal incidents) use a colspan for
        // the community columns, so they have no cell at col 2-5; treat the
        // missing value as lowest so the sort never throws on them.
        const ca = a.cells[col], cb = b.cells[col];
        const ka = ca ? sortKey(ca.textContent, col) : (col >= 1 ? -Infinity : '');
        const kb = cb ? sortKey(cb.textContent, col) : (col >= 1 ? -Infinity : '');
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
// The comparison baseline (labelled "All communities") is a weighted aggregate
// that CONTAINS every community, so it is never a peer bar. It is drawn as a
// dashed reference line (like the Hawaiʻi dashboard's US reference), via refValue.
function _refLine(refValue, refLabel) {
  return { id: 'refline', afterDatasetsDraw(chart) {
    if (refValue == null) return;
    const { ctx, chartArea: { top, bottom, left, right }, scales: { x } } = chart;
    const px = x.getPixelForValue(refValue);
    ctx.save();
    ctx.strokeStyle = '#9aa3a8'; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(px, top); ctx.lineTo(px, bottom); ctx.stroke();
    ctx.setLineDash([]);
    // Label the reference line. Darker + slightly larger than the line so
    // the reference label reads at a glance on every chart (it was easy to
    // miss at 9px light-grey). Flip alignment near the edges so it never clips.
    ctx.font = '600 10px -apple-system, system-ui, sans-serif';
    ctx.fillStyle = '#5f6b73';
    const half = ctx.measureText(refLabel).width / 2;
    if (px + half > right) { ctx.textAlign = 'right'; ctx.fillText(refLabel, right, top - 3); }
    else if (px - half < left) { ctx.textAlign = 'left'; ctx.fillText(refLabel, left, top - 3); }
    else { ctx.textAlign = 'center'; ctx.fillText(refLabel, px, top - 3); }
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
      scales: { x: { display: false, grace: '8%', beginAtZero: beginAtZero === true,
        // Keep the dashed All-communities reference line inside the axis even when
        // it sits beyond every bar (lone-bar cards like mpce / GER, where the
        // baseline is higher than the single Muslim bar).
        suggestedMin: refValue == null ? undefined : Math.min(refValue, ...values),
        suggestedMax: refValue == null ? undefined : Math.max(refValue, ...values) },
        y: { grid: { display: false }, border: { display: false }, ticks: { font: { size: 11 } } } },
    },
    plugins: [_valueLabels(decimals, suffix), _refLine(refValue == null ? null : refValue, refLabel)],
  });
}
function lineChart(id, labels, values, color, suffix, decimals) {
  _spec(id, 'lineChart', Array.from(arguments).slice(1));
  new Chart(document.getElementById(id), {
    type: 'line',
    data: { labels: labels, datasets: [{ data: values, borderColor: color, backgroundColor: 'rgba(43,108,176,.12)', fill: true, tension: 0.3, pointRadius: 3, pointBackgroundColor: color }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => c.parsed.y.toFixed(decimals) + suffix } } },
      scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } }, y: { beginAtZero: false, grace: '10%', grid: { color: '#f0ede4', drawTicks: false }, border: { display: false }, ticks: { font: { size: 10 }, color: '#999', maxTicksLimit: 5 } } },
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
        label: d.label, color: d.borderColor, isRefline: !!d._isRefline,
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
      // Reference-line labels (All-India / median) get the same legible slate
      // used on the hbar charts, while the dashed line itself stays light grey.
      ctx.fillStyle = it.isRefline ? '#5f6b73' : it.color;
      ctx.textAlign = 'left';
      ctx.fillText(it.label, it.x + 5, it.y);
    }
    ctx.restore();
  }};
}
function trendChart(id, years, seriesMap, allSeries, suffix, decimals, hasBreak, refLine, dashedExtras, mode) {
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
    const labelText = Array.isArray(allSeries) ? 'All communities' : (allSeries.label || 'All communities');
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
          callbacks: { label: (c) => c.dataset.label + ': ' + c.parsed.y.toFixed(decimals) + suffix },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { beginAtZero: false, grace: '12%', grid: { color: '#f0ede4', drawTicks: false },
             border: { display: false }, ticks: { font: { size: 10 }, color: '#999', maxTicksLimit: 5 } },
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

// Compare toggle: flips every comparison pill on the page between vs all communities
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
  const factories = { hbar, lineChart, trendChart, concentrationCurve };
  let modalCharts = [];
  let activeMid = null;

  // Clean per-tab URL (Hawaii pattern): the address bar always shows the
  // shareable /m/{mid}/ (overview) or /m/{mid}/{view}/ path. A reload of that
  // path hits the matching static stub, which redirects back through the
  // #{mid}/{view} hash into the SPA, which then rewrites to this clean path.
  function setMetricUrl(mid, view) {
    if (!mid) return;
    const path = '/m/' + encodeURIComponent(mid) + '/' +
      (view && view !== 'overview' ? encodeURIComponent(view) + '/' : '');
    if (location.pathname !== path) history.replaceState(null, '', path);
  }

  function switchView(view) {
    body.querySelectorAll('.modal-tab').forEach((t) =>
      t.classList.toggle('active', t.dataset.view === view));
    body.querySelectorAll('.modal-panel').forEach((p) =>
      p.classList.toggle('active', p.dataset.view === view));
    setMetricUrl(activeMid, view);
    // A chart created while its tab was hidden was sized 0; now that the panel
    // is visible, nudge any chart in it to remeasure (the by-district curve).
    const panel = body.querySelector('.modal-panel.active');
    if (panel) panel.querySelectorAll('canvas').forEach((cv) => {
      const c = Chart.getChart(cv); if (c) c.resize();
    });
    if (typeof gtag === 'function' && view !== 'overview' && activeMid) {
      gtag('event', 'metric_view_opened', { metric_id: activeMid, view });
    }
  }

  function openModal(card, targetView) {
    closeChart();
    const clone = card.cloneNode(true);
    body.innerHTML = '';

    // --- Persistent context header -------------------------------------
    // Lift the metric name + one-line definition OUT of the cloned card into a
    // header that sits above the tab bar, so they stay visible on every tab.
    // Without this, a drill-down tab (e.g. By state) is a bare table with no
    // statement of which metric it belongs to. The name also carries
    // id="modal-title", the dialog's aria-labelledby target.
    const ctx = document.createElement('div');
    ctx.className = 'modal-context';
    const nameEl = clone.querySelector('.card-metric');
    const defEl = clone.querySelector('.card-plain');
    if (nameEl) { nameEl.id = 'modal-title'; ctx.appendChild(nameEl); }
    if (defEl) ctx.appendChild(defEl);
    body.appendChild(ctx);

    // --- Tabbed layout (Hawaii-dashboard pattern) ----------------------
    // The card carries its drill-down "views" (By state / By sex / By
    // district) in a hidden .card-views block. Lift each into its own modal
    // tab so the card face stays uncluttered while the detail view keeps the
    // full data one click away. An "Overview" tab holds the cloned card
    // (chart, comparisons, About). Metrics without extra views get no tab bar.
    const panels = document.createElement('div');
    panels.className = 'modal-panels';
    const overview = document.createElement('div');
    overview.className = 'modal-panel active';
    overview.dataset.view = 'overview';
    overview.appendChild(clone);
    panels.appendChild(overview);

    const views = Array.from(clone.querySelectorAll('.card-views > details[data-view-id]'));
    if (views.length) {
      const tabBar = document.createElement('div');
      tabBar.className = 'modal-tabs';
      tabBar.setAttribute('role', 'tablist');
      const mkTab = (label, sub, view, active) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'modal-tab' + (active ? ' active' : '');
        b.setAttribute('role', 'tab');
        b.dataset.view = view;
        b.innerHTML = '<span>' + label + '</span>' +
          (sub ? '<span class="tab-sub">' + sub + '</span>' : '');
        b.addEventListener('click', () => switchView(view));
        return b;
      };
      tabBar.appendChild(mkTab('Overview', 'Chart and summary', 'overview', true));
      views.forEach((d) => {
        const vid = d.getAttribute('data-view-id') || 'view';
        const label = d.getAttribute('data-view-label') || 'View';
        const sub = d.getAttribute('data-view-sub') || '';
        const panel = document.createElement('div');
        panel.className = 'modal-panel modal-panel-view';
        panel.dataset.view = vid;
        // Move the disclosure's content (minus its <summary>) into the panel;
        // the tab itself is now the label, so the summary is redundant.
        Array.from(d.childNodes).forEach((n) => {
          if (n.nodeType === 1 && n.tagName === 'SUMMARY') return;
          panel.appendChild(n);
        });
        d.remove();
        panels.appendChild(panel);
        tabBar.appendChild(mkTab(label, sub, vid, false));
      });
      body.appendChild(tabBar);
    }
    body.appendChild(panels);

    activeMid = card.getAttribute('data-metric-id') || null;

    // Reveal the modal first so the layout pass settles and the wrapper
    // picks up its 440px CSS height. Chart.js measures its container at
    // construction, so we defer instantiation to the next frame.
    overlay.hidden = false;
    document.body.classList.add('modal-open');
    closeBtn.focus();

    // Re-render every chart in the clone on a fresh canvas: the overview chart
    // plus any per-tab chart (e.g. pop-share's by-district concentration curve).
    // The clone's canvas ids still match the originals, which are the CHART_SPECS
    // keys. A chart whose tab is hidden is created 0-size and auto-resizes
    // (responsive) when shown; switchView also nudges it.
    // Query `body` not `clone`: per-tab canvases were just moved out of the
    // clone into their own panels, so they are no longer clone descendants.
    body.querySelectorAll('canvas').forEach((cv) => {
      const origId = cv.id;
      const spec = CHART_SPECS[origId];
      if (!spec || !factories[spec.fnName]) return;
      cv.removeAttribute('width');
      cv.removeAttribute('height');
      cv.style.width = '';
      cv.style.height = '';
      cv.id = origId + '-modal';
      // trendChart's signature is (id, years, seriesMap, allSeries, suffix,
      // decimals, hasBreak, refLine, dashedExtras, mode). Preserve args 0-7 and
      // force mode='modal' at position 8 so it lands in the correct slot.
      let args = spec.args;
      if (spec.fnName === 'trendChart') {
        args = spec.args.slice(0, 8);
        while (args.length < 8) args.push(undefined);
        args.push('modal');
      }
      factories[spec.fnName](cv.id, ...args);
      const ch = Chart.getChart(cv.id);
      if (ch) modalCharts.push(ch);
    });
    // Force a resize after layout settles so labels reflow into the modal's
    // larger real estate (Chart.js measures at construction).
    requestAnimationFrame(() => modalCharts.forEach((c) => c && c.resize()));

    // Honour a requested initial tab (e.g. a card-face "By state" hint). The
    // chart was built above while Overview was visible so Chart.js could
    // measure it; only now do we reveal the requested view.
    if (targetView && targetView !== 'overview') switchView(targetView);

    // Reflect the open metric + tab in the address bar as a shareable clean
    // path (switchView already did this for a non-overview target).
    setMetricUrl(activeMid, targetView || 'overview');
    if (typeof gtag === 'function' && activeMid) {
      gtag('event', 'metric_opened', { metric_id: activeMid });
    }
  }

  function closeChart() {
    modalCharts.forEach((c) => { try { c.destroy(); } catch (e) { /* already gone */ } });
    modalCharts = [];
  }

  function closeModal() {
    ShareMenu.close();
    closeChart();
    overlay.hidden = true;
    document.body.classList.remove('modal-open');
    body.innerHTML = '';
    activeMid = null;
    // Reset the address bar to the site root so closing leaves a shareable URL.
    if (location.pathname !== '/' || location.hash) {
      history.replaceState(null, '', '/' + location.search);
    }
  }

  function openByMid(mid, view) {
    if (!mid) return false;
    const card = document.querySelector('.cards .card[data-metric-id="' + CSS.escape(mid) + '"]');
    if (!card) return false;
    openModal(card, view);
    return true;
  }

  closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !overlay.hidden) {
      closeModal();
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

  // --- Share menu (Hawaii-dashboard pattern) ---------------------------
  // A small popover: Copy link / Email / X / LinkedIn / Bluesky. On a touch
  // device with a native share sheet we use that instead. The shared URL is the
  // ACTIVE tab's clean permalink, so the preview unfurls from the matching
  // per-view stub's OG meta. Chrome only (slate-blue accent), never maroon.
  const ShareMenu = (function () {
    const ICON = {
      copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>',
      email: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 7 10 6 10-6"/></svg>',
      x: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.9 1.6h3.3l-7.2 8.2L23.7 22h-6.6l-5.2-6.8L5.9 22H2.6l7.7-8.8L1 1.6h6.8l4.7 6.2zM17.7 20h1.8L7.1 3.5H5.1z"/></svg>',
      linkedin: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.4 3H3.6a.6.6 0 0 0-.6.6v16.8a.6.6 0 0 0 .6.6h16.8a.6.6 0 0 0 .6-.6V3.6a.6.6 0 0 0-.6-.6zM8.3 18.3H5.6V9.7h2.7v8.6zM6.9 8.5a1.6 1.6 0 1 1 0-3.1 1.6 1.6 0 0 1 0 3.1zm11.4 9.8h-2.7v-4.2c0-1 0-2.3-1.4-2.3s-1.6 1.1-1.6 2.2v4.3H9.9V9.7h2.6v1.2h.1c.4-.7 1.2-1.4 2.5-1.4 2.7 0 3.2 1.8 3.2 4.1v4.7z"/></svg>',
      bluesky: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6.3 4.2C8.6 5.9 11 9.4 12 11.3c1-1.9 3.4-5.4 5.7-7.1 1.7-1.2 4.3-2.2 4.3 1.7 0 .8-.5 5.2-.7 5.9-.8 2.4-3.2 3-5.4 2.7 3.8.6 4.8 2.8 2.7 4.9-4 4-5.7-1-6.1-2.3-.1-.2-.1-.3-.2-.3s-.1.1-.2.3c-.4 1.3-2.1 6.3-6.1 2.3-2.1-2.1-1.1-4.3 2.7-4.9-2.2.3-4.6-.3-5.4-2.7-.2-.7-.7-5.1-.7-5.9 0-3.9 2.6-2.9 4.3-1.7z"/></svg>',
    };
    let menu = null, anchor = null;
    function close() {
      if (menu) { menu.remove(); menu = null; }
      if (anchor) { anchor.setAttribute('aria-expanded', 'false'); anchor = null; }
      document.removeEventListener('click', onDoc, true);
      document.removeEventListener('keydown', onKey, true);
      window.removeEventListener('resize', close);
      window.removeEventListener('scroll', close, true);
    }
    function onDoc(e) {
      if (!menu) return;
      if (menu.contains(e.target) || (anchor && anchor.contains(e.target))) return;
      close();
    }
    function onKey(e) {
      if (!menu) return;
      if (e.key === 'Escape') { const a = anchor; close(); if (a) a.focus(); e.stopPropagation(); e.preventDefault(); return; }
      if (e.key === 'Tab') {
        e.stopPropagation();
        const items = Array.from(menu.querySelectorAll('.share-menu-item'));
        if (!items.length) return;
        const first = items[0], last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
    function place() {
      const r = anchor.getBoundingClientRect();
      let top = r.bottom + 6;
      if (top + menu.offsetHeight + 8 > window.innerHeight && r.top - menu.offsetHeight - 6 > 0)
        top = r.top - menu.offsetHeight - 6;
      let left = Math.min(r.right - menu.offsetWidth, window.innerWidth - menu.offsetWidth - 8);
      left = Math.max(8, left);
      menu.style.top = top + 'px';
      menu.style.left = left + 'px';
    }
    function mkItem(method, label, href, onClick) {
      const el = document.createElement(href ? 'a' : 'button');
      el.className = 'share-menu-item';
      el.setAttribute('role', 'menuitem');
      if (href) { el.href = href; el.target = '_blank'; el.rel = 'noopener'; }
      else { el.type = 'button'; }
      el.innerHTML = ICON[method] + '<span>' + label + '</span>';
      el.addEventListener('click', onClick);
      return el;
    }
    function open(btn, opts) {
      if (menu && anchor === btn) { close(); return; }   // toggle
      const touch = window.matchMedia && window.matchMedia('(hover: none) and (pointer: coarse)').matches;
      if (touch && navigator.share) {
        navigator.share({ title: opts.title, text: opts.lede, url: opts.url })
          .then(() => opts.track && opts.track('native')).catch(() => {});
        return;
      }
      close();
      anchor = btn;
      const url = opts.url, title = opts.title, lede = opts.lede;
      const track = (m) => { try { if (opts.track) opts.track(m); } catch (e) {} };
      menu = document.createElement('div');
      menu.className = 'share-menu';
      menu.setAttribute('role', 'menu');
      menu.appendChild(mkItem('copy', 'Copy link', null, (e) => {
        e.preventDefault();
        const it = e.currentTarget, span = it.querySelector('span');
        const finish = () => { if (span) span.textContent = 'Copied'; it.classList.add('copied'); track('copy'); setTimeout(close, 900); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(finish, finish);
        else finish();
      }));
      menu.appendChild(mkItem('email', 'Email',
        'mailto:?subject=' + encodeURIComponent(title) + '&body=' + encodeURIComponent(lede + '\\n\\n' + url),
        () => { track('email'); close(); }));
      menu.appendChild(mkItem('x', 'Share on X',
        'https://x.com/intent/post?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url),
        () => { track('x'); close(); }));
      menu.appendChild(mkItem('linkedin', 'Share on LinkedIn',
        'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(url),
        () => { track('linkedin'); close(); }));
      menu.appendChild(mkItem('bluesky', 'Share on Bluesky',
        'https://bsky.app/intent/compose?text=' + encodeURIComponent(title + ' ' + url),
        () => { track('bluesky'); close(); }));
      document.body.appendChild(menu);
      btn.setAttribute('aria-expanded', 'true');
      place();
      document.addEventListener('click', onDoc, true);
      document.addEventListener('keydown', onKey, true);
      window.addEventListener('resize', close);
      window.addEventListener('scroll', close, true);
      const first = menu.querySelector('.share-menu-item');
      if (first) first.focus();
    }
    return { open, close };
  })();

  // Share button -> open the menu for the ACTIVE tab's permalink.
  shareBtn.setAttribute('aria-haspopup', 'menu');
  shareBtn.setAttribute('aria-expanded', 'false');
  shareBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!activeMid) return;
    const card = body.querySelector('.card');
    const name = card ? (card.getAttribute('data-metric-name') || activeMid) : activeMid;
    const activeTabEl = body.querySelector('.modal-tab.active');
    const view = activeTabEl ? activeTabEl.dataset.view : 'overview';
    const labelSpan = activeTabEl ? activeTabEl.querySelector('span') : null;
    const viewLabel = (view && view !== 'overview' && labelSpan) ? labelSpan.textContent : '';
    const url = location.origin + '/m/' + encodeURIComponent(activeMid) + '/' +
      (view && view !== 'overview' ? encodeURIComponent(view) + '/' : '');
    ShareMenu.open(shareBtn, {
      url: url,
      title: 'muslimdata.in: ' + name + (viewLabel ? ' (' + viewLabel + ')' : ''),
      lede: name,
      track: (method) => { if (typeof gtag === 'function') gtag('event', 'share_clicked', { metric_id: activeMid, view: view, method: method }); },
    });
  });

  document.querySelectorAll('.cards .card').forEach((card) => {
    card.addEventListener('click', (e) => {
      // A card-face "view" hint (e.g. "By state") opens the modal straight to
      // that tab; data-view-id matches the modal tab's data-view + URL segment.
      const viewLink = e.target.closest('.card-view-link');
      if (viewLink) {
        openModal(card, viewLink.getAttribute('data-view-id') || undefined);
        return;
      }
      // Let links, summaries, and download triggers behave normally.
      if (e.target.closest('a, summary, details, button')) return;
      openModal(card);
    });
  });

  // Hash routing: open the matching modal on page load or hash change. The hash
  // form is #{mid} or #{mid}/{view} (the per-tab stub's redirect target);
  // openModal then rewrites the address bar to the clean /m/{mid}/{view}/ path.
  function handleHash() {
    const raw = location.hash.replace(/^#/, '');
    if (!raw) {
      if (!overlay.hidden) closeModal();
      return;
    }
    const slash = raw.indexOf('/');
    const mid = slash === -1 ? raw : raw.slice(0, slash);
    const view = slash === -1 ? undefined : raw.slice(slash + 1);
    openByMid(mid, view);
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
<link rel="canonical" href="{canonical_url}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#fafaf7">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{og_url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="muslimdata.in">
<meta property="og:image" content="{og_image_url}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{og_image_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{og_image_url}">
<meta http-equiv="refresh" content="0; url={refresh_url}">
<script>location.replace({redirect_target});</script>
<style>body{{font:14px -apple-system,system-ui,sans-serif;color:#666;padding:40px;text-align:center}}</style>
<!--DATASET_JSONLD-->
</head>
<body>
<p>Redirecting to <a href="{refresh_url}">muslimdata.in</a>...</p>
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
_OG_ACCENT = (123, 29, 34)    # site --muslim maroon (hero value + wordmark)
_OG_TIER = {                  # comp-pill TEXT polarity only: --positive/--negative/--neutral
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
    comp_label = "vs all communities"
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
        comp_value = f"{_gap_str(gap, unit)} {_verdict_word(cls, gap)}"
        comp_class = cls
    year = _year_of(mid)
    return dict(name=name, hero=fmt_num(muslim, unit), caption=caption,
                year=str(year) if year else "",
                comp_label=comp_label if comp_value else "",
                comp_value=comp_value, comp_class=comp_class, polarity=polarity)


def _state_extremes(mid: str):
    """(hi_name, hi_val, lo_name, lo_val) for a metric's state-level feature
    series (Muslim where the metric splits by religion, else the dominant
    series), each state at its OWN latest year. None if no state rows. Mirrors
    the feature-selection logic in _state_details so the OG nugget matches the
    'By state' tab."""
    from collections import defaultdict
    rows = [r for r in load_metric(mid) if r["geography_level"] == "state"]
    if not rows:
        return None
    latest_year: dict[str, int] = defaultdict(int)
    for r in rows:
        y = int(r["year"])
        if y > latest_year[r["geography_code"]]:
            latest_year[r["geography_code"]] = y
    by_geo: dict[str, dict] = defaultdict(dict)
    for r in rows:
        g = r["geography_code"]
        if int(r["year"]) == latest_year[g]:
            by_geo[g][r["religion"]] = float(r["value"])
    if any("muslim" in v for v in by_geo.values()):
        feature = "muslim"
    else:
        keys = [k for v in by_geo.values() for k in v]
        feature = max(set(keys), key=keys.count) if keys else "all"
    vals = [(g, v[feature]) for g, v in by_geo.items() if feature in v]
    if not vals:
        return None
    hi = max(vals, key=lambda x: x[1])
    lo = min(vals, key=lambda x: x[1])
    return state_label(hi[0]), hi[1], state_label(lo[0]), lo[1]


def _og_view_data(m: dict, view: dict):
    """OG payload for one metric VIEW (by-state / by-sex / by-district): the base
    metric card payload plus a `view_label` badge and a one-line `view_detail`
    data nugget. Falls back to the view's sub-label if the nugget can't be
    computed. Returns None when the base metric has no carded payload."""
    base = _og_data_for_metric(m)
    if not base:
        return None
    mid = m["id"]
    unit = m["display"]["scorecard"]["unit_format"]
    vid = view["id"]
    detail = ""
    if vid == "by-state":
        ex = _state_extremes(mid)
        if ex:
            hi_n, hi_v, lo_n, lo_v = ex
            detail = (f"Highest {hi_n} {fmt_num(hi_v, unit)} · "
                      f"Lowest {lo_n} {fmt_num(lo_v, unit)}")
    elif vid == "by-sex":
        rows = [r for r in load_metric(mid, sex=None)
                if r["geography_level"] == "national" and r["religion"] == "muslim"
                and r["sex"] in ("male", "female")]
        if rows:
            latest = max(int(r["year"]) for r in rows)
            bys = {r["sex"]: float(r["value"]) for r in rows if int(r["year"]) == latest}
            if "male" in bys and "female" in bys:
                detail = (f"Muslim male {fmt_num(bys['male'], unit)} · "
                          f"female {fmt_num(bys['female'], unit)}")
    elif vid == "by-district":
        # The by-district view's data always comes from the concentration
        # canonical (it hosts the top-100 ranking), regardless of the host card.
        try:
            conc = _nat_by_religion("district-concentration-top100").get("muslim")
            _, top10 = _district_cumulative("district-concentration-top100")
            detail = (f"{_round_str(conc, 1)}% in the top 100 districts · "
                      f"top 10 hold {_round_str(top10, 1)}%")
        except Exception:
            detail = ""
    if not detail:
        detail = view.get("sub", "")
    return dict(base, view_label=view["label"], view_detail=detail)


def _render_og_image(out_path: pathlib.Path, payload: dict) -> None:
    """Draw a 1200x630 PNG to out_path from the OG payload."""
    img = Image.new("RGB", (OG_W, OG_H), _OG_BG)
    draw = ImageDraw.Draw(img)
    margin = 64
    # Top accent rule + brand row.
    draw.rectangle([(0, 0), (OG_W, 12)], fill=_OG_ACCENT)
    draw.text((margin, 36), "muslimdata.in", font=_og_font(28, bold=True), fill=_OG_ACCENT)
    # Top-right badge: the view name (accent) for a per-view card, else the
    # polarity hint (muted) for the base metric card.
    if payload.get("view_label"):
        badge_font = _og_font(22, bold=True)
        badge_text = payload["view_label"].upper()
        badge_w = draw.textlength(badge_text, font=badge_font)
        draw.text((OG_W - margin - badge_w, 42), badge_text, font=badge_font, fill=_OG_ACCENT)
    elif payload.get("polarity"):
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
    # Right column: for a per-view card, a "BREAKDOWN" data nugget (e.g. highest/
    # lowest state, male vs female, top-10 district share); otherwise the
    # comparison block (vs all communities / vs Hindu), when present.
    if payload.get("view_label") and payload.get("view_detail"):
        col_x = 620
        head_font = _og_font(24, bold=True)
        draw.text((col_x, hero_y + 10), "BREAKDOWN", font=head_font, fill=_OG_MUTED)
        nug_font = _og_font(34, bold=True)
        nug_lines = _og_wrap(draw, payload["view_detail"], nug_font,
                             OG_W - margin - col_x, max_lines=4)
        for i, line in enumerate(nug_lines):
            draw.text((col_x, hero_y + 56 + i * 46), line, font=nug_font, fill=_OG_FG)
    elif payload.get("comp_label") and payload.get("comp_value"):
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
    draw.text((margin, y + 20), f"{len(_carded_metrics())} indicators across 6 themes.",
              font=_og_font(32), fill=_OG_FG)
    draw.text((margin, y + 70), "Hindu and all-India comparison baselines on every metric.",
              font=_og_font(32), fill=_OG_MUTED)
    draw.text((margin, OG_H - 60),
              "Census · NFHS · PLFS · AISHE · NCRB · PRS-ECI",
              font=_og_font(22), fill=_OG_MUTED)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)


def _emit_og_images(out_dir: pathlib.Path, view_map: dict | None = None) -> int:
    """Generate 1200x630 PNGs: /og/{mid}.png per metric, /og/{mid}-{view}.png per
    modal view (by-state / by-sex / by-district), plus /og/default.png for the
    homepage and About page. Returns the total count written."""
    if Image is None:
        print("WARN: Pillow not installed; skipping OG image generation")
        return 0
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        data = _yaml.safe_load(f)
    view_map = view_map or {}
    og_dir = out_dir / "og"
    og_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for m in data["metrics"]:
        payload = _og_data_for_metric(m)
        if not payload:
            continue
        _render_og_image(og_dir / f"{m['id']}.png", payload)
        written += 1
        for view in view_map.get(m["id"], []):
            vpayload = _og_view_data(m, view)
            if not vpayload:
                continue
            _render_og_image(og_dir / f"{m['id']}-{view['id']}.png", vpayload)
            written += 1
    _render_og_default(og_dir / "default.png")
    return written


def _emit_metric_stubs(out_dir: pathlib.Path, view_map: dict | None = None) -> int:
    """Write per-VIEW redirect stub pages at /m/{mid}/{view}/index.html (the
    overview /m/{mid}/ is a full landing page, see _emit_metric_landings). Each
    view stub carries its own OG meta (title, description, per-view OG image) and
    client-redirects into the main page's #{mid}/{view} hash so the modal
    auto-opens on the right tab; it canonicalises to the overview landing page to
    consolidate SEO. Returns the count of stubs written."""
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        data = _yaml.safe_load(f)
    view_map = view_map or {}
    stubs_root = out_dir / "m"
    stubs_root.mkdir(parents=True, exist_ok=True)
    written = 0

    def _write(sub_path, og_url_path, canonical_url, title, og_title,
               description, og_image, redirect_hash, jsonld):
        # 240-char cap so the description fits inside what social cards display.
        if len(description) > 240:
            description = description[:237].rstrip() + "..."
        page = STUB_TEMPLATE.format(
            title=html.escape(title),
            og_title=html.escape(og_title),
            description=html.escape(description),
            og_image_alt=html.escape(
                f"{og_title}: Indian Muslims vs Hindu and all-India baselines on muslimdata.in"),
            canonical_url=canonical_url,
            og_url=f"{SITE_URL}/{og_url_path}",
            og_image_url=f"{SITE_URL}/og/{og_image}",
            refresh_url=f"/#{redirect_hash}",
            redirect_target=json.dumps(f"/#{redirect_hash}"),
        )
        page = page.replace("<!--DATASET_JSONLD-->", jsonld)
        d = stubs_root / sub_path
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page)

    for m in data["metrics"]:
        disp = m.get("display", {}).get("scorecard")
        if not disp or disp.get("include", True) is False:
            continue
        mid = m["id"]
        name = m.get("name", disp.get("label", mid))
        overview_canonical = f"{SITE_URL}/m/{mid}/"
        # Per-view stubs (canonical -> overview landing page; own OG image + title).
        for view in view_map.get(mid, []):
            vid, vlabel, vsub = view["id"], view["label"], view.get("sub", "")
            vdesc = (f"{name} {vlabel.lower()}"
                     + (f" ({vsub})" if vsub else "")
                     + ", with Hindu and all-India baselines on muslimdata.in.")
            _write(
                sub_path=f"{mid}/{vid}",
                og_url_path=f"m/{mid}/{vid}/",
                canonical_url=overview_canonical,
                title=f"{name}, {vlabel.lower()}: muslimdata.in",
                og_title=f"{name} · {vlabel}",
                description=vdesc,
                og_image=f"{mid}-{vid}.png",
                redirect_hash=f"{mid}/{vid}",
                jsonld="",
            )
            written += 1
    return written


# ----- Per-metric landing pages (full, indexable; Hawaii /c/{slug}/ analog) -----
# Replaces the old /m/{mid}/ redirect stub with a real self-canonical page:
# hero + comparison, national-by-religion table, the same state/sex/district
# breakdown tables the modal shows, methodology + sources, related-metric links,
# and Dataset + BreadcrumbList JSON-LD, with a CTA into the interactive chart at
# /#{mid}. The per-view stubs (/m/{mid}/{view}/) still redirect + canonicalise here.
LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#fafaf7">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="muslimdata.in">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{og_image_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{og_image}">
<script src="/js/analytics.js" defer></script>
<style>
  :root {
    --fg:#1a1a1a; --muted:#666; --bg:#fafaf7; --card:#fff; --rule:#e6e3da;
    --muslim:#7b1d22; --accent:#2c5f8a; --positive:#065F46; --negative:#991B1B;
  }
  * { box-sizing:border-box; }
  body { font:16px/1.6 -apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif; color:var(--fg); background:var(--bg); margin:0; }
  .page { max-width:820px; margin:0 auto; padding:32px 24px 64px; }
  a { color:var(--accent); }
  .masthead { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px 16px; margin-bottom:14px; padding-bottom:10px; border-bottom:1px solid var(--rule); }
  .masthead-brand { font-size:14px; font-weight:600; color:var(--fg); text-decoration:none; }
  .masthead-brand:hover { color:var(--accent); }
  .masthead-nav { display:flex; gap:14px; margin-right:auto; margin-left:24px; }
  .masthead-nav a { font-size:13px; color:var(--fg); text-decoration:none; font-weight:500; }
  .masthead-nav a:hover { color:var(--accent); }
  .masthead-meta { margin:0; font-size:12px; color:var(--muted); }
  .breadcrumb { font-size:13px; color:var(--muted); margin:14px 0 4px; }
  .breadcrumb a { color:var(--accent); text-decoration:none; }
  .breadcrumb a:hover { text-decoration:underline; }
  .breadcrumb [aria-current] { color:var(--fg); font-weight:600; }
  h1 { font-size:30px; margin:8px 0 8px; letter-spacing:-0.01em; line-height:1.2; }
  .lede { font-size:17px; color:var(--muted); margin:0 0 20px; max-width:60em; }
  .hero { display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; margin:8px 0 4px; }
  .hero-value { font-size:2.6rem; font-weight:700; letter-spacing:-.02em; color:var(--muslim); font-feature-settings:"tnum"; }
  .hero-unit, .hero-year { font-size:15px; color:var(--muted); font-weight:500; }
  .polarity { font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.02em; margin:0 0 6px; font-weight:600; }
  .polarity span { color:var(--positive); }
  .compare { font-size:15px; color:var(--fg); margin:0 0 16px; }
  .compare b { font-feature-settings:"tnum"; }
  .compare b.good { color:var(--positive); } .compare b.bad { color:var(--negative); } .compare b.mid, .compare b.neutral { color:var(--muted); }
  .cta { display:inline-block; background:var(--accent); color:#fff; text-decoration:none; font-weight:600; font-size:15px; padding:11px 18px; border-radius:8px; margin:6px 0 8px; transition:background .15s; }
  .cta:hover { background:#234c70; }
  h2 { font-size:19px; margin:34px 0 8px; letter-spacing:-0.005em; }
  .breakdown-sub { font-size:13px; font-weight:400; color:var(--muted); margin-left:8px; }
  table { width:100%; border-collapse:collapse; margin:10px 0; font-size:14px; font-feature-settings:"tnum"; }
  th,td { text-align:right; padding:7px 10px; border-bottom:1px solid var(--rule); }
  th:first-child, td:first-child { text-align:left; }
  th { font-weight:600; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
  .scroll-table { max-height:380px; overflow-y:auto; border:1px solid var(--rule); border-radius:6px; margin:10px 0; }
  .scroll-table table { margin:0; }
  .scroll-table thead th { position:sticky; top:0; background:var(--card); }
  .src-note { font-size:13px; color:var(--muted); }
  .meta-block p { font-size:14.5px; line-height:1.6; max-width:60em; }
  .meta-block b { color:var(--accent); }
  ul.related { list-style:none; padding:0; margin:10px 0; display:flex; flex-wrap:wrap; gap:8px; }
  ul.related a { display:inline-block; padding:7px 12px; border:1px solid var(--rule); border-radius:999px; background:var(--card); text-decoration:none; font-size:13px; font-weight:500; color:var(--accent); }
  ul.related a:hover { border-color:var(--accent); }
  hr { border:none; border-top:1px solid var(--rule); margin:36px 0 0; }
  footer { font-size:13px; color:var(--muted); margin-top:24px; }
  @media (max-width:560px) { h1 { font-size:24px; } .hero-value { font-size:2rem; } .masthead-nav { margin-left:0; } }
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-duration:.01ms !important; animation-duration:.01ms !important; } }
</style>
{jsonld}
</head>
<body>
<div class="page">
<div class="masthead">
  <a class="masthead-brand" href="/">muslimdata.in</a>
  <nav class="masthead-nav">
    <a href="/">Dashboard</a>
    <a href="/about/">About</a>
  </nav>
  <p class="masthead-meta">Last updated {timestamp}</p>
</div>
<nav class="breadcrumb" aria-label="Breadcrumb">{breadcrumb}</nav>
<h1>{h1}</h1>
<p class="lede">{lede}</p>
<div class="hero"><span class="hero-value">{hero_value}</span><span class="hero-unit">{hero_unit}</span><span class="hero-year">{hero_year}</span></div>
{polarity_html}
{compare_html}
<p><a class="cta" href="/#{mid}">{cta_label}</a></p>
{national_html}
{breakdowns_html}
<h2>About this measurement</h2>
<div class="meta-block">{about_html}</div>
{related_html}
<hr>
<footer><p>Every value traces to a primary source with the original file archived and checksummed. muslimdata.in is independent, non-commercial, and <a href="https://github.com/iqbash1/indian-muslims-dashboard">open source</a>. Last updated {timestamp}.</p></footer>
</div>
</body>
</html>
"""


def _community_label(rel: str) -> str:
    return "All communities" if rel == "all" else COMMUNITY_LABEL.get(rel, rel.capitalize())


def _landing_national_table(mid: str, unit: str) -> str:
    """Static Community | Value table for the metric's latest national year.
    Returns '' for muslim-only metrics (a single row isn't a comparison)."""
    by_rel = _nat_by_religion(mid)
    if len(by_rel) <= 1:
        return ""
    order = [r for r in ("muslim", "hindu") if r in by_rel]
    order += sorted([r for r in by_rel if r not in ("muslim", "hindu", "all")],
                    key=lambda r: -by_rel[r])
    if "all" in by_rel:
        order.append("all")
    rows = "".join(
        f'<tr><td>{html.escape(_community_label(r))}</td>'
        f'<td>{html.escape(fmt_num(by_rel[r], unit))}</td></tr>'
        for r in order)
    return ('<table><thead><tr><th scope="col">Community</th><th scope="col">Latest value</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def _landing_breakdowns(m: dict, views: list) -> str:
    """The metric's drill-down tables (state / sex / district), the same ones the
    modal shows as tabs, rendered inline as static sections. Driven by `views`
    (= view_map[mid]) so it never shows a breakdown the card lacks; reuses the
    exact table renderers (stripped of their <details>/<summary> wrapper)."""
    mid = m["id"]
    disp = m["display"]["scorecard"]
    unit = disp["unit_format"]
    special = disp.get("special_render")
    parts = []
    for v in views:
        vid = v["id"]
        if vid == "by-state":
            block = _state_details(
                mid, "count" if special == "time_series_count" else unit,
                value_label=(CAPTION.get(mid, "count").capitalize()
                             if special == "time_series_count" else None))
        elif vid == "by-sex":
            block = _sex_details(mid, unit)
        elif vid == "by-district":
            # Always the concentration canonical (the top-100 ranking), with a
            # stat note; chart-free here (the curve is interactive-only).
            cmid = "district-concentration-top100"
            conc = _nat_by_religion(cmid).get("muslim")
            parsed = _parse_district_rows(cmid)
            if conc is not None and parsed:
                _, top10 = _district_cumulative(cmid)
                note = (f"The {len(parsed)} most Muslim-populous districts (of "
                        f"{TOTAL_DISTRICTS_2011}) are home to {_round_str(conc, 1)}% of all "
                        f"Indian Muslims; the top 10 alone hold {_round_str(top10, 1)}%.")
                block = f'<p>{html.escape(note)}</p>{_top100_districts_inner(cmid)}'
            else:
                block = ""
        else:
            block = ""
        if not block:
            continue
        inner = re.sub(r'^<details\b[^>]*>\s*<summary>.*?</summary>', '', block, flags=re.S)
        inner = re.sub(r'</details>\s*$', '', inner)
        sub = f'<span class="breakdown-sub">{html.escape(v["sub"])}</span>' if v.get("sub") else ""
        parts.append(f'<section class="breakdown"><h2>{html.escape(v["label"])}{sub}</h2>{inner}</section>')
    return "".join(parts)


def _related_metrics(m: dict) -> list:
    """(id, name) of other carded metrics in the same display section."""
    section = SECTION_OF.get(m["cluster"], m["cluster"])
    return [(x["id"], x.get("name", x["id"])) for x in _carded_metrics()
            if SECTION_OF.get(x["cluster"], x["cluster"]) == section and x["id"] != m["id"]]


def _breadcrumb_html(m: dict) -> str:
    section = SECTION_OF.get(m["cluster"], m["cluster"].capitalize())
    name = m.get("name", m["id"])
    return (f'<a href="/">Home</a> › <span>{html.escape(section)}</span> › '
            f'<span aria-current="page">{html.escape(name)}</span>')


def _breadcrumb_jsonld(m: dict) -> str:
    name = m.get("name", m["id"])
    obj = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "muslimdata.in", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": name, "item": f"{SITE_URL}/m/{m['id']}/"},
        ],
    }
    return '<script type="application/ld+json">\n' + json.dumps(obj, indent=2, ensure_ascii=False) + "\n</script>"


def _emit_metric_landings(out_dir: pathlib.Path, view_map: dict | None = None) -> int:
    """Write a full, self-canonical landing page at /m/{mid}/index.html per
    carded metric. Returns the count written."""
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        data = _yaml.safe_load(f)
    view_map = view_map or {}
    timestamp = dt.datetime.now().strftime("%-d %B %Y")
    stubs_root = out_dir / "m"
    stubs_root.mkdir(parents=True, exist_ok=True)
    written = 0
    for m in data["metrics"]:
        disp = m.get("display", {}).get("scorecard")
        if not disp or disp.get("include", True) is False:
            continue
        mid = m["id"]
        name = m.get("name", disp.get("label", mid))
        unit = disp["unit_format"]
        payload = _og_data_for_metric(m) or {}
        plain = PLAIN_DEFINITION.get(mid, "")
        defn = " ".join((METRIC_META.get(mid, {}).get("definition") or "").split())
        notes = " ".join((METRIC_META.get(mid, {}).get("methodology_notes") or "").split())
        yr = payload.get("year", "")

        polarity_html = ""
        if payload.get("polarity") == "Higher is better":
            polarity_html = '<p class="polarity"><span aria-hidden="true">↑</span> higher is better</p>'
        elif payload.get("polarity") == "Lower is better":
            polarity_html = '<p class="polarity"><span aria-hidden="true">↓</span> lower is better</p>'

        compare_html = ""
        if payload.get("comp_label") and payload.get("comp_value"):
            cls = payload.get("comp_class", "mid")
            compare_html = (f'<p class="compare">{html.escape(payload["comp_label"])}: '
                            f'<b class="{cls}">{html.escape(payload["comp_value"])}</b></p>')

        views = view_map.get(mid, [])
        bk_names = _and_join([v["label"].replace("By ", "").lower() for v in views]) if views else ""
        cta_label = ("Explore the interactive chart"
                     + (f", with breakdowns by {bk_names}" if bk_names else "") + " →")

        nt = _landing_national_table(mid, unit)
        national_html = (f'<h2>Latest figures by community{(" (" + str(yr) + ")") if yr else ""}</h2>{nt}'
                         if nt else "")
        breakdowns_html = _landing_breakdowns(m, views)

        about_parts = []
        if defn:
            about_parts.append(f'<p><b>Definition.</b> {html.escape(defn)}</p>')
        if notes:
            about_parts.append(f'<p><b>Methodology.</b> {html.escape(notes)}</p>')
        docs = _source_documents(mid)
        if docs:
            links = " · ".join(
                f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(l)}</a>'
                for _, l, u in docs)
            about_parts.append(f'<p class="src-note"><b>Sources.</b> {links}. '
                               f'Data file: <a href="/canonical/{mid}.csv">{mid}.csv</a>.</p>')
        else:
            about_parts.append(f'<p class="src-note">Data file: '
                               f'<a href="/canonical/{mid}.csv">{mid}.csv</a>.</p>')
        about_html = "".join(about_parts)

        rel = _related_metrics(m)
        related_html = ""
        if rel:
            lis = "".join(f'<li><a href="/m/{rid}/">{html.escape(rname)}</a></li>'
                          for rid, rname in rel)
            related_html = f'<h2>Related indicators</h2><ul class="related">{lis}</ul>'

        description = (f"{name} for India's Muslims, with Hindu and all-India comparison baselines. "
                       + (defn[:180] if defn else ""))
        if len(description) > 240:
            description = description[:237].rstrip() + "..."

        jsonld = _dataset_jsonld(m) + "\n" + _breadcrumb_jsonld(m)
        subs = {
            "{title}": html.escape(f"{name}: muslimdata.in"),
            "{description}": html.escape(description),
            "{canonical}": f"{SITE_URL}/m/{mid}/",
            "{og_title}": html.escape(name),
            "{og_image}": f"{SITE_URL}/og/{mid}.png",
            "{og_image_alt}": html.escape(
                f"{name}: Indian Muslims vs Hindu and all-India baselines on muslimdata.in"),
            "{breadcrumb}": _breadcrumb_html(m),
            "{h1}": html.escape(name),
            "{lede}": html.escape(plain or (defn[:160] if defn else "")),
            "{hero_value}": html.escape(payload.get("hero", "n/a")),
            "{hero_unit}": html.escape(payload.get("caption", "")),
            "{hero_year}": f"({html.escape(str(yr))})" if yr else "",
            "{polarity_html}": polarity_html,
            "{compare_html}": compare_html,
            "{mid}": mid,
            "{cta_label}": html.escape(cta_label),
            "{national_html}": national_html,
            "{breakdowns_html}": breakdowns_html,
            "{about_html}": about_html,
            "{related_html}": related_html,
            "{timestamp}": timestamp,
        }
        page = LANDING_TEMPLATE
        for k, v in subs.items():
            page = page.replace(k, v)
        page = page.replace("{jsonld}", jsonld)
        d = stubs_root / mid
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page)
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
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#fafaf7">
<meta property="og:title" content="About muslimdata.in">
<meta property="og:description" content="A scorecard of living-conditions indicators for India's Muslim population, with Hindu and all-India comparison baselines on every metric.">
<meta property="og:url" content="{site_url}/about/">
<meta property="og:type" content="article">
<meta property="og:image" content="{site_url}/og/default.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="muslimdata.in: the state of Muslim India, in data. {n_metrics} indicators with Hindu and all-India comparison baselines.">
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
  </nav>
  <p class="masthead-meta">Last updated {timestamp}</p>
</div>

<h1>About muslimdata.in</h1>
<p class="lede">A scorecard of living-conditions indicators for India's Muslim
population, with Hindu and all-India comparison baselines on every metric.</p>

<h2>Why this exists</h2>
<p>The Sachar Committee report (2006) remains one of India's most-cited
assessments of Muslim socio-economic status. Nearly two decades later, few
public resources keep that lens current: the data exists, scattered across the
Census of India, NCRB, NFHS, AISHE, PLFS, and other primary sources, but it
is not assembled in one place, with comparison baselines, in a form that a
non-specialist can read.</p>
<p>muslimdata.in is an attempt at that single place. Every number is sourced
from a primary public dataset, traced back to its original file, and shown
alongside the Hindu and all-India comparison so the reader can judge the gap
without having to compute it.</p>

<h2>What's on the dashboard</h2>
<p>{n_metrics} indicators across six themes (population, health, education,
employment, representation, justice), drawn from {n_sources}
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
official totals. Civil-society compilations report substantially higher counts.</li>
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


# ----- SEO / AI-discoverability (patterns adopted from sibling hawaiidashboard.org) -----
# Machine-readable structured data (schema.org Dataset per metric -> Google
# Dataset Search + AI answer engines), an llms.txt site summary, and a sitemap
# with real <lastmod> taken from git (so the build stays byte-stable between
# rebuilds — unlike a now()-stamped date).

def _carded_metrics() -> list[dict]:
    """Metrics with a scorecard display block (the ones actually rendered)."""
    import yaml as _yaml
    with (REPO_ROOT / "manifest" / "metrics.yaml").open() as f:
        data = _yaml.safe_load(f)
    return [
        m for m in data["metrics"]
        if (d := m.get("display", {}).get("scorecard")) and d.get("include", True) is not False
    ]


def _metric_coverage(mid: str):
    """(sorted distinct years, set of geography_levels) from the canonical CSV."""
    rows = load_metric(mid, sex=None)
    years = sorted({int(r["year"]) for r in rows if str(r.get("year", "")).strip().isdigit()})
    geos = {r.get("geography_level", "").strip() for r in rows if r.get("geography_level")}
    return years, geos


def _git_last_date(rel_path: str) -> str:
    """Last git commit date (YYYY-MM-DD) for a repo-relative path, for sitemap
    <lastmod>. Git-derived (deterministic given repo state) so the generated
    sitemap stays byte-stable between rebuilds; '' if git is unavailable."""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", rel_path],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _dataset_jsonld(m: dict) -> str:
    """schema.org Dataset block for a metric stub page. Brace-heavy JSON, so
    callers must inject it via str.replace(), never str.format()."""
    mid = m["id"]
    name = m.get("name", mid)
    defn = " ".join((m.get("definition") or "").split())
    desc = defn or f"{name} for India's Muslim population, with Hindu and all-India comparison baselines."
    years, _geos = _metric_coverage(mid)
    src = (m.get("sources") or {}).get("primary", "")
    obj = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f"{name}: India, by religion",
        "description": desc[:4900],
        "url": f"{SITE_URL}/m/{mid}/",
        "license": "https://github.com/iqbash1/indian-muslims-dashboard",
        "isAccessibleForFree": True,
        "creator": {"@type": "Organization", "name": "muslimdata.in", "url": SITE_URL},
        "publisher": {"@type": "Organization", "name": "muslimdata.in", "url": SITE_URL},
        "spatialCoverage": {"@type": "Place", "name": "India"},
        "variableMeasured": name,
        "keywords": [k for k in ["India", "Indian Muslims", "religion", m.get("cluster", ""), name] if k],
        "distribution": [{
            "@type": "DataDownload",
            "encodingFormat": "text/csv",
            "contentUrl": f"{SITE_URL}/canonical/{mid}.csv",
        }],
    }
    if years:
        obj["temporalCoverage"] = f"{years[0]}/{years[-1]}" if years[0] != years[-1] else str(years[0])
    if src:
        obj["measurementTechnique"] = f"Extracted from the published {src} source; provenance at {SITE_URL}/m/{mid}/."
    return '<script type="application/ld+json">\n' + json.dumps(obj, indent=2, ensure_ascii=False) + "\n</script>"


def _home_jsonld() -> str:
    """Organization + WebSite + ItemList for the home page; the ItemList lets
    search engines discover every metric page from the root."""
    items = [
        {"@type": "ListItem", "position": i + 1, "url": f"{SITE_URL}/m/{m['id']}/", "name": m.get("name", m["id"])}
        for i, m in enumerate(_carded_metrics())
    ]
    obj = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Organization", "@id": f"{SITE_URL}/#org", "name": "muslimdata.in",
             "url": SITE_URL, "description": SITE_DESCRIPTION},
            {"@type": "WebSite", "@id": f"{SITE_URL}/#website", "name": SITE_TITLE, "url": SITE_URL,
             "description": SITE_DESCRIPTION, "publisher": {"@id": f"{SITE_URL}/#org"}},
            {"@type": "ItemList", "name": "Living-conditions indicators for India's Muslims",
             "itemListElement": items},
        ],
    }
    return '<script type="application/ld+json">\n' + json.dumps(obj, indent=2, ensure_ascii=False) + "\n</script>"


def _emit_llms_txt(out_dir: pathlib.Path) -> None:
    """Plain-text site summary for AI/LLM crawlers (llms.txt convention) so
    answer engines describe the dashboard and cite the right per-metric CSVs."""
    L = [
        "# muslimdata.in", "",
        f"> {SITE_DESCRIPTION}", "",
        "muslimdata.in is a static, source-traceable dashboard of living-conditions "
        "indicators for India's Muslim population, with Hindu and all-India comparison "
        "baselines on every metric. It is modelled on the Hawaii state dashboard pattern. "
        "Every value traces to a primary government source (Census of India, NFHS, PLFS, "
        "NCRB, AISHE, Sachar Committee) with the original file archived and checksummed.",
        "",
        "## Reading the data",
        "- Each metric has a page at /m/{id}/ and a machine-readable CSV at /canonical/{id}.csv "
        "(CORS-enabled). CSV columns: metric_id, geography_level, geography_code, year, religion, "
        "value, denominator, source_id, source_document, methodology_note.",
        "- Comparisons are Muslim vs Hindu vs all-India; each metric shows the year its data is current to.",
        "- The 2021 Census is delayed, so demographic metrics are 2011 or earlier.",
        "",
        "## Metrics",
    ]
    for m in _carded_metrics():
        mid, name = m["id"], m.get("name", m["id"])
        years, _ = _metric_coverage(mid)
        span = f"{years[0]}-{years[-1]}" if years and years[0] != years[-1] else (str(years[0]) if years else "n/a")
        src = (m.get("sources") or {}).get("primary", "")
        L.append(f"- {name} ({span}{'; source: ' + src if src else ''}): "
                 f"{SITE_URL}/m/{mid}/ | data: {SITE_URL}/canonical/{mid}.csv")
    L += ["", "## Pages",
          f"- Home: {SITE_URL}/",
          f"- About and methodology: {SITE_URL}/about/",
          f"- Per-source methodology runbooks: {SITE_URL}/runbooks/"]
    (out_dir / "llms.txt").write_text("\n".join(L) + "\n")


def _emit_sitemap(out_dir: pathlib.Path) -> None:
    """sitemap.xml of home + About + every per-metric page, with <lastmod> from
    git (a metric page is as fresh as its canonical CSV's last commit). Replaces
    the previously hand-maintained, lastmod-less file."""
    build_date = _git_last_date("dashboard/build.py")
    entries = [
        (f"{SITE_URL}/", build_date, "weekly", "1.0"),
        (f"{SITE_URL}/about/", build_date, "monthly", "0.5"),
    ]
    for m in _carded_metrics():
        mid = m["id"]
        entries.append((f"{SITE_URL}/m/{mid}/", _git_last_date(f"canonical/{mid}.csv"), "monthly", "0.8"))
    P = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, cf, pr in entries:
        P.append("  <url>")
        P.append(f"    <loc>{loc}</loc>")
        if lastmod:
            P.append(f"    <lastmod>{lastmod}</lastmod>")
        P.append(f"    <changefreq>{cf}</changefreq>")
        P.append(f"    <priority>{pr}</priority>")
        P.append("  </url>")
    P.append("</urlset>")
    (out_dir / "sitemap.xml").write_text("\n".join(P) + "\n")


def build() -> None:
    # Status-bar counts derived from canonical (SSOT — never goes stale).
    n_metrics = len(SCORECARD_SPEC)
    n_rows, source_ids = 0, set()
    for cpath in sorted(CANONICAL_DIR.glob("*.csv")):
        with cpath.open() as f:
            for row in csv.DictReader(f):
                if row.get("source_id"):
                    source_ids.add(row["source_id"])
                # Count the both-sexes aggregate only, so the headline data-point
                # count keeps meaning "one per geo x year x religion" once
                # gender (male/female) rows exist for some metrics.
                if row.get("sex", "all") == "all":
                    n_rows += 1
    n_sources = len(source_ids)

    cluster_grids, card_charts, view_map = render_all_clusters()

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
        f" They run ahead on a handful ({top_ahead_joined})."
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
        "{home_jsonld}": _home_jsonld(),
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

    # Per-metric district-level downloads (district rows only, names resolved):
    # too granular for on-screen, offered as a CSV. See _district_download_link.
    _emit_district_downloads(OUT_PATH.parent)

    # Emit docs/js/analytics.js from the template, substituting GA4 + Clarity
    # IDs. Treated as build output (regenerated each build), like index.html.
    analytics_src = REPO_ROOT / "dashboard" / "analytics.template.js"
    analytics_out = OUT_PATH.parent / "js" / "analytics.js"
    analytics_out.parent.mkdir(parents=True, exist_ok=True)
    js_text = analytics_src.read_text()
    js_text = js_text.replace("__GA4_ID__", GA4_ID).replace("__CLARITY_ID__", CLARITY_ID)
    analytics_out.write_text(js_text)

    # Emit 1200x630 OG cards: /og/{mid}.png per metric plus /og/{mid}-{view}.png
    # for each modal view (by-state / by-sex / by-district), referenced by the
    # stub pages below, and a /og/default.png used by the homepage + About.
    _emit_og_images(OUT_PATH.parent, view_map)

    # Emit the full, indexable landing page per metric at /m/{mid}/index.html
    # (hero, data tables, methodology, sources, related links, JSON-LD), then the
    # per-view redirect stubs at /m/{mid}/{view}/index.html (own OG meta, redirect
    # into the #{mid}/{view} modal tab, canonical -> the landing page).
    _emit_metric_landings(OUT_PATH.parent, view_map)
    _emit_metric_stubs(OUT_PATH.parent, view_map)

    # Emit the About page at /about/index.html.
    _emit_about_page(OUT_PATH.parent, substitutions["{timestamp}"])

    # SEO / AI-discoverability: llms.txt summary + sitemap with git-dated lastmod.
    _emit_llms_txt(OUT_PATH.parent)
    _emit_sitemap(OUT_PATH.parent)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html_out)
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} ({len(html_out):,} bytes)")
    print(f"wrote {analytics_out.relative_to(REPO_ROOT)} ({len(js_text):,} bytes)")
    print("wrote docs/llms.txt + docs/sitemap.xml (SEO / AI discoverability)")


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

NAMED_COMMUNITIES = ("hindu", "muslim", "christian", "sikh", "buddhist", "jain", "other_minority")


def _comparison_series(series: dict, years: list[int]):
    """Return (values, label, pill_label) for the dashed comparison line.

    Prefers the source-published "all" aggregate when it's populated across
    every year in the trend; otherwise falls back to the per-year median of
    available community values so the Muslim line always has a benchmark.
    The fallback line is labelled "All communities" (it is the per-year median
    across the named communities); the label avoids claiming "All-India" when
    the benchmark is community-level rather than the official aggregate."""
    import statistics as _stats
    source_all = [series.get("all", {}).get(y) for y in years]
    if source_all and all(v is not None for v in source_all):
        return source_all, "All communities", "vs all communities"
    community_keys = [c for c in NAMED_COMMUNITIES if c in series]
    if not community_keys:
        return None, None, None
    values = []
    for y in years:
        vals = [series[c].get(y) for c in community_keys if series[c].get(y) is not None]
        values.append(_stats.median(vals) if vals else None)
    if not any(v is not None for v in values):
        return None, None, None
    return values, "All communities", "vs all communities"
COMMUNITY_LABEL = {
    "hindu": "Hindu", "muslim": "Muslim", "christian": "Christian",
    "sikh": "Sikh", "buddhist": "Buddhist", "jain": "Jain",
    "all": "All", "other": "Other", "other_minority": "Other minorities",
}
# `tier` (good/mid/bad from community_rank) now drives only TEXT colour, via the
# .card-comp CSS classes; chart bars no longer recolour by tier (colour contract:
# the Muslim series is always maroon). No tier->bar palette is needed.


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
    "mpce": "spent per person each month",
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
    "inr_per_month": ("", 0),
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
    "sachar-committee-2006": "Sachar Committee (NSS 2004-05)",
}


def _verdict(gap: float, hib) -> str:
    """good / bad / neutral for a Muslim-minus-reference gap given polarity."""
    if hib is None or gap == 0:
        return "neutral"
    return "good" if ((gap > 0) if hib else (gap < 0)) else "bad"


def _gap_str(gap: float, unit: str) -> str:
    if unit == "count":
        return f"{'+' if gap >= 0 else '-'}{abs(int(gap)):,}"
    if unit in ("inr_per_month", "inr_per_year", "inr"):
        return f"{'+' if gap >= 0 else '-'}Rs {abs(int(gap)):,}"
    sign = "+" if gap >= 0 else ""
    return f"{sign}{_round_str(gap, _disp_dp(unit))}{'pp' if unit == 'percent' else ''}"


def _verdict_word(cls: str, gap: float | None = None) -> str:
    # Good/bad metrics read as ahead/behind. For neutral-polarity metrics (no
    # inherent better/worse, e.g. urban share) a flat "even" misreads when there
    # is a real gap, so name the direction Muslim sits instead.
    if cls == "neutral":
        if gap is None or gap == 0:
            return "even"
        return "higher" if gap > 0 else "lower"
    return {"good": "ahead", "bad": "behind"}[cls]


def _tier_word(tier: str) -> str:
    return {"good": "top tier", "mid": "middle tier", "bad": "bottom tier"}[tier]


def _year_of(metric_id: str):
    yrs = [int(r["year"]) for r in load_metric(metric_id) if r["geography_level"] == "national"]
    return max(yrs) if yrs else ""


def _comp(label: str, verdict: str, detail: str, cls: str, comp_type: str | None = None, fallback: bool = False) -> str:
    attr = f' data-comp-type="{comp_type}"' if comp_type else ""
    attr += ' data-comp-fallback' if fallback else ""
    return (f'<div class="card-comp {cls}"{attr}><div class="comp-label">{html.escape(label)}</div>'
            f'<div class="comp-verdict">{html.escape(verdict)}</div>'
            f'<div class="comp-detail">{html.escape(detail)}</div></div>')


PLAIN_DEFINITION = {
    "pop-share": "How much of India's population is Muslim, by the latest census.",
    "urban-share": "What share of each community lives in towns and cities rather than villages.",
    "sex-ratio": "Higher means more women relative to men; a low value signals a gender imbalance favouring males.",
    "district-concentration-top100": "How geographically concentrated India's Muslims are, measured by the share living in their 100 most-populous districts.",
    "lit-7plus": "Of people aged 7 and older, what share can read and write. The Census uses 7+ as the standard cutoff to exclude very young children.",
    "ger-higher-ed": "Of every 100 young people in the typical college-going age band (18 to 23), how many are enrolled in higher education (any degree or diploma course after Class 12).",
    "muslim-higher-ed-enrolment": "Total number of Muslim students enrolled in higher education across India in the latest year.",
    "lfpr-15plus": "Of people aged 15 and older, what share is in the workforce, either working or actively looking for work.",
    "wpr-15plus": "Of people aged 15 and older, what share is currently working.",
    "salaried-share": "Of all workers, what share has regular salaried jobs (as opposed to self-employment or casual labour).",
    "imr": "Of every 1,000 babies born, how many die before their first birthday.",
    "stunting-u5": "Of children under 5, what share is too short for their age, a long-term sign of chronic undernutrition.",
    "inst-delivery": "Of recent live births, what share took place at a hospital or health facility rather than at home.",
    "women-anemia": "Of women in childbearing age (15 to 49), what share has anaemia (low haemoglobin).",
    "improved-sanitation": "What share of households has a toilet of any type.",
    "mpce": "How much a typical person in a community spends in a month, on food, rent, fuel, clothes and everything else. In India this is the usual way to measure how well-off people are, because reliable income data does not exist.",
    "ls-share": "Of the 543 seats in India's national parliament (Lok Sabha), what share is held by Muslim MPs.",
    "mla-share": "Across all 31 state and UT legislative assemblies that hold elections, what share of MLA seats is held by Muslims.",
    "prison-rate-per-100k": "For every 100,000 people of a religion, how many are in prison. Allows fair comparison across communities of different size.",
    "undertrial-rate-per-100k": "For every 100,000 people of a religion, how many are in prison awaiting trial (not yet convicted).",
    "communal-incidents-govt": "Number of communal or religious rioting incidents recorded in police records each year (NCRB).",
    "communal-incidents-civic": "In-person events (rallies, religious gatherings, political speeches) where Muslims are targeted with hateful rhetoric.",
}


_SOURCES_REG = None
def _sources_registry():
    """source_id -> source dict (name, home_url, publisher) from sources.yaml."""
    global _SOURCES_REG
    if _SOURCES_REG is None:
        import yaml as _yaml
        with (REPO_ROOT / "manifest" / "sources.yaml").open() as fh:
            data = _yaml.safe_load(fh)
        _SOURCES_REG = {s["id"]: s for s in data.get("sources", [])}
    return _SOURCES_REG


def _source_documents(mid):
    """Original source documents behind a metric's chart, so a reader can open
    the primary source and recreate the numbers. Each canonical row names its
    source_document (the archived L1 file); we resolve that to the real weblink
    via the file's .meta.json sidecar (which also holds the SHA256). Where the
    provenance is a templated per-state Census path or a manual compilation
    (no single file), we fall back to the source's home page. Returns
    [(source_id, label, url)], primary source first, deduped by url."""
    f = CANONICAL_DIR / f"{mid}.csv"
    if not f.exists():
        return []
    reg = _sources_registry()
    primary = (METRIC_META.get(mid, {}).get("sources") or {}).get("primary")
    found = []  # (source_id, label, url, is_fallback)
    seen_docs = set()
    with f.open() as fh:
        for r in csv.DictReader(fh):
            doc = (r.get("source_document") or "").strip()
            sid = (r.get("source_id") or "").strip()
            if not doc or doc in seen_docs:
                continue
            seen_docs.add(doc)
            url, fallback = "", False
            sidecar = REPO_ROOT / (doc + ".meta.json")
            if sidecar.exists():
                try:
                    url = (json.load(sidecar.open()) or {}).get("url", "") or ""
                except Exception:
                    url = ""
            if not url:  # templated (<state>) path or manual compilation
                url = (reg.get(sid, {}) or {}).get("home_url", "") or ""
                fallback = True
            if not url:
                continue
            label = SOURCE_LABEL.get(sid) or (reg.get(sid, {}) or {}).get("name") or sid
            found.append((sid, label, url, fallback))
    # Drop a source's home-page fallback if it also has a real document.
    real_sids = {sid for sid, _, _, fb in found if not fb}
    found = [t for t in found if not (t[3] and t[0] in real_sids)]
    # Dedupe by url; primary source first, otherwise canonical order.
    out, seen_urls = [], set()
    for sid, label, url, _ in sorted(found, key=lambda t: (t[0] != primary,)):
        if url in seen_urls:
            continue
        seen_urls.add(url)
        out.append((sid, label, url))
    return out


def _extract_views(html_str: str) -> list[dict]:
    """Parse the drill-down `<details data-view-id=... data-view-label=...
    data-view-sub=...>` tags out of a card's HTML, in document (= tab) order.
    Single source of truth for both the card-face hint AND the per-view stub /
    OG generation, so they never drift from what the card actually renders."""
    out: list[dict] = []
    for tag in re.findall(r"<details\b[^>]*>", html_str):
        if "data-view-id" not in tag:
            continue
        def attr(name: str) -> str:
            m = re.search(name + r'="([^"]*)"', tag)
            return m.group(1) if m else ""
        out.append({"id": attr("data-view-id"),
                    "label": attr("data-view-label"),
                    "sub": attr("data-view-sub")})
    return out


def _card_shell(mid, label, value, unit_txt, year, polarity, chart_html, comps_html,
                src, csv_href, details_html="", download_html="") -> str:
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
    expand_html = '<span class="card-expand" aria-hidden="true" title="Open for the full chart and method">↗</span>'

    # "About this measurement" block: visible only when the card is cloned
    # into the modal (display:none on the card grid via CSS). Pulls the
    # technical definition and methodology notes from manifest/metrics.yaml
    # so the modal has the full provenance + caveats without crowding the
    # card.
    meta = METRIC_META.get(mid, {})
    method_html = ""
    # Original source documents (the actual report/table weblinks) so a reader
    # can open the primary source and recreate the chart. Listed in the modal
    # panel; the footer links the primary one.
    docs = _source_documents(mid)
    # Collapse the YAML block-scalar hard-wraps to single spaces so the prose
    # reflows to the modal width instead of breaking at the source line ends.
    def_text = " ".join((meta.get("definition") or "").split())
    notes_text = " ".join((meta.get("methodology_notes") or "").split())
    if def_text or notes_text or docs:
        parts = []
        if def_text:
            parts.append(f'<p><b>Definition.</b> {html.escape(def_text)}</p>')
        if notes_text:
            parts.append(f'<p><b>Methodology.</b> {html.escape(notes_text)}</p>')
        if docs:
            doc_links = " · ".join(
                f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(l)}</a>'
                for _, l, u in docs)
            parts.append(
                '<p class="card-sources"><b>Where this data comes from.</b> '
                f'{doc_links}. Data file: '
                f'<a href="{html.escape(csv_href)}" target="_blank" rel="noopener">{html.escape(mid)}.csv</a>. '
                'You can open any of these to check the numbers on this chart '
                'yourself.</p>')
        ts = _transform_script(mid)
        if ts:
            parts.append(
                '<p class="card-reproduce"><b>Reproduce this.</b> Every figure on this '
                'card, in every tab, is computed from the data file above by an open '
                f'script: <a href="{GITHUB_REPO}/blob/main/{html.escape(ts)}" '
                'target="_blank" rel="noopener">transform code</a>. Each data-file row '
                'also records its own source and method.</p>')
        method_html = (
            '<div class="card-method">'
            '<h3 class="card-method-title">About this measurement</h3>'
            + "".join(parts) +
            '</div>'
        )
    # Footer: the source NAME links to the original source document; "Data file"
    # opens the CSV extract. Primary source first (docs is primary-sorted).
    primary_url = docs[0][2] if docs else ""
    src_foot = (f'<a href="{html.escape(primary_url)}" target="_blank" rel="noopener">{html.escape(src)}</a>'
                if primary_url else f'<span class="src-name">{html.escape(src)}</span>')

    # The metric's extra "views" (state / sex / district drill-downs) ride
    # along in the card DOM inside a hidden .card-views block; the modal JS
    # lifts each into its own tab (see modalSetup). On the card face we render
    # only a minimal one-line hint listing the view names so the homepage stays
    # uncluttered. Each view's tab label is carried in data-view-label= on its
    # <details>; the hint's data-view-id matches the modal tab's data-view, so a
    # hint click opens that exact tab (and its shareable /m/{mid}/{view}/ URL).
    views_html = f'<div class="card-views">{details_html}</div>' if details_html else ""
    hint_html = ""
    metric_views = _extract_views(details_html)
    if metric_views:
        links = " · ".join(
            f'<button type="button" class="card-view-link" data-view-id="{html.escape(v["id"])}">{html.escape(v["label"])}</button>'
            for v in metric_views)
        hint_html = (f'<div class="card-views-hint">More views: {links} '
                     f'<span aria-hidden="true">↗</span></div>')

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
        f'{download_html}'
        f'{views_html}'
        f'{hint_html}'
        # Footer: source NAME links to the original source document; a separate
        # "Data file" link opens the CSV extract. Full source list (every
        # document) is in the modal "About this measurement" panel.
        f'<div class="card-foot">'
        f'{src_foot}'
        f'<a href="{html.escape(csv_href)}" target="_blank" rel="noopener">Data file</a>'
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
        points.append([rank, _round_dp(share, 1)])
        if rank == 10:
            top10 = share
    return points, top10


def _top100_districts_inner(metric_id: str) -> str:
    """Sortable, scrollable # | District (ST) | Muslims | % of district table for
    the top-ranked districts (NO <details>/<summary> wrapper, so it can be
    composed into the pop-share by-district view + the landing page). Each
    numeric cell carries a `data-sort` raw value so the client sort is correct
    (text like "4.71M" / "501k" would sort wrong by string). '' if no rows."""
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
            f'<td style="text-align:right;font-feature-settings:&quot;tnum&quot;" data-sort="{pct:.4f}">{_round_str(pct, 1)}%</td>'
            f"</tr>"
        )
    return (
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
        f'</div>'
    )


def _concentration_view(curve_cvid: str, download_html: str = ""):
    """pop-share's "By district" tab: the geographic-concentration story folded
    in from the former district-concentration card (Commit DV). Returns
    (details_html, curve_js). Reads the district-concentration-top100 canonical
    (top-100 ranking + national concentration figure) regardless of host card."""
    cmid = "district-concentration-top100"
    conc = _nat_by_religion(cmid).get("muslim")
    parsed = _parse_district_rows(cmid)
    if conc is None or not parsed:
        return "", None
    n = len(parsed)
    points, top10 = _district_cumulative(cmid)
    note = (f"India had {TOTAL_DISTRICTS_2011} districts in 2011, yet the {n} most "
            f"Muslim-populous, just {_round_str(n / TOTAL_DISTRICTS_2011 * 100, 1)}% of them, are "
            f"home to {_round_str(conc, 1)}% of all Indian Muslims, and the top 10 alone hold "
            f"{_round_str(top10, 1)}%. This is a geographic-concentration measure, not a "
            f"community comparison.")
    curve_html = (f'<div class="card-chartwrap" style="height:200px"><canvas id="{curve_cvid}" '
                  f'role="img" aria-label="Cumulative share of India\'s Muslim population held by '
                  f'the top-ranked districts; values listed in the table below."></canvas></div>')
    curve_js = f'concentrationCurve("{curve_cvid}", {json.dumps(points)}, 10, "%");'
    view = (f'<details data-view-id="by-district" data-view-label="By district" '
            f'data-view-sub="top {n} of {TOTAL_DISTRICTS_2011}">'
            f'<summary>Geographic concentration (top {n} districts)</summary>'
            f'<p class="comp-note">{html.escape(note)}</p>'
            f'{curve_html}'
            f'{_top100_districts_inner(cmid)}'
            f'{download_html}'
            f'{_view_provenance(cmid)}'
            f'</details>')
    return view, curve_js


GITHUB_REPO = "https://github.com/iqbash1/indian-muslims-dashboard"

_TRANSFORM_SCRIPT_CACHE: dict[str, str | None] = {}


def _transform_script(mid: str) -> str | None:
    """Repo-relative path of the canonicalise script that produced a metric, for
    the 'reproduce this' links. Most live at transform/canonicalize/<id>.py."""
    if mid in _TRANSFORM_SCRIPT_CACHE:
        return _TRANSFORM_SCRIPT_CACHE[mid]
    stem = mid.replace("-", "_")
    cand = REPO_ROOT / "transform" / "canonicalize" / f"{stem}.py"
    out: str | None = None
    if cand.exists():
        out = cand.relative_to(REPO_ROOT).as_posix()
    else:
        for p in sorted((REPO_ROOT / "transform").rglob("*.py")):
            if stem in p.stem:
                out = p.relative_to(REPO_ROOT).as_posix()
                break
    _TRANSFORM_SCRIPT_CACHE[mid] = out
    return out


def _view_provenance(mid: str) -> str:
    """A compact 'reproduce this view' caption appended to every modal view tab:
    the primary source(s), the downloadable canonical rows, and the open transform
    code that computed them, so each view stands alone for an independent
    researcher."""
    docs = _source_documents(mid)
    src = " · ".join(
        f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(l)}</a>'
        for _, l, u in docs) or "see methodology"
    bits = [f'<a href="canonical/{html.escape(mid)}.csv" download>data file</a>']
    ts = _transform_script(mid)
    if ts:
        bits.append(
            f'<a href="{GITHUB_REPO}/blob/main/{html.escape(ts)}" target="_blank" '
            f'rel="noopener">transform code</a>')
    return (f'<p class="view-provenance"><b>Reproduce this view.</b> Source: {src}. '
            f'Each value is computed from the {" · ".join(bits)}; every row records its '
            f'own source and method.</p>')


def _state_details(metric_id: str, unit: str, value_label: str | None = None) -> str:
    from collections import defaultdict
    rows = [r for r in load_metric(metric_id) if r["geography_level"] == "state"]
    if not rows:
        return ""
    # State data can carry several years (e.g. census 2001 + 2011) or a
    # different latest year per state (per-assembly election years). Take each
    # state's OWN latest year so a single table never mixes rounds.
    latest_year: dict[str, int] = defaultdict(int)
    for r in rows:
        y = int(r["year"])
        if y > latest_year[r["geography_code"]]:
            latest_year[r["geography_code"]] = y
    by_geo: dict[str, dict] = defaultdict(dict)
    years_used: set[int] = set()
    for r in rows:
        g = r["geography_code"]
        if int(r["year"]) != latest_year[g]:
            continue
        by_geo[g][r["religion"]] = float(r["value"])
        years_used.add(latest_year[g])
    if not by_geo:
        return ""
    # Featured (sortable) column: Muslim where the metric splits by religion;
    # otherwise the single series present (e.g. 'all' for incident counts not
    # broken out by religion). Muslim metrics sort lowest-first (the gap is the
    # story); count/all metrics sort highest-first (the biggest count is).
    if any("muslim" in v for v in by_geo.values()):
        feature, feat_label, reverse = "muslim", (value_label or "Muslim"), False
    else:
        keys = [k for v in by_geo.values() for k in v]
        feature = max(set(keys), key=keys.count) if keys else "all"
        feat_label, reverse = (value_label or feature.capitalize()), True
    # Hindu is shown as a static baseline only when Muslim is the subject, so the
    # table never reads as a Hindu-vs-Muslim ranking.
    has_hindu = feature == "muslim" and any("hindu" in v for v in by_geo.values())
    order = sorted(by_geo, key=lambda g: by_geo[g].get(feature, 0), reverse=reverse)
    # Sortable cells carry the raw value in data-sort so the handler
    # (setupSortableTables) orders by magnitude, not formatted string; missing
    # values sort low via a sentinel.
    def numcell(b: dict, rel: str, sortable: bool = True) -> str:
        if rel not in b:
            return '<td data-sort="-1">n/a</td>' if sortable else "<td>n/a</td>"
        val = fmt_num(b[rel], unit)
        return f'<td data-sort="{b[rel]:.4f}">{val}</td>' if sortable else f"<td>{val}</td>"

    head = ('<tr><th class="sortable" data-col="0">State / UT</th>'
            f'<th class="sortable" data-col="1" data-type="num">{html.escape(feat_label)}</th>'
            + ("<th>Hindu</th>" if has_hindu else "")
            + '</tr>')
    trs = []
    for g in order:
        b = by_geo[g]
        cells = f'<td>{html.escape(state_label(g))}</td>' + numcell(b, feature)
        if has_hindu:
            cells += numcell(b, "hindu", sortable=False)
        trs.append(f"<tr>{cells}</tr>")
    yr_txt = f", {next(iter(years_used))}" if len(years_used) == 1 else ""
    return (f'<details data-view-id="by-state" data-view-label="By state" data-view-sub="{len(order)} states{yr_txt}">'
            f'<summary>Full state data ({len(order)} states{yr_txt})</summary>'
            f'<table class="sortable-table"><thead>{head}</thead>'
            f'<tbody>{"".join(trs)}</tbody></table>{_view_provenance(metric_id)}</details>')


_DISTRICT_NAMES: dict[str, str] | None = None


def _district_names() -> dict[str, str]:
    """{district_code -> name} from the 2011 per-state Census C-01 files
    (area_name, 'District - ' prefix stripped). Codes are built exactly as
    pop_share's canonicalizer builds them (IN-S{sc}-D{dc}), so they line up with
    the canonical district rows. Cached after first call."""
    global _DISTRICT_NAMES
    if _DISTRICT_NAMES is not None:
        return _DISTRICT_NAMES
    names: dict[str, str] = {}
    cdir = REPO_ROOT / "extracted" / "census-2011"
    for fp in sorted(cdir.glob("c01-population-by-religion-*.csv")):
        with fp.open() as f:
            for row in csv.DictReader(f):
                if row.get("distt_code", "000") == "000":
                    continue  # state/national aggregate, not a district
                code = f'IN-S{row["state_code"]}-D{row["distt_code"]}'
                if code in names:
                    continue
                nm = (row.get("area_name") or "").strip()
                if nm.startswith("District - "):
                    nm = nm[len("District - "):].strip()
                names[code] = nm
    _DISTRICT_NAMES = names
    return names


def _metrics_with_district_download() -> list[str]:
    """Metrics whose canonical carries district rows, offered as a CSV download
    (too granular for on-screen). district-concentration is excluded — it already
    renders its 100 districts on the card."""
    out: list[str] = []
    for cpath in sorted(CANONICAL_DIR.glob("*.csv")):
        mid = cpath.stem
        if mid == "district-concentration-top100":
            continue
        with cpath.open() as f:
            if any(r["geography_level"] == "district" for r in csv.DictReader(f)):
                out.append(mid)
    return out


def _emit_district_downloads(out_dir: pathlib.Path) -> int:
    """Write docs/canonical/{mid}-districts.csv (district rows only, with state +
    district names resolved) for each download-eligible metric. Returns count."""
    names = _district_names()
    pub = out_dir / "canonical"
    pub.mkdir(parents=True, exist_ok=True)
    n_files = 0
    for mid in _metrics_with_district_download():
        rows = [r for r in load_metric(mid) if r["geography_level"] == "district"]
        if not rows:
            continue
        rows.sort(key=lambda r: r["geography_code"])
        with (pub / f"{mid}-districts.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["district_code", "state", "district", "year", "religion", "value", "source"])
            for r in rows:
                code = r["geography_code"]
                state = state_label("-".join(code.split("-")[:2]))
                w.writerow([code, state, names.get(code, ""), r["year"],
                            r["religion"], r["value"], r.get("source_id", "")])
        n_files += 1
    return n_files


def _district_download_link(mid: str) -> str:
    """Small download CTA for a metric's full district CSV (or '' if none)."""
    if mid == "district-concentration-top100":
        return ""
    n = sum(1 for r in load_metric(mid) if r["geography_level"] == "district")
    if not n:
        return ""
    return (f'<p class="card-download">'
            f'All {n} districts: '
            f'<a href="canonical/{html.escape(mid)}-districts.csv" download>download CSV</a></p>')


def _sex_details(metric_id: str, unit: str) -> str:
    """National male-vs-female drill-down for metrics that carry sex='male'/
    'female' rows; returns '' for metrics that don't (so it's safe to call on any
    card). Latest year; one row per community, Muslim first and 'All' last."""
    from collections import defaultdict
    rows = [r for r in load_metric(metric_id, sex=None)
            if r["geography_level"] == "national" and r["sex"] in ("male", "female")]
    if not rows:
        return ""
    latest = max(int(r["year"]) for r in rows)
    by_rel: dict[str, dict[str, float]] = defaultdict(dict)
    for r in rows:
        if int(r["year"]) == latest:
            by_rel[r["religion"]][r["sex"]] = float(r["value"])
    comms = [rel for rel, sx in by_rel.items() if "male" in sx and "female" in sx]
    if not comms:
        return ""
    # Muslim first (the subject), 'all' baseline last, others by female value.
    comms.sort(key=lambda rel: (rel != "muslim", rel == "all", by_rel[rel].get("female", 0.0)))

    def comm_label(rel: str) -> str:
        return "All communities" if rel == "all" else COMMUNITY_LABEL.get(rel, rel.capitalize())

    def cell(rel: str, sx: str) -> str:
        v = by_rel[rel].get(sx)
        if v is None:
            return '<td data-sort="-1">n/a</td>'
        return f'<td data-sort="{v:.4f}">{fmt_num(v, unit)}</td>'

    trs = "".join(
        f'<tr><td>{html.escape(comm_label(rel))}</td>{cell(rel, "male")}{cell(rel, "female")}</tr>'
        for rel in comms)
    head = ('<tr><th class="sortable" data-col="0">Community</th>'
            '<th class="sortable" data-col="1" data-type="num">Male</th>'
            '<th class="sortable" data-col="2" data-type="num">Female</th></tr>')
    return (f'<details data-view-id="by-sex" data-view-label="By sex" data-view-sub="{latest}">'
            f'<summary>By sex ({latest})</summary>'
            f'<table class="sortable-table"><thead>{head}</thead>'
            f'<tbody>{trs}</tbody></table>{_view_provenance(metric_id)}</details>')


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


def render_metric_card(m: dict):
    """Return (card_html, chart_js_or_None, views) for one live metric, where
    views is the list of drill-down view dicts ({id,label,sub}) in tab order."""
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
        card_html, js = _card_timeseries(mid, label, unit, src, csv_href, cvid)
    elif special == "time_series_count":
        card_html, js = _card_ts_count(mid, label, src, csv_href, cvid)
    elif mid in ("pop-share", "muslim-higher-ed-enrolment"):
        card_html, js = _card_muslim_only(mid, label, unit, src, csv_href, cvid)
    else:
        card_html, js = _card_comparison(mid, label, unit, hib, src, csv_href, cvid, suffix, dec)
    # Third element: this metric's drill-down views (id/label/sub), in tab order,
    # for the per-view stub + OG generators. Extracted from the rendered card so
    # it can never drift from what actually appears in the modal.
    return card_html, js, _extract_views(card_html)


def _ger_count_views() -> str:
    """Fold the decarded `muslim-higher-ed-enrolment` (absolute Muslim student
    counts) into the ger-higher-ed modal as "Students by state" + "Students by
    sex" tabs - the Commit-DV pattern (a satellite metric surfaced as host-card
    tabs, like district-concentration -> pop-share)."""
    cmid = "muslim-higher-ed-enrolment"
    total = _nat_by_religion(cmid).get("muslim")
    out = ""
    st = sorted(
        [(state_label(r["geography_code"]), int(float(r["value"])))
         for r in load_metric(cmid) if r["geography_level"] == "state"],
        key=lambda x: -x[1])
    if st:
        intro = (f'<p class="comp-note">{fmt_num(total, "count")} Muslim students were '
                 f'enrolled in higher education in 2021 (AISHE Muslim Minority total). '
                 f'AISHE tabulates only Muslim Minority enrolment, so there is no '
                 f'community ranking.</p>') if total else ""
        body = "".join(
            f'<tr><td>{html.escape(name)}</td>'
            f'<td data-sort="{v}">{fmt_num(v, "count")}</td></tr>' for name, v in st)
        head = ('<tr><th class="sortable" data-col="0">State / UT</th>'
                '<th class="sortable" data-col="1" data-type="num">Students</th></tr>')
        out += (f'<details data-view-id="students-by-state" data-view-label="Students by state" '
                f'data-view-sub="{len(st)} states, 2021">'
                f'<summary>Muslim students by state ({len(st)} states)</summary>'
                f'{intro}<table class="sortable-table"><thead>{head}</thead>'
                f'<tbody>{body}</tbody></table>{_view_provenance(cmid)}</details>')
    sx = {r["sex"]: int(float(r["value"]))
          for r in load_metric(cmid, sex=None)
          if r["geography_level"] == "national" and r["sex"] in ("male", "female")}
    if "male" in sx and "female" in sx:
        head = ('<tr><th class="sortable" data-col="0">Community</th>'
                '<th class="sortable" data-col="1" data-type="num">Male</th>'
                '<th class="sortable" data-col="2" data-type="num">Female</th></tr>')
        body = (f'<tr><td>Muslim</td>'
                f'<td data-sort="{sx["male"]}">{fmt_num(sx["male"], "count")}</td>'
                f'<td data-sort="{sx["female"]}">{fmt_num(sx["female"], "count")}</td></tr>')
        out += (f'<details data-view-id="students-by-sex" data-view-label="Students by sex" '
                f'data-view-sub="2021">'
                f'<summary>Muslim students by sex (2021)</summary>'
                f'<table class="sortable-table"><thead>{head}</thead>'
                f'<tbody>{body}</tbody></table>{_view_provenance(cmid)}</details>')
    return out


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
        all_series, all_line_label, all_pill_label = None, None, "vs all communities"
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
        base_label = all_pill_label or "vs all communities"
        comps += _comp(f"{base_label} · {fmt_num(all_v, unit)}",
                       _gap_str(gap, unit), _verdict_word(cls, gap), cls,
                       comp_type="vs-all", fallback=(hindu is None))
    other_min = nat.get("other_minority")
    if other_min is not None and muslim is not None:
        gap = muslim - other_min
        cls = _verdict(gap, hib)
        comps += _comp(f"vs other minorities · {fmt_num(other_min, unit)}",
                       _gap_str(gap, unit), _verdict_word(cls, gap), cls,
                       comp_type="vs-other-min")
    if hindu is not None:
        gap = muslim - hindu
        cls = _verdict(gap, hib)
        comps += _comp(f"vs Hindu · {fmt_num(hindu, unit)}",
                       _gap_str(gap, unit), _verdict_word(cls, gap), cls,
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
        series_map = {rel: [(_round_dp(v, _disp_dp(unit)) if (v := series.get(rel, {}).get(y)) is not None else None)
                            for y in years]
                      for rel in named if rel in series}
        # all_series was computed at the top of the function so the comp pill
        # and the chart's dashed line share the same comparator (source "all"
        # when populated; median across communities otherwise). Pass it as an
        # object so the chart's end-of-line label matches the pill label.
        chart_html = f'<div class="card-chartwrap" style="height:200px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
        all_arg = ({"values": [(_round_dp(v, _disp_dp(unit)) if v is not None else None) for v in all_series],
                    "label": all_line_label} if all_series else None)
        js = (f'trendChart("{cvid}", {json.dumps(years)}, {json.dumps(series_map)}, '
              f'{json.dumps(all_arg)}, {json.dumps(suffix)}, {dec}, {json.dumps(bool(has_break))});')
        # State + sex drill-downs become modal tabs (see _card_shell / modalSetup);
        # each returns "" for metrics that lack that breakdown, so the metric
        # simply gets fewer tabs.
        details = _state_details(mid, unit) + _sex_details(mid, unit)
    else:
        # SNAPSHOT card: latest-year community bar with All-India dashed baseline.
        # If we have a 2-point time series, surface the Muslim Δ as a comparison pill.
        if len(years) == 2 and "muslim" in series:
            mfirst = series["muslim"].get(years[0])
            mlast = series["muslim"].get(years[-1])
            if mfirst is not None and mlast is not None:
                delta = mlast - mfirst
                arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                comps += _comp(f"Since {years[0]}", f"{arrow} {_round_str(abs(delta), _disp_dp(unit))}{suffix}",
                               f"{_round_str(mfirst, _disp_dp(unit))}{suffix} → {_round_str(mlast, _disp_dp(unit))}{suffix}", "mid")
        pairs = [(COMMUNITY_LABEL[c], nat[c], c == "muslim") for c in named]
        if hib is not None:
            pairs.sort(key=lambda b: b[1], reverse=bool(hib))
        labels = [p[0] for p in pairs]
        values = [_round_dp(p[1], _disp_dp(unit)) for p in pairs]
        # Colour contract: the Muslim bar is ALWAYS the brand maroon (its series
        # identity); every other community is the muted grey. Whether Muslim sits
        # well or badly is carried by the verdict + tier TEXT (green/red), never by
        # recolouring the bar.
        colors = ["#7b1d22" if p[2] else "#D8DEE2" for p in pairs]
        # "All communities" is ALWAYS the dashed reference line, never a peer bar,
        # so the baseline reads identically on every card: the full community
        # ranking where the source has one, or a lone Muslim bar against the dashed
        # line where it does not (mpce / GER carry Muslim + All-India only). Skip
        # only when there is nothing to anchor against.
        if not pairs or (len(pairs) == 1 and all_v is None):
            chart_html = ""
            js = None
        else:
            h = len(pairs) * 28 + 28
            chart_html = f'<div class="card-chartwrap" style="height:{h}px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
            ref = json.dumps(_round_dp(all_v, _disp_dp(unit))) if all_v is not None else "null"
            ref_label = f"All communities ({fmt_num(all_v, unit)})" if all_v is not None else ""
            # A lone Muslim bar needs a zero anchor so its length stays honest and
            # the dashed line fits (the 2-bar-magnitude exception); a full ranking
            # keeps the house no-zero baseline so community gaps stay visible.
            begin_zero = "true" if len(pairs) == 1 else "false"
            js = (f'hbar("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, {json.dumps(colors)}, '
                  f'{json.dumps(suffix)}, {dec}, {ref}, {json.dumps(ref_label)}, {begin_zero});')
        details = _state_details(mid, unit) + _sex_details(mid, unit)

    if mid == "ger-higher-ed":
        details += _ger_count_views()   # fold in the decarded student-count metric
    return _card_shell(mid, label, headline, CAPTION.get(mid, ""), _year_of(mid), polarity,
                       chart_html, comps, src, csv_href, details), js


def _card_muslim_only(mid, label, unit, src, csv_href, cvid):
    nat = _nat_by_religion(mid)
    muslim = nat.get("muslim")
    headline = fmt_num(muslim, unit) if muslim is not None else "n/a"
    chart_html, js, note = "", None, ""
    conc_view, download = "", _district_download_link(mid)
    if mid == "pop-share":
        # Decadal multi-community trend (1961->2011). Hindu (~80%) dominates if
        # plotted on the same axis as Muslim + minor religions, so the chart's
        # y-axis hugs the 0-15% band where the Muslim story is legible; Hindu's
        # trajectory is summarised in the note (it moved 83.45 -> 79.80 over 50
        # years, a flat-looking 3.65pp drift at this resolution).
        years, series, _ = _nat_trend(mid)
        main_named = ("muslim", "christian", "sikh", "buddhist", "jain")
        series_map = {rel: [(_round_dp(v, _disp_dp(unit)) if (v := series.get(rel, {}).get(y)) is not None else None)
                            for y in years]
                      for rel in main_named if rel in series}
        hindu_first = series.get("hindu", {}).get(years[0]) if years else None
        hindu_last = series.get("hindu", {}).get(years[-1]) if years else None
        chart_html = f'<div class="card-chartwrap" style="height:200px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
        # No All-India series (shares already sum to ~100%); no refLine.
        js = (f'trendChart("{cvid}", {json.dumps(years)}, {json.dumps(series_map)}, '
              f'null, "%", {_disp_dp(unit)}, false);')
        # The provenance caveats (RGI volumes; 1981 excludes Assam, 1991 excludes
        # Jammu & Kashmir) live in the modal's "About this measurement" methodology,
        # so the card face keeps just the one-line reason Hindu is off the chart.
        note = (f"Hindu's share drifted from {_round_str(hindu_first, 1)}% in 1961 to "
                f"{_round_str(hindu_last, 1)}% in 2011, omitted from the chart so the "
                f"Muslim and minor-community trends are legible.")
        # "By district" tab: the geographic-concentration story, merged in from
        # the former district-concentration card (Commit DV). Its cumulative
        # curve is a 2nd modal chart; the all-640-districts CSV download lives in
        # this tab too. _concentration_view reads the concentration canonical.
        conc_view, curve_js = _concentration_view(cvid + "-district", download)
        if curve_js:
            js = js + "\n" + curve_js
        download = ""  # moved into the by-district tab
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
                  f'{json.dumps(["#7b1d22"] * len(st))}, "k", 0, null, "");')
        note = ("No community ranking. AISHE tabulates “Muslim Minority” enrolment separately; "
                "other communities are not enumerated in the same table. Top-8 states shown (thousands).")
    comps = f'<div class="comp-note">{html.escape(note)}</div>'
    # Drill-downs become modal tabs (see _card_shell): state data, sex (where the
    # source supports it), and, for pop-share, the by-district concentration view.
    details = _state_details(mid, unit) + _sex_details(mid, unit) + conc_view
    return _card_shell(mid, label, headline, CAPTION.get(mid, ""), _year_of(mid), "",
                       chart_html, comps, src, csv_href, details, download_html=download), js


def _card_timeseries(mid, label, unit, src, csv_href, cvid):
    rows = sorted([r for r in load_metric(mid) if r["geography_level"] == "national"],
                  key=lambda r: int(r["year"]))
    latest = rows[-1] if rows else None
    val = float(latest["value"]) if latest else None
    headline = fmt_num(val, unit) if val is not None else "n/a"
    gap = (val - MUSLIM_POP_SHARE) if val is not None else 0
    comps = _comp("vs population", f"{'+' if gap >= 0 else ''}{_round_str(gap, 1)}pp", "vs 14.2% pop share", "bad" if gap < 0 else "good")
    chart_html, js = "", None
    if len(rows) >= 2:
        labels = [int(r["year"]) for r in rows]
        values = [_round_dp(float(r["value"]), _disp_dp(unit)) for r in rows]
        chart_html = f'<div class="card-chartwrap" style="height:150px"><canvas id="{cvid}" role="img" aria-label="Visualisation of this metric; numerical values are listed in the card above."></canvas></div>'
        js = f'lineChart("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, "#7b1d22", "%", {_disp_dp(unit)});'
        comps += _comp("trend", f"{labels[0]}-{labels[-1]}", f"{_round_str(values[0], 1)}% → {_round_str(values[-1], 1)}%", "neutral")
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
                  f'{json.dumps([_round_dp(s[1], _disp_dp(unit)) for s in st])}, '
                  f'{json.dumps(["#7b1d22"] * len(st))}, "%", 1);')
        comps += _comp("all states", headline, "aggregate across assemblies", "neutral")
    details = _state_details(mid, unit)
    return _card_shell(mid, label, headline, CAPTION.get(mid, ""), latest["year"] if latest else "",
                       "", chart_html, comps, src, csv_href, details), js


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
        js = f'lineChart("{cvid}", {json.dumps(labels)}, {json.dumps(values)}, "#7b1d22", "", 0);'
        comps += _comp("trend", f"{labels[0]}-{labels[-1]}", f"{values[0]:,} → {val:,}", "neutral")
    elif len(rows) == 2:
        # Only two rounds: a 2-point line is just a sloped segment, so show the
        # two years as side-by-side bars instead, so the year-on-year jump
        # reads at a glance. Zero-based (beginAtZero=True) so bars are honest:
        # 668 vs 1,165 must look like "nearly double", not "triple". The latest
        # bar is the brand maroon (subject series); the rise/fall is shown in the
        # comp pill, not by recolouring the bar.
        first, last = int(float(rows[0]["value"])), val
        delta = last - first
        pct = (delta / first * 100) if first else 0
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        cls = "bad" if delta > 0 else ("good" if delta < 0 else "mid")
        y0, y1 = str(rows[0]["year"]), str(latest["year"])
        chart_html = (f'<div class="card-chartwrap" style="height:104px"><canvas id="{cvid}" '
                      f'role="img" aria-label="Bar comparison of {y0} versus {y1}; values listed in the card above."></canvas></div>')
        js = (f'hbar("{cvid}", {json.dumps([y0, y1])}, {json.dumps([first, last])}, '
              f'{json.dumps(["#D8DEE2", "#7b1d22"])}, "", 0, null, "", true);')
        noun = CAPTION.get(mid, "events")
        comps += _comp(f"vs {y0}", f"{arrow} {abs(pct):.0f}%", f"{delta:+,} {noun}", cls)
    # State-level drill-down for count metrics (e.g. communal-incidents-govt):
    # State | <noun> count, highest first. Returns "" for national-only metrics.
    details = _state_details(mid, "count", value_label=CAPTION.get(mid, "count").capitalize())
    return _card_shell(mid, label, f"{val:,}", CAPTION.get(mid, "events"), latest["year"] if latest else "",
                       "lower is better", chart_html, comps, src, csv_href, details), js


def render_all_clusters():
    """Group live metrics into the SECTION_GROUPS display sections and render each
    as a card grid. Within a section, cards order by scorecard `order`.

    Returns (clusters_html, charts_js, view_map) where view_map is
    {mid: [{id,label,sub}, ...]} for the per-view stub + OG generators.
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
    view_map: dict[str, list] = {}
    for name, cluster_ids in SECTION_GROUPS:
        ms = [m for cid in cluster_ids for m in by_cluster.get(cid, [])]
        if not ms:
            continue
        ms.sort(key=lambda m: m["display"]["scorecard"].get("order", 999))
        cards = []
        for m in ms:
            card_html, js, views = render_metric_card(m)
            cards.append(card_html)
            if js:
                charts.append(js)
            if views:
                view_map[m["id"]] = views
        intro = SECTION_INTROS.get(name, "")
        intro_html = (f'<p class="cluster-intro">{html.escape(intro)}</p>\n'
                      if intro else "")
        grids.append(f'<h2 class="cluster-header">{html.escape(name)}</h2>\n'
                     f'{intro_html}'
                     f'<div class="cards">\n{"".join(cards)}\n</div>')
    return "\n\n".join(grids), "\n".join(charts), view_map


if __name__ == "__main__":
    build()
