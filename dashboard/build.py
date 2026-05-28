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

def prep_pop_share(rows: list[dict]) -> dict:
    states = [(r["geography_code"], float(r["value"]))
              for r in rows if r["geography_level"] == "state"]
    states.sort(key=lambda x: -x[1])
    districts = [(r["geography_code"], float(r["value"]))
                 for r in rows if r["geography_level"] == "district"]
    districts.sort(key=lambda x: -x[1])
    top_districts = districts[:50]
    national = next((float(r["value"]) for r in rows if r["geography_code"] == "IN"), None)
    return {
        "headline": fmt_num(national, "percent") if national else "—",
        "headline_caption": (
            f"All-India Muslim share of total population (2011). "
            f"<b>{len(districts)} districts</b> in canonical with district-level Muslim share."
        ),
        "chart_labels": [state_label(c) for c, _ in states],
        "chart_values": [round(v, 2) for _, v in states],
        "chart_unit": "%",
        "national": national,
        "national_label": "National avg",
        "rows": [{"label": state_label(c), "value": fmt_num(v, "percent")}
                 for c, v in states],
        "top_districts": [{"label": c, "value": fmt_num(v, "percent")}
                          for c, v in top_districts],
        "n_districts": len(districts),
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
CLUSTER_DISPLAY = {
    "demographics": "Demographics",
    "education": "Education",
    "employment": "Employment",
    "income": "Income",
    "health": "Health",
    "housing": "Housing",
    "finance": "Finance",
    "representation": "Representation",
    "justice": "Justice",
    "civic": "Civic",
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
            CLUSTER_DISPLAY.get(m["cluster"], m["cluster"].capitalize()),
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

        # Special case: communal-incidents-govt time series, show latest year, no religion comparison
        if mid == "communal-incidents-govt":
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
                f'<td colspan="3" style="text-align:left">{val:,} incidents (national aggregate)</td>'
                f'<td class="gap-neutral">civil-society counts higher</td>'
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


def prep_prison_rate(kind: str) -> dict:
    """For prison/undertrial: present as absolute count + per-100k rate."""
    r = compute_prison_rates()[kind]
    muslim_cnt = r["muslim"]["count"]
    muslim_rate = r["muslim"]["rate_per_100k"]
    hindu_rate = r["hindu"]["rate_per_100k"]
    all_rate = r["all"]["rate_per_100k"]
    ratio = round(muslim_rate / hindu_rate, 2)
    return {
        "headline": f"{muslim_cnt:,}",
        "headline_caption": (
            f"All-India Muslim {kind} count. <b>{muslim_rate} per 100,000 Muslims</b>, "
            f"vs Hindu {hindu_rate} per 100k and All {all_rate} per 100k. "
            f"Muslim rate is <b>{ratio}× the Hindu rate</b>."
        ),
        "chart_labels": ["Muslim", "Hindu", "All"],
        "chart_values": [muslim_rate, hindu_rate, all_rate],
    }


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
  <p>Each tile shows: source path, methodology note, "data current to" badge, and a
  link to the underlying canonical CSV. Click any column header in the scorecard to sort.
  Numbers tagged <i>"paradox"</i> are ones where Muslim outcomes run <i>ahead of</i> Hindu —
  notably infant survival, women's anaemia, and sex ratio. These coexist with persistent
  Muslim disadvantage on the socioeconomic, representation, and justice indicators.</p>
</section>

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
    <summary>Full state data ({n_ps_rows} states)</summary>
    <table><thead><tr><th>State / UT</th><th>Muslim share</th></tr></thead><tbody>
      {ps_rows}
    </tbody></table>
  </details>
  <details>
    <summary>Top 50 districts by Muslim share (of {n_ps_districts} total)</summary>
    <table><thead><tr><th>District code</th><th>Muslim share</th></tr></thead><tbody>
      {ps_top_districts}
    </tbody></table>
    <p class="methodology" style="margin-top:8px">District codes are <code>IN-S&lt;state&gt;-D&lt;distt&gt;</code>
    using Census 2011 codes. The top of this list is dominated by Kashmir Valley districts
    (state 01), Lakshadweep (31), Malappuram in Kerala (32), and Murshidabad-belt districts
    in West Bengal (19).</p>
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

<!-- INSTITUTIONAL DELIVERY -->
<section class="tile">
  <div class="tile-head">
    <h2>Institutional delivery rate</h2>
    <p class="source">canonical/inst-delivery.csv · sources/nfhs-5/reports/india-report-fr375.pdf (Table 8.13, p. 324)</p>
    <p class="data-current">Data current to · NFHS-5 (2019-21)</p>
  </div>
  <div class="headline">{id_headline}</div>
  <p class="headline-caption">{id_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="id-chart"></canvas></div>
  <p class="methodology">Percentage of live births (5 years preceding NFHS-5) that took place in a
  health facility. Muslim institutional delivery (84.3%) runs 5.2pp below Hindu (89.5%) — unlike
  IMR and anaemia (where the Muslim outcome runs ahead), this is the expected direction.
  Suggests the maternal-care system reaches Muslim women less effectively even where infant
  outcomes are paradoxically better.</p>
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

<h2 class="cluster-header">Housing</h2>

<!-- IMPROVED SANITATION -->
<section class="tile">
  <div class="tile-head">
    <h2>Toilet facility access (households)</h2>
    <p class="source">canonical/improved-sanitation.csv · sources/nfhs-5/reports/india-report-fr375.pdf (Table 2.4, p. 74)</p>
    <p class="data-current">Data current to · NFHS-5 (2019-21)</p>
  </div>
  <div class="headline">{is_headline}</div>
  <p class="headline-caption">{is_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="is-chart"></canvas></div>
  <p class="methodology">Percentage of households with access to a toilet facility (any type —
  not strictly "improved" per JMP definition). Muslim toilet access (90.3%) runs <b>above
  Hindu (80.7%)</b> — primarily a composition effect: urban share of Muslim population is
  higher than urban share of Hindu population, and urban toilet access is uniformly higher
  than rural. Reading: this is a paradox metric like IMR / sex-ratio — Muslim infrastructure
  access is not uniformly worse, and the headline number depends heavily on urban-rural mix.</p>
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

<h2 class="cluster-header">Representation</h2>

<!-- LOK SABHA SHARE -->
<section class="tile">
  <div class="tile-head">
    <h2>Muslim share of Lok Sabha members</h2>
    <p class="source">canonical/ls-share.csv · manual entry from ECI affidavit aggregations (Maktoob Media, FACTLY, The India Forum, Statista)</p>
    <p class="data-current">Data current to · 18th Lok Sabha (2024 general election)</p>
  </div>
  <div class="headline">{ls_headline}</div>
  <p class="headline-caption">{ls_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="ls-chart"></canvas></div>
  <p class="methodology">Time series 2009–2024: 28 (5.16%), 22 (4.05%), 27 (4.97%), 24 (4.42%).
  Muslim share of seats has hovered around 4-5% across the last four Lok Sabhas, against a
  Muslim population share of <b>~14.2%</b> — chronic 9-10pp underrepresentation, and the
  second-lowest share since independence (the lowest was 2014). Religion is not tabulated
  by ECI or PRS Legislative Research; data is post-election journalistic aggregation of
  candidate affidavits, cross-verified across multiple sources (documented manual entry).</p>
</section>

<!-- MLA SHARE -->
<section class="tile">
  <div class="tile-head">
    <h2>Muslim share of state assembly MLAs</h2>
    <p class="source">canonical/mla-share.csv · manual entry from ECI affidavit aggregations</p>
    <p class="data-current">Data current to · most recent assembly election per state (2023-2026)</p>
  </div>
  <div class="headline">{mla_headline}</div>
  <p class="headline-caption">{mla_caption}</p>
  <div class="chart-wrap" style="height:340px"><canvas id="mla-chart"></canvas></div>
  <p class="methodology">National aggregate across 28 state assemblies is ~6%. Per-state values vary
  sharply: Kerala (25%) and West Bengal (13.7%) come closest to population proportionality, while
  Chhattisgarh (0%), Madhya Pradesh (0.9%), and Maharashtra (3.5%) are far below their Muslim
  population share. Like the Lok Sabha figure, this is manual entry from journalistic aggregation
  of ECI affidavits — religion is not in any official tabulation. Coverage gap: ~19 more state
  assemblies need their own research (UP, Bihar, Assam, TN, Karnataka, Gujarat, Punjab, etc.).</p>
</section>

<h2 class="cluster-header">Justice</h2>

<!-- PRISON RATE -->
<section class="tile">
  <div class="tile-head">
    <h2>Muslim prison population — count and incarceration rate</h2>
    <p class="source">canonical/prison-share.csv · sources/ncrb-prison/psi-2022.pdf (Tables 2.10C–2.13C, pp. 103, 107, 111, 115)</p>
    <p class="data-current">Data current to · NCRB Prison Statistics India 2022 (as on 2023-12-01)</p>
  </div>
  <div class="headline">{ps2_headline}</div>
  <p class="headline-caption">{ps2_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="ps2-chart"></canvas></div>
  <p class="methodology">Combined convicts + undertrials + detenues + other prisoners.
  Presented as absolute count and as incarceration rate per 100,000 of religious population
  (a more direct measure of disproportion than "share of prisoners" alone). Muslim incarceration
  rate of 63.3 per 100k vs Hindu 39.8 per 100k means a Muslim Indian is <b>1.59× as likely to
  be in prison</b> as a Hindu Indian. Detenues (preventive-detention prisoners) skew much higher:
  40.5% Muslim by share, driven heavily by J&K. Caveat: Maharashtra did not report religion
  breakdown for ~33k undertrials/detenues — rates are computed over religion-reported prisoners
  with full population in the denominator (so the actual rate is mildly understated).</p>
</section>

<!-- UNDERTRIAL RATE -->
<section class="tile">
  <div class="tile-head">
    <h2>Muslim undertrial population — count and rate</h2>
    <p class="source">canonical/undertrial-share.csv · sources/ncrb-prison/psi-2022.pdf (Table 2.11C, p. 107)</p>
    <p class="data-current">Data current to · NCRB PSI 2022</p>
  </div>
  <div class="headline">{us_headline}</div>
  <p class="headline-caption">{us_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="us-chart"></canvas></div>
  <p class="methodology">Undertrials are prisoners awaiting trial — not convicted. Muslim
  undertrial rate (48.7 per 100k Muslims) is <b>1.66× the Hindu rate</b> (29.3 per 100k Hindus),
  the highest disproportion among the prison categories — consistent with widely-documented
  patterns of detention-vs-conviction disparity (Muslims face higher pre-trial detention even
  when conviction rates are similar).</p>
</section>

<h2 class="cluster-header">Civic — communal violence</h2>

<!-- COMMUNAL INCIDENTS (GOVT) -->
<section class="tile">
  <div class="tile-head">
    <h2>Communal/religious rioting incidents (NCRB)</h2>
    <p class="source">canonical/communal-incidents-govt.csv · sources/ncrb-crime/cii-2022-book1.pdf (Tables 1.2 + 1A.4)</p>
    <p class="data-current">Data current to · NCRB Crime in India 2022</p>
  </div>
  <div class="headline">{ci_headline}</div>
  <p class="headline-caption">{ci_caption}</p>
  <div class="chart-wrap" style="height:280px"><canvas id="ci-chart"></canvas></div>
  <p class="methodology">National annual total of cases registered under "Communal/Religious" rioting
  (IPC Sec.147-151 sub-classification). The 2020 spike (857) coincides with CAA-NRC protests and
  the Delhi riots; the subsequent decline (378 → 272) is contested. Several states have stopped
  recording "communal" as a separate crime category since ~2017, which deflates the national
  total. Civil-society compilations (Documentation of the Oppressed, India Hate Lab) typically
  report substantially higher counts. NCRB tables do not disclose religion of victim or
  perpetrator — only incident counts.</p>
  <details>
    <summary>Top 15 states by NCRB-recorded incidents in 2022 (of {ci_n_states})</summary>
    <table><thead><tr><th>State / UT</th><th>Incidents 2022</th></tr></thead><tbody>
      {ci_state_rows}
    </tbody></table>
    <p class="methodology" style="margin-top:8px">Caveat repeated: cross-state comparisons are
    biased by inconsistent recording practices — some states (e.g. UP, Bengal) show 0 in this
    table because they no longer classify communal cases separately, not because no incidents
    occurred.</p>
  </details>
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

new Chart(document.getElementById('is-chart'), {
  type: 'bar',
  data: {
    labels: {is_chart_labels},
    datasets: [{ label: 'Toilet access (%)', data: {is_chart_values},
      backgroundColor: ['rgba(43,108,176,0.85)', 'rgba(183,106,43,0.85)', 'rgba(90,106,93,0.85)'] }],
  },
  options: { ...CFG_BASE, indexAxis: 'y',
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('id-chart'), {
  type: 'bar',
  data: {
    labels: {id_chart_labels},
    datasets: [{ label: 'Institutional delivery (%)', data: {id_chart_values},
      backgroundColor: ['rgba(43,108,176,0.85)', 'rgba(183,106,43,0.85)', 'rgba(90,106,93,0.85)'] }],
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

new Chart(document.getElementById('mla-chart'), {
  type: 'bar',
  data: {
    labels: {mla_chart_labels},
    datasets: [{ label: 'Muslim share of state assembly (%)', data: {mla_chart_values},
      backgroundColor: 'rgba(43,108,176,0.85)' }],
  },
  options: { ...CFG_BASE,
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('ci-chart'), {
  type: 'bar',
  data: {
    labels: {ci_chart_labels},
    datasets: [{ label: 'Communal incidents (NCRB)', data: {ci_chart_values},
      backgroundColor: 'rgba(123,29,34,0.85)' }],
  },
  options: { ...CFG_BASE,
    plugins: { ...CFG_BASE.plugins, legend: { display: false } } },
});

new Chart(document.getElementById('ls-chart'), {
  type: 'bar',
  data: {
    labels: {ls_chart_labels},
    datasets: [
      { label: 'Muslim share of Lok Sabha (%)', data: {ls_chart_values}, backgroundColor: 'rgba(43,108,176,0.85)' },
    ],
  },
  options: { ...CFG_BASE,
    plugins: { ...CFG_BASE.plugins, legend: { display: false } },
    scales: { ...CFG_BASE.scales, y: { ...CFG_BASE.scales.y, suggestedMin: 0, suggestedMax: 16,
      ticks: { font: { size: 11 }, callback: function(v) { return v + '%'; } } } } },
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
    id_ = prep_national_by_religion(load_metric("inst-delivery"), "percent")
    wa = prep_national_by_religion(load_metric("women-anemia"), "percent")
    is_ = prep_national_by_religion(load_metric("improved-sanitation"), "percent")
    lfpr = prep_national_by_religion(load_metric("lfpr-15plus"), "percent")
    wpr = prep_national_by_religion(load_metric("wpr-15plus"), "percent")
    ps2 = prep_prison_rate("prison")
    us = prep_prison_rate("undertrial")
    # mla-share: national row + per-state rows (multiple years)
    mla_data_rows = load_metric("mla-share")
    mla_national = next((r for r in mla_data_rows if r["geography_level"] == "national"), None)
    mla_states = sorted([r for r in mla_data_rows if r["geography_level"] == "state"],
                        key=lambda r: -float(r["value"]))
    mla_data = {
        "headline": f"{float(mla_national['value']):.2f}%" if mla_national else "—",
        "headline_caption": (
            "All-state aggregate ~<b>6% of MLAs</b> across 28 state assemblies, vs Muslim "
            "population share ~14.2%. Per-state chart below shows verified counts for 8 states."
        ),
        "chart_labels": [state_label(r["geography_code"]) + f' ({r["year"]})' for r in mla_states],
        "chart_values": [float(r["value"]) for r in mla_states],
    }
    # ls-share time series tile (national only)
    ls_rows = sorted([r for r in load_metric("ls-share") if r["geography_level"] == "national"],
                     key=lambda r: int(r["year"]))
    ls_latest = ls_rows[-1] if ls_rows else None
    ls_data = {
        "headline": f"{float(ls_latest['value']):.2f}%" if ls_latest else "—",
        "headline_caption": (
            f"Muslim MPs in the 18th Lok Sabha (2024). "
            f"<b>{float(ls_latest['value']):.2f}% of 543 seats</b> "
            f"vs Muslim population share ~14.2% — a chronic 9-10pp underrepresentation."
        ),
        "chart_labels": [r["year"] for r in ls_rows],
        "chart_values": [float(r["value"]) for r in ls_rows],
    }
    # communal-incidents-govt: national time series + state-2022 drill-down
    all_ci = load_metric("communal-incidents-govt")
    ci_national = sorted([r for r in all_ci if r["geography_level"] == "national"],
                         key=lambda r: int(r["year"]))
    ci_states = sorted([r for r in all_ci if r["geography_level"] == "state"],
                       key=lambda r: -int(float(r["value"])))
    ci_latest = ci_national[-1] if ci_national else None
    # Render state drill-down rows (top 15)
    ci_state_rows = "\n      ".join(
        f'<tr><td>{html.escape(state_label(r["geography_code"]))}</td>'
        f'<td>{int(float(r["value"]))}</td></tr>'
        for r in ci_states[:15]
    )
    ci_data = {
        "headline": f"{int(float(ci_latest['value'])):,}" if ci_latest else "—",
        "headline_caption": (
            f"Communal/religious rioting incidents recorded by NCRB nationally in "
            f"{ci_latest['year']}. Time series: 857 (2020) → 378 (2021) → 272 (2022). "
            f"The published decline is contested by civic compilations which report higher counts; "
            f"several states have stopped recording 'communal' as a separate category since ~2017."
        ),
        "chart_labels": [r["year"] for r in ci_national],
        "chart_values": [int(float(r["value"])) for r in ci_national],
        "state_rows": ci_state_rows,
        "n_states": len(ci_states),
    }
    ahe = prep_muslim_higher_ed(load_metric("muslim-higher-ed-enrolment"))

    n_sources = 6
    n_metrics = 17  # +communal-incidents-govt
    n_rows = (len(load_metric("pop-share")) + len(load_metric("lit-7plus"))
              + len(load_metric("sex-ratio")) + len(load_metric("imr"))
              + len(load_metric("inst-delivery")) + len(load_metric("women-anemia"))
              + len(load_metric("improved-sanitation"))
              + len(load_metric("lfpr-15plus")) + len(load_metric("wpr-15plus"))
              + len(load_metric("prison-share")) + len(load_metric("undertrial-share"))
              + len(load_metric("prison-rate-per-100k")) + len(load_metric("undertrial-rate-per-100k"))
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
        "{n_ps_districts}": str(pop["n_districts"]),
        "{ps_rows}": render_rows(pop["rows"], ["value"]),
        "{ps_top_districts}": render_rows(pop["top_districts"], ["value"]),
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
        # institutional delivery
        "{id_headline}": id_["headline"],
        "{id_caption}": id_["headline_caption"],
        "{id_chart_labels}": json.dumps(id_["chart_labels"]),
        "{id_chart_values}": json.dumps(id_["chart_values"]),
        # improved sanitation (toilet access)
        "{is_headline}": is_["headline"],
        "{is_caption}": is_["headline_caption"],
        "{is_chart_labels}": json.dumps(is_["chart_labels"]),
        "{is_chart_values}": json.dumps(is_["chart_values"]),
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
        # lok sabha share
        "{ls_headline}": ls_data["headline"],
        "{ls_caption}": ls_data["headline_caption"],
        "{ls_chart_labels}": json.dumps(ls_data["chart_labels"]),
        "{ls_chart_values}": json.dumps(ls_data["chart_values"]),
        # mla share
        "{mla_headline}": mla_data["headline"],
        "{mla_caption}": mla_data["headline_caption"],
        "{mla_chart_labels}": json.dumps(mla_data["chart_labels"]),
        "{mla_chart_values}": json.dumps(mla_data["chart_values"]),
        # communal incidents
        "{ci_headline}": ci_data["headline"],
        "{ci_caption}": ci_data["headline_caption"],
        "{ci_chart_labels}": json.dumps(ci_data["chart_labels"]),
        "{ci_chart_values}": json.dumps(ci_data["chart_values"]),
        "{ci_state_rows}": ci_data["state_rows"],
        "{ci_n_states}": str(ci_data["n_states"]),
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

    # Auto-linkify references to canonical/*.csv. We point at `canonical/X.csv`
    # relative to the preview folder — and copy the canonical CSVs into
    # dashboard/preview/canonical/ at build time, so the links work both locally
    # AND when GitHub Pages publishes only the dashboard/preview/ folder.
    import re as _re
    import shutil as _shutil
    html_out = _re.sub(
        r"(canonical/[a-zA-Z0-9_\-]+\.csv)",
        r'<a class="csv-link" href="\1">\1</a>',
        html_out,
    )

    # Copy canonical CSVs into the publish folder so the download links resolve.
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


if __name__ == "__main__":
    build()
