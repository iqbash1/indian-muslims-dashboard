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
MANIFEST = REPO_ROOT / "manifest" / "metrics.yaml"
OUT_PATH = REPO_ROOT / "dashboard" / "preview" / "index.html"


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

def prep_pop_share(rows: list[dict]) -> dict:
    states = [(r["geography_code"], float(r["value"]))
              for r in rows if r["geography_level"] == "state"]
    states.sort(key=lambda x: -x[1])
    national = next((float(r["value"]) for r in rows if r["geography_code"] == "IN"), None)
    return {
        "headline": fmt_num(national, "percent") if national else "—",
        "headline_caption": "All-India Muslim share of total population (2011)",
        "chart_labels": [state_label(c) for c, _ in states],
        "chart_values": [round(v, 2) for _, v in states],
        "chart_unit": "%",
        "national": national,
        "national_label": "National avg",
        "rows": [{"label": state_label(c), "value": fmt_num(v, "percent")}
                 for c, v in states],
    }


def prep_lit_7plus(rows: list[dict]) -> dict:
    by_geo: dict[str, dict[str, float]] = {}
    for r in rows:
        g = r["geography_code"]
        if g not in by_geo:
            by_geo[g] = {}
        by_geo[g][r["religion"]] = float(r["value"])

    national = by_geo.get("IN", {})
    state_keys = [g for g in by_geo if g.startswith("IN-S")]
    state_keys.sort(key=lambda g: by_geo[g].get("muslim", 0))

    # Gap chart: Muslim vs Hindu literacy by state
    chart_labels = [state_label(g) for g in state_keys]
    muslim = [round(by_geo[g].get("muslim", 0), 2) for g in state_keys]
    hindu = [round(by_geo[g].get("hindu", 0), 2) for g in state_keys]

    table_rows = []
    for g in [(None, "IN")] + [(None, k) for k in state_keys]:
        code = g[1]
        b = by_geo.get(code, {})
        gap = b.get("hindu", 0) - b.get("muslim", 0)
        table_rows.append({
            "label": state_label(code),
            "muslim": fmt_num(b.get("muslim", 0), "percent") if "muslim" in b else "—",
            "hindu": fmt_num(b.get("hindu", 0), "percent") if "hindu" in b else "—",
            "all": fmt_num(b.get("all", 0), "percent") if "all" in b else "—",
            "gap": f"{gap:+.2f}pp" if "muslim" in b and "hindu" in b else "—",
        })

    return {
        "headline": fmt_num(national.get("muslim", 0), "percent"),
        "headline_caption": (
            f"All-India Muslim literacy (7+), 2011. "
            f"Hindu: {fmt_num(national.get('hindu', 0), 'percent')}, "
            f"All: {fmt_num(national.get('all', 0), 'percent')}"
        ),
        "chart_labels": chart_labels,
        "muslim_series": muslim,
        "hindu_series": hindu,
        "table_rows": table_rows,
    }


def prep_sex_ratio(rows: list[dict]) -> dict:
    by_geo: dict[str, dict[str, float]] = {}
    for r in rows:
        g = r["geography_code"]
        if g not in by_geo:
            by_geo[g] = {}
        by_geo[g][r["religion"]] = float(r["value"])

    national = by_geo.get("IN", {})
    state_keys = [g for g in by_geo if g.startswith("IN-S")]
    state_keys.sort(key=lambda g: by_geo[g].get("muslim", 0))

    return {
        "headline": fmt_num(national.get("muslim", 0), "females_per_1000_males"),
        "headline_caption": (
            f"All-India Muslim sex ratio (females per 1000 males), 2011. "
            f"Hindu: {fmt_num(national.get('hindu', 0), 'females_per_1000_males')}, "
            f"All: {fmt_num(national.get('all', 0), 'females_per_1000_males')}"
        ),
        "chart_labels": [state_label(g) for g in state_keys],
        "muslim_series": [round(by_geo[g].get("muslim", 0), 1) for g in state_keys],
        "hindu_series": [round(by_geo[g].get("hindu", 0), 1) for g in state_keys],
    }


SCORECARD_SPEC = [
    # (cluster, metric_id, display_name, unit, reference_religion, higher_is_better)
    ("Demographics", "pop-share",                 "Population share",                 "percent", None,    None),
    ("Demographics", "sex-ratio",                 "Sex ratio (F/1000M)",              "females_per_1000_males", "hindu", True),
    ("Education",    "lit-7plus",                 "Literacy rate (7+)",               "percent", "hindu", True),
    ("Education",    "muslim-higher-ed-enrolment","Higher-ed enrolment (count)",      "count",   None,    None),
    ("Employment",   "lfpr-15plus",               "LFPR (15+)",                       "percent", "hindu", True),
    ("Employment",   "wpr-15plus",                "WPR (15+)",                        "percent", "hindu", True),
    ("Health",       "imr",                       "Infant Mortality Rate",            "per_1000_live_births", "hindu", False),
    ("Health",       "women-anemia",              "Anaemia in women (15-49)",         "percent", "hindu", False),
    ("Justice",      "prison-share",              "Muslim share of prisoners",        "percent", None,    None),  # gap vs pop-share
    ("Justice",      "undertrial-share",          "Muslim share of undertrials",      "percent", None,    None),
]
MUSLIM_POP_SHARE = 14.23


def render_scorecard_rows() -> str:
    """Compute one HTML <tr> per metric showing Muslim/Hindu/All and gap vs reference."""
    rows: list[str] = []
    for cluster, mid, name, unit, ref, higher_better in SCORECARD_SPEC:
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
        if mid in ("prison-share", "undertrial-share") and m_val is not None:
            # Gap is Muslim share - Muslim population share (overrepresentation)
            diff = m_val - MUSLIM_POP_SHARE
            sign = "+" if diff > 0 else ""
            gap_str = f"{sign}{diff:.2f}pp vs 14.23% pop"
            gap_class = "gap-bad" if diff > 0 else "gap-good"
        elif ref == "hindu" and m_val is not None and h_val is not None:
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


def prep_national_by_religion(rows: list[dict], unit: str) -> dict:
    """For metrics that only have national-level data (e.g. IMR, anemia from NFHS)."""
    by_religion = {r["religion"]: float(r["value"]) for r in rows
                   if r["geography_level"] == "national"}
    muslim = by_religion.get("muslim")
    hindu = by_religion.get("hindu")
    all_v = by_religion.get("all")
    headline = fmt_num(muslim, unit) if muslim is not None else "—"
    caption_parts = []
    if hindu is not None:
        caption_parts.append(f"Hindu: {fmt_num(hindu, unit)}")
    if all_v is not None:
        caption_parts.append(f"All: {fmt_num(all_v, unit)}")
    caption = "All-India Muslim, NFHS-5. " + ", ".join(caption_parts)
    # Bar chart of religion comparison
    order = ["muslim", "hindu", "all"]
    labels = [r.capitalize() if r != "all" else "All" for r in order if r in by_religion]
    values = [round(by_religion[r], 2) for r in order if r in by_religion]
    return {
        "headline": headline,
        "headline_caption": caption,
        "chart_labels": labels,
        "chart_values": values,
    }


def prep_muslim_higher_ed(rows: list[dict]) -> dict:
    states = [(r["geography_code"], float(r["value"]))
              for r in rows if r["geography_level"] == "state"]
    states.sort(key=lambda x: -x[1])
    national = next((float(r["value"]) for r in rows if r["geography_code"] == "IN"), None)
    return {
        "headline": fmt_num(national, "count") if national else "—",
        "headline_caption": (
            "All-India Muslim student enrolment in higher education (AISHE 2021-22). "
            "Note: AISHE reports Muslim Minority separately; Hindu is residual, not directly enumerated."
        ),
        "chart_labels": [state_label(c) for c, _ in states[:20]],
        "chart_values": [int(v) for _, v in states[:20]],
        "rows": [{"label": state_label(c), "value": fmt_num(v, "count")}
                 for c, v in states],
    }


# ---------- HTML rendering ----------

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
</style>
</head>
<body>
<div class="page">

<h1>Indian Muslims — Living Conditions Dashboard</h1>
<p class="tagline">Preview build · {timestamp}</p>

<div class="status-bar">
  <span><b>{n_metrics}</b> metrics live</span>
  <span><b>{n_sources}</b> sources archived</span>
  <span><b>{n_rows}</b> canonical rows · all schema-valid</span>
  <span>Comparison baseline on every applicable tile</span>
</div>

<!-- SCORECARD -->
<section class="tile scorecard">
  <div class="tile-head">
    <h2>Scorecard — all metrics at a glance</h2>
    <p class="data-current">Muslim outcome vs Hindu/All baseline · sorted by gap magnitude</p>
  </div>
  <table class="scorecard-table"><thead><tr>
    <th>Cluster</th><th>Metric</th><th>Year</th><th>Muslim</th><th>Hindu</th><th>All</th><th>Gap vs reference</th>
  </tr></thead><tbody>
    {scorecard_rows}
  </tbody></table>
  <p class="methodology">"Gap" is Muslim minus reference baseline (Hindu where available, else All).
  Red gap = Muslim outcome worse than reference; green = Muslim outcome better. For prison
  metrics, gap is Muslim share minus Muslim population share (14.2%) — overrepresentation
  in red, parity green.</p>
</section>

<h2 class="cluster-header">Demographics</h2>

<!-- POP SHARE -->
<section class="tile">
  <div class="tile-head">
    <h2>Muslim share of total population</h2>
    <p class="source">canonical/pop-share.csv · sources/census-2011/c-series/c01-population-by-religion.xls</p>
    <p class="data-current">Data current to · Census 2011 (next release: 2021 round delayed indefinitely)</p>
  </div>
  <div class="headline">{ps_headline}</div>
  <p class="headline-caption">{ps_caption}</p>
  <div class="chart-wrap"><canvas id="ps-chart"></canvas></div>
  <p class="methodology">Muslim population / total population at each geography, total residence
  (urban + rural combined). Per Census 2011 published methodology.</p>
  <details>
    <summary>Full data ({n_ps_rows} states)</summary>
    <table><thead><tr><th>State / UT</th><th>Muslim share</th></tr></thead><tbody>
      {ps_rows}
    </tbody></table>
  </details>
</section>

<h2 class="cluster-header">Education</h2>

<!-- LIT 7+ -->
<section class="tile">
  <div class="tile-head">
    <h2>Literacy rate (7+ years)</h2>
    <p class="source">canonical/lit-7plus.csv · sources/census-2011/c-series/c09-education-by-religion.xlsx</p>
    <p class="data-current">Data current to · Census 2011</p>
  </div>
  <div class="headline">{lit_headline}</div>
  <p class="headline-caption">{lit_caption}</p>
  <div class="chart-wrap"><canvas id="lit-chart"></canvas></div>
  <p class="methodology">(Literate − age-not-stated) / (Total − 0-6 − age-not-stated) × 100. Matches the
  Census published literacy definition. Under-7 are all illiterate by Census convention; the gap
  between Muslim and Hindu literacy is the comparison the dashboard is built around.</p>
  <details>
    <summary>Full data ({n_lit_rows} rows)</summary>
    <table><thead><tr>
      <th>State / UT</th><th>Muslim</th><th>Hindu</th><th>All</th><th>Hindu − Muslim gap</th>
    </tr></thead><tbody>
      {lit_rows}
    </tbody></table>
  </details>
</section>

<h2 class="cluster-header">Health</h2>

<!-- (sex-ratio remains in Demographics cluster — reordering deferred to keep this diff small) -->
<!-- SEX RATIO -->
<section class="tile">
  <div class="tile-head">
    <h2>Sex ratio (females per 1000 males)</h2>
    <p class="source">canonical/sex-ratio.csv · sources/census-2011/c-series/c15-religion-by-age-sex.xlsx</p>
    <p class="data-current">Data current to · Census 2011</p>
  </div>
  <div class="headline">{sr_headline}</div>
  <p class="headline-caption">{sr_caption}</p>
  <div class="chart-wrap"><canvas id="sr-chart"></canvas></div>
  <p class="methodology">Females ÷ males × 1000, at all ages and total residence. Higher = more females
  per male. Muslims have a higher national sex ratio than Hindus (951 vs 939) — one of the rare
  indicators where the Muslim outcome runs ahead.</p>
</section>

<!-- IMR -->
<section class="tile">
  <div class="tile-head">
    <h2>Infant Mortality Rate</h2>
    <p class="source">canonical/imr.csv · sources/nfhs-5/reports/india-report-fr375.pdf (Table 7.2, p. 284) · weighted with sources/census-2011/c-series/c01-population-by-religion.xls</p>
    <p class="data-current">Data current to · NFHS-5 (2019-21); 5-year reference period 2014-2020</p>
  </div>
  <div class="headline">{imr_headline}</div>
  <p class="headline-caption">{imr_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="imr-chart"></canvas></div>
  <p class="methodology">Infant deaths per 1000 live births. NFHS-5 Table 7.2 publishes URBAN
  and RURAL IMR by religion separately (no total-residence-by-religion column). Total
  residence computed as population-weighted average using Census 2011 urban/rural population
  by religion (urban/rural population shares by religion are stable 2011-2021, &lt;1% drift).
  Note: Muslim IMR running below Hindu IMR is the well-documented "Muslim mortality paradox"
  in Indian demography — Muslim infant survival outperforms Muslim adult socioeconomic
  indicators.</p>
</section>

<!-- WOMEN ANAEMIA -->
<section class="tile">
  <div class="tile-head">
    <h2>Anaemia in women (age 15–49)</h2>
    <p class="source">canonical/women-anemia.csv · sources/nfhs-5/reports/india-report-fr375.pdf (Table 10.23.1, p. 468)</p>
    <p class="data-current">Data current to · NFHS-5 (2019-21)</p>
  </div>
  <div class="headline">{wa_headline}</div>
  <p class="headline-caption">{wa_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="wa-chart"></canvas></div>
  <p class="methodology">Any anaemia (haemoglobin &lt;12.0 g/dl non-pregnant, &lt;11.0 g/dl pregnant),
  altitude-adjusted. Total residence, national. Muslim women's anaemia (55.6%) is slightly
  below Hindu (57.4%) — the same Muslim-paradox direction as IMR, though both rates are high
  in absolute terms. Methodology note: NFHS-5 uses capillary blood (vs venous in NFHS-4) —
  treat as a methodology break when comparing across rounds.</p>
</section>

<h2 class="cluster-header">Employment</h2>

<!-- LFPR 15+ -->
<section class="tile">
  <div class="tile-head">
    <h2>Labour Force Participation Rate (15+)</h2>
    <p class="source">canonical/lfpr-15plus.csv · sources/plfs/annual/plfs-annual-report-2023-24.pdf (Table 48, pp. 396–400)</p>
    <p class="data-current">Data current to · PLFS 2023-24 (Jul 2023 – Jun 2024)</p>
  </div>
  <div class="headline">{lfpr_headline}</div>
  <p class="headline-caption">{lfpr_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="lfpr-chart"></canvas></div>
  <p class="methodology">Share of population age 15+ either working or actively seeking work
  (usual status, principal + subsidiary). The 5.9pp Muslim–Hindu gap is driven heavily by
  Muslim women's lower LFPR (30.2% vs Hindu women 43.3% per the source); Muslim men's LFPR
  (80.6%) actually exceeds Hindu men's (78.6%).</p>
</section>

<!-- WPR 15+ -->
<section class="tile">
  <div class="tile-head">
    <h2>Worker Population Ratio (15+)</h2>
    <p class="source">canonical/wpr-15plus.csv · sources/plfs/annual/plfs-annual-report-2023-24.pdf (Table 48, pp. 396–400)</p>
    <p class="data-current">Data current to · PLFS 2023-24</p>
  </div>
  <div class="headline">{wpr_headline}</div>
  <p class="headline-caption">{wpr_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="wpr-chart"></canvas></div>
  <p class="methodology">Share of population age 15+ currently working. WPR = LFPR − unemployed.
  The Muslim–Hindu gap (5.9pp) parallels LFPR.</p>
</section>

<h2 class="cluster-header">Justice</h2>

<!-- PRISON SHARE -->
<section class="tile">
  <div class="tile-head">
    <h2>Muslim share of prison population</h2>
    <p class="source">canonical/prison-share.csv · sources/ncrb-prison/psi-2022.pdf (Tables 2.10C–2.13C, pp. 103, 107, 111, 115)</p>
    <p class="data-current">Data current to · NCRB Prison Statistics India 2022 (as on 2023-12-01)</p>
  </div>
  <div class="headline">{ps2_headline}</div>
  <p class="headline-caption">{ps2_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="ps2-chart"></canvas></div>
  <p class="methodology">Combined convicts + undertrials + detenues + other prisoners. Muslims
  are 14.2% of population (per Census 2011) but <b>20.17% of prisoners</b> whose religion was
  reported — a 6pp overrepresentation. Detenues (preventive-detention prisoners) skew much
  higher: 40.5% Muslim, driven heavily by J&K. Caveat: Maharashtra did not report religion
  for ~33k undertrials/detenues — share is computed over religion-reported subset only.</p>
</section>

<!-- UNDERTRIAL SHARE -->
<section class="tile">
  <div class="tile-head">
    <h2>Muslim share of undertrial prisoners</h2>
    <p class="source">canonical/undertrial-share.csv · sources/ncrb-prison/psi-2022.pdf (Table 2.11C, p. 107)</p>
    <p class="data-current">Data current to · NCRB PSI 2022</p>
  </div>
  <div class="headline">{us_headline}</div>
  <p class="headline-caption">{us_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="us-chart"></canvas></div>
  <p class="methodology">Undertrials are prisoners awaiting trial — not convicted. The
  undertrial Muslim share (20.92%) runs higher than the convict Muslim share (17.13%),
  consistent with widely-documented patterns of detention-vs-conviction disparity.</p>
</section>

<h2 class="cluster-header">Education — Higher Ed (count)</h2>

<!-- MUSLIM HIGHER ED ENROLMENT -->
<section class="tile">
  <div class="tile-head">
    <h2>Muslim student enrolment in higher education</h2>
    <p class="source">canonical/muslim-higher-ed-enrolment.csv · sources/aishe/aishe-report-2021-22.pdf (Table 15, p. 140)</p>
    <p class="data-current">Data current to · AISHE 2021-22 (next release: AISHE 2022-23 expected mid-2026)</p>
  </div>
  <div class="headline">{ahe_headline}</div>
  <p class="headline-caption">{ahe_caption}</p>
  <div class="chart-wrap"><canvas id="ahe-chart"></canvas></div>
  <p class="methodology">AISHE classifies enrolment as "Muslim Minority" vs "Other Minority Community"
  (Christians, Sikhs, Buddhists, Jains, Parsis); Hindu enrolment is the residual, not directly
  enumerated. This tile shows absolute Muslim count. A "Muslim share of total enrolment" metric
  is a separate canonical target that requires Total Enrolment by state from a different AISHE
  table (not yet extracted).</p>
  <div class="note">
    <b>Known data gap:</b> Ladakh, Lakshadweep, and West Bengal could not be cleanly extracted from
    AISHE Table 15 (PDF text-layer issues — see <code>transform/aishe/extract_table15.py</code>
    docstring). Combined, these account for less than 0.1% of national Muslim enrolment.
  </div>
  <details>
    <summary>Full data ({n_ahe_rows} states)</summary>
    <table><thead><tr><th>State / UT</th><th>Muslim enrolment</th></tr></thead><tbody>
      {ahe_rows}
    </tbody></table>
  </details>
</section>

<footer>
  <p>Built by <code>dashboard/build.py</code> from <code>canonical/*.csv</code> at {timestamp}.
  Every number on this page traces L4 → L3 (canonical) → L2 (extracted) → L1 (source file)
  with SHA256 sidecar provenance. Re-run the builder after any canonical change:
  <code>python dashboard/build.py</code></p>
</footer>

</div>

<script>
const CFG_BASE = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top', labels: { font: { size: 12 } } },
    tooltip: { titleFont: { size: 12 }, bodyFont: { size: 12 } },
  },
  scales: {
    y: { ticks: { font: { size: 11 } } },
    x: { ticks: { font: { size: 11 }, maxRotation: 60, minRotation: 60 } },
  },
};

new Chart(document.getElementById('ps-chart'), {
  type: 'bar',
  data: {
    labels: {ps_chart_labels},
    datasets: [
      { label: 'Muslim share (%)', data: {ps_chart_values}, backgroundColor: 'rgba(43,108,176,0.85)' },
    ],
  },
  options: {
    ...CFG_BASE,
    plugins: {
      ...CFG_BASE.plugins,
      annotation: {},
      legend: { display: false },
    },
  },
});

new Chart(document.getElementById('lit-chart'), {
  type: 'bar',
  data: {
    labels: {lit_chart_labels},
    datasets: [
      { label: 'Muslim', data: {lit_muslim}, backgroundColor: 'rgba(43,108,176,0.85)' },
      { label: 'Hindu',  data: {lit_hindu},  backgroundColor: 'rgba(183,106,43,0.85)' },
    ],
  },
  options: CFG_BASE,
});

new Chart(document.getElementById('sr-chart'), {
  type: 'bar',
  data: {
    labels: {sr_chart_labels},
    datasets: [
      { label: 'Muslim', data: {sr_muslim}, backgroundColor: 'rgba(43,108,176,0.85)' },
      { label: 'Hindu',  data: {sr_hindu},  backgroundColor: 'rgba(183,106,43,0.85)' },
    ],
  },
  options: {
    ...CFG_BASE,
    scales: {
      ...CFG_BASE.scales,
      y: { ...CFG_BASE.scales.y, suggestedMin: 800, suggestedMax: 1100 },
    },
  },
});

new Chart(document.getElementById('imr-chart'), {
  type: 'bar',
  data: {
    labels: {imr_chart_labels},
    datasets: [
      { label: 'IMR (per 1000 live births)', data: {imr_chart_values},
        backgroundColor: ['rgba(43,108,176,0.85)', 'rgba(183,106,43,0.85)', 'rgba(90,106,93,0.85)'] },
    ],
  },
  options: { ...CFG_BASE, indexAxis: 'y',
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('wa-chart'), {
  type: 'bar',
  data: {
    labels: {wa_chart_labels},
    datasets: [
      { label: 'Any anaemia (%)', data: {wa_chart_values},
        backgroundColor: ['rgba(43,108,176,0.85)', 'rgba(183,106,43,0.85)', 'rgba(90,106,93,0.85)'] },
    ],
  },
  options: { ...CFG_BASE, indexAxis: 'y',
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('lfpr-chart'), {
  type: 'bar',
  data: {
    labels: {lfpr_chart_labels},
    datasets: [{ label: 'LFPR 15+ (%)', data: {lfpr_chart_values},
      backgroundColor: ['rgba(43,108,176,0.85)', 'rgba(183,106,43,0.85)', 'rgba(90,106,93,0.85)'] }],
  },
  options: { ...CFG_BASE, indexAxis: 'y',
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('wpr-chart'), {
  type: 'bar',
  data: {
    labels: {wpr_chart_labels},
    datasets: [{ label: 'WPR 15+ (%)', data: {wpr_chart_values},
      backgroundColor: ['rgba(43,108,176,0.85)', 'rgba(183,106,43,0.85)', 'rgba(90,106,93,0.85)'] }],
  },
  options: { ...CFG_BASE, indexAxis: 'y',
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('ps2-chart'), {
  type: 'bar',
  data: {
    labels: {ps2_chart_labels},
    datasets: [{ label: 'Prison share (%)', data: {ps2_chart_values},
      backgroundColor: ['rgba(43,108,176,0.85)', 'rgba(183,106,43,0.85)'] }],
  },
  options: { ...CFG_BASE, indexAxis: 'y',
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('us-chart'), {
  type: 'bar',
  data: {
    labels: {us_chart_labels},
    datasets: [{ label: 'Undertrial share (%)', data: {us_chart_values},
      backgroundColor: ['rgba(43,108,176,0.85)', 'rgba(183,106,43,0.85)'] }],
  },
  options: { ...CFG_BASE, indexAxis: 'y',
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('ahe-chart'), {
  type: 'bar',
  data: {
    labels: {ahe_chart_labels},
    datasets: [
      { label: 'Muslim enrolment (top 20 states)', data: {ahe_chart_values},
         backgroundColor: 'rgba(123,29,34,0.85)' },
    ],
  },
  options: { ...CFG_BASE, plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});
</script>
</body>
</html>
"""


def render_rows(rows: list[dict], cols: list[str], national_label: str | None = None) -> str:
    out: list[str] = []
    for r in rows:
        cls = ' class="national"' if national_label and r.get("label") == national_label else ""
        cells = "".join(f"<td>{html.escape(str(r.get(c, '—')))}</td>" for c in cols)
        out.append(f"<tr{cls}><td>{html.escape(r['label'])}</td>{cells}</tr>")
    return "\n      ".join(out)


def build() -> None:
    pop = prep_pop_share(load_metric("pop-share"))
    lit = prep_lit_7plus(load_metric("lit-7plus"))
    sr = prep_sex_ratio(load_metric("sex-ratio"))
    imr = prep_national_by_religion(load_metric("imr"), "per_1000_live_births")
    wa = prep_national_by_religion(load_metric("women-anemia"), "percent")
    lfpr = prep_national_by_religion(load_metric("lfpr-15plus"), "percent")
    wpr = prep_national_by_religion(load_metric("wpr-15plus"), "percent")
    ps2 = prep_national_by_religion(load_metric("prison-share"), "percent")
    us = prep_national_by_religion(load_metric("undertrial-share"), "percent")
    ahe = prep_muslim_higher_ed(load_metric("muslim-higher-ed-enrolment"))

    n_sources = 6  # Census + NFHS-5 + PLFS + AISHE + HCES + NCRB
    n_metrics = 10
    n_rows = (len(load_metric("pop-share")) + len(load_metric("lit-7plus"))
              + len(load_metric("sex-ratio")) + len(load_metric("imr"))
              + len(load_metric("women-anemia")) + len(load_metric("lfpr-15plus"))
              + len(load_metric("wpr-15plus")) + len(load_metric("prison-share"))
              + len(load_metric("undertrial-share"))
              + len(load_metric("muslim-higher-ed-enrolment")))

    substitutions = {
        "{timestamp}": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "{n_metrics}": str(n_metrics),
        "{n_sources}": str(n_sources),
        "{n_rows}": str(n_rows),
        "{scorecard_rows}": render_scorecard_rows(),
        # pop-share
        "{ps_headline}": pop["headline"],
        "{ps_caption}": pop["headline_caption"],
        "{n_ps_rows}": str(len(pop["rows"])),
        "{ps_rows}": render_rows(pop["rows"], ["value"]),
        "{ps_chart_labels}": json.dumps(pop["chart_labels"]),
        "{ps_chart_values}": json.dumps(pop["chart_values"]),
        # lit-7plus
        "{lit_headline}": lit["headline"],
        "{lit_caption}": lit["headline_caption"],
        "{n_lit_rows}": str(len(lit["table_rows"])),
        "{lit_rows}": render_rows(lit["table_rows"], ["muslim", "hindu", "all", "gap"],
                                   national_label="All India"),
        "{lit_chart_labels}": json.dumps(lit["chart_labels"]),
        "{lit_muslim}": json.dumps(lit["muslim_series"]),
        "{lit_hindu}": json.dumps(lit["hindu_series"]),
        # sex-ratio
        "{sr_headline}": sr["headline"],
        "{sr_caption}": sr["headline_caption"],
        "{sr_chart_labels}": json.dumps(sr["chart_labels"]),
        "{sr_muslim}": json.dumps(sr["muslim_series"]),
        "{sr_hindu}": json.dumps(sr["hindu_series"]),
        # imr
        "{imr_headline}": imr["headline"],
        "{imr_caption}": imr["headline_caption"],
        "{imr_chart_labels}": json.dumps(imr["chart_labels"]),
        "{imr_chart_values}": json.dumps(imr["chart_values"]),
        # women anaemia
        "{wa_headline}": wa["headline"],
        "{wa_caption}": wa["headline_caption"],
        "{wa_chart_labels}": json.dumps(wa["chart_labels"]),
        "{wa_chart_values}": json.dumps(wa["chart_values"]),
        # lfpr 15+
        "{lfpr_headline}": lfpr["headline"],
        "{lfpr_caption}": lfpr["headline_caption"],
        "{lfpr_chart_labels}": json.dumps(lfpr["chart_labels"]),
        "{lfpr_chart_values}": json.dumps(lfpr["chart_values"]),
        # wpr 15+
        "{wpr_headline}": wpr["headline"],
        "{wpr_caption}": wpr["headline_caption"],
        "{wpr_chart_labels}": json.dumps(wpr["chart_labels"]),
        "{wpr_chart_values}": json.dumps(wpr["chart_values"]),
        # prison share
        "{ps2_headline}": ps2["headline"],
        "{ps2_caption}": ps2["headline_caption"],
        "{ps2_chart_labels}": json.dumps(ps2["chart_labels"]),
        "{ps2_chart_values}": json.dumps(ps2["chart_values"]),
        # undertrial share
        "{us_headline}": us["headline"],
        "{us_caption}": us["headline_caption"],
        "{us_chart_labels}": json.dumps(us["chart_labels"]),
        "{us_chart_values}": json.dumps(us["chart_values"]),
        # muslim higher ed
        "{ahe_headline}": ahe["headline"],
        "{ahe_caption}": ahe["headline_caption"],
        "{n_ahe_rows}": str(len(ahe["rows"])),
        "{ahe_rows}": render_rows(ahe["rows"], ["value"]),
        "{ahe_chart_labels}": json.dumps(ahe["chart_labels"]),
        "{ahe_chart_values}": json.dumps(ahe["chart_values"]),
    }
    html_out = TEMPLATE
    for k, v in substitutions.items():
        html_out = html_out.replace(k, v)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html_out)
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} ({len(html_out):,} bytes)")


if __name__ == "__main__":
    build()
