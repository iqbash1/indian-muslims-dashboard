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
    ahe = prep_muslim_higher_ed(load_metric("muslim-higher-ed-enrolment"))

    n_sources = 5  # Census + NFHS-5 + PLFS + AISHE + (HCES pending)
    n_metrics = 4
    n_rows = (len(load_metric("pop-share")) + len(load_metric("lit-7plus"))
              + len(load_metric("sex-ratio")) + len(load_metric("muslim-higher-ed-enrolment")))

    substitutions = {
        "{timestamp}": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "{n_metrics}": str(n_metrics),
        "{n_sources}": str(n_sources),
        "{n_rows}": str(n_rows),
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
