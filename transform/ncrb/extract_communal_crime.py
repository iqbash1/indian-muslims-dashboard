"""
L1 -> L2 for NCRB Crime in India — communal/religious rioting.
MULTI-YEAR (v2): processes CII 2022 and CII 2023 reports.

Reads:
  sources/ncrb-crime/cii-2022-book1.pdf      (pages 35 national, 67 states; 2020/21/22)
  sources/ncrb-crime/cii-2023-part1.pdf      (pages 35 national, 67 states; 2021/22/23)
Writes:
  extracted/ncrb-crime/cii-communal-incidents.csv

Captures two views:
  - National time series: deduped union across reports (2020/21/22/23 — overlap
    years 21+22 match across reports, so dedupe is safe).
  - State-level: most-recent-year per report (CII 2022 -> 2022 states; CII 2023
    -> 2023 states). Both years are kept.

Important caveat (also in source-runbook): several states have stopped
recording 'communal' as a separate crime category since ~2017, deflating
the published national total over time. The 2020 spike (857) reflects
CAA-NRC protest violence + Delhi riots; the subsequent decline (378->272)
is contested by civil-society counts (CJP "Myth of Neutral Data" critique).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "extracted" / "ncrb-crime" / "cii-communal-incidents.csv"
EXTRACTOR_VERSION = "2.0.0"

# Source kinds:
#   "main" = full CII volume — Table 1.2 at page 35, Table 1A.4 state at page 67
#   "table-1-2" = standalone per-table PDF (small) — Table 1.2 scanned across pages,
#                no state-level (just national time series)
# Per-source: (filename, kind, report_year, [years in Table 1.2 row])
REPORTS = [
    ("cii-2017-table-1-2.pdf", "table-1-2", 2017, [2015, 2016, 2017]),
    ("cii-2018-table-1-2.pdf", "table-1-2", 2018, [2016, 2017, 2018]),
    ("cii-2021-table-1-2.pdf", "table-1-2", 2021, [2019, 2020, 2021]),
    ("cii-2022-book1.pdf",     "main",      2022, [2020, 2021, 2022]),
    ("cii-2023-part1.pdf",     "main",      2023, [2021, 2022, 2023]),
]
MAIN_NATIONAL_PAGE = 35
MAIN_STATE_PAGE = 67

# Table 1.2 row format: "23.1 Communal/Religious <y1_i> <y1_r> <y2_i> <y2_r> <y3_i> <y3_r> <share>"
NATIONAL_TIME_SERIES_RE = re.compile(
    r"^23\.1\s+Communal/Religious\s+(\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+\.\d+)"
)

NUM = r"\d+(?:\.\d+)?"
STATE_ROW_RE = re.compile(
    rf"^(\d{{1,2}})\s+(.+?)\s+"
    rf"({NUM})\s+({NUM})\s+"             # unlawful assembly I, R
    rf"({NUM})\s+({NUM})\s+({NUM})\s+"   # rioting total I, V, R
    rf"({NUM})\s+({NUM})\s+({NUM})\s+"   # communal/religious I, V, R
    rf"({NUM})\s+({NUM})\s+({NUM})\s*$"  # sectarian I, V, R
)
TOTAL_ROW_RE = re.compile(
    rf"^TOTAL\s+(STATE\(S\)|UT\(S\)|ALL\s+INDIA)\s+"
    rf"({NUM})\s+({NUM})\s+"
    rf"({NUM})\s+({NUM})\s+({NUM})\s+"
    rf"({NUM})\s+({NUM})\s+({NUM})\s+"
    rf"({NUM})\s+({NUM})\s+({NUM})\s*$"
)


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path: pathlib.Path) -> dict:
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text())
    if sha256_of(path) != meta["sha256"]:
        sys.exit(f"sha256 mismatch for {path.name}")
    return meta


def _scan_national_row(pdf, pages_to_scan: list[int]) -> tuple[re.Match | None, int]:
    """Find the '23.1 Communal/Religious' row across the given page indices. Returns
    (match, 1-based page_number) or (None, -1)."""
    for page_idx in pages_to_scan:
        if page_idx >= len(pdf.pages):
            continue
        text = pdf.pages[page_idx].extract_text() or ""
        for line in text.splitlines():
            m = NATIONAL_TIME_SERIES_RE.match(line.strip())
            if m:
                return m, page_idx + 1
    return None, -1


def extract_one_report(source_filename: str, kind: str, report_year: int, years: list[int]) -> list[dict]:
    src = REPO_ROOT / "sources" / "ncrb-crime" / source_filename
    meta = verify(src)
    sha_prefix = meta["sha256"][:16]

    out: list[dict] = []
    with pdfplumber.open(str(src)) as pdf:
        if kind == "main":
            scan_pages = [MAIN_NATIONAL_PAGE - 1]
        else:
            # Per-table PDF — scan all pages (tiny file)
            scan_pages = list(range(len(pdf.pages)))
        m, found_page = _scan_national_row(pdf, scan_pages)
        if m:
            for i, yr in enumerate(years):
                out.append({
                    "row_type": "national_year", "year": yr,
                    "geography": "ALL INDIA",
                    "communal_incidents": int(m.group(1 + i * 2)),
                    "page": found_page,
                    "source_document": str(src.relative_to(REPO_ROOT)),
                    "source_sha256_prefix": sha_prefix,
                    "report_year": report_year,
                })

        # State-level (Table 1A.4) only for "main" volumes
        if kind == "main":
            text = pdf.pages[MAIN_STATE_PAGE - 1].extract_text() or ""
            latest_year = years[-1]
            for line in text.splitlines():
                line = line.strip()
                m_state = STATE_ROW_RE.match(line)
                m_total = TOTAL_ROW_RE.match(line)
                base = {
                    "page": MAIN_STATE_PAGE,
                    "source_document": str(src.relative_to(REPO_ROOT)),
                    "source_sha256_prefix": sha_prefix,
                    "report_year": report_year,
                }
                if m_state:
                    out.append({
                        **base,
                        "row_type": f"state_{latest_year}", "year": latest_year,
                        "geography": m_state.group(2).strip(),
                        "communal_incidents": int(float(m_state.group(8))),
                    })
                elif m_total:
                    out.append({
                        **base,
                        "row_type": f"subtotal_{latest_year}", "year": latest_year,
                        "geography": f"TOTAL {m_total.group(1).strip()}",
                        "communal_incidents": int(float(m_total.group(7))),
                    })
    return out


def extract() -> None:
    extraction_run = (
        f"ncrb-cii-communal-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    all_rows: list[dict] = []
    for filename, kind, ryear, years in REPORTS:
        all_rows.extend(extract_one_report(filename, kind, ryear, years))

    # Dedupe national_year by year (keep latest report's value; consistency
    # check: overlapping years should match across reports).
    by_year: dict[int, dict] = {}
    other_rows: list[dict] = []
    for r in all_rows:
        if r["row_type"] == "national_year":
            yr = r["year"]
            if yr in by_year and by_year[yr]["communal_incidents"] != r["communal_incidents"]:
                print(f"  WARN: {yr} national overlap mismatch: "
                      f"{by_year[yr]['communal_incidents']} (from {by_year[yr]['report_year']}) "
                      f"vs {r['communal_incidents']} (from {r['report_year']})")
            if yr not in by_year or r["report_year"] > by_year[yr]["report_year"]:
                by_year[yr] = r
        else:
            other_rows.append(r)
    final_rows = sorted(by_year.values(), key=lambda r: r["year"]) + other_rows

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "row_type", "year", "geography", "communal_incidents", "page", "report_year",
        ])
        for r in final_rows:
            w.writerow([
                "ncrb-crime", r["source_document"],
                r["source_sha256_prefix"], extraction_run,
                r["row_type"], r["year"], r["geography"],
                r["communal_incidents"], r["page"], r["report_year"],
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(final_rows)} rows)")
    for r in final_rows:
        if r["row_type"] == "national_year" or r["row_type"].startswith("subtotal_"):
            print(f"  {r['year']} {r['geography']}: {r['communal_incidents']} incidents  "
                  f"(from CII {r['report_year']})")


if __name__ == "__main__":
    extract()
