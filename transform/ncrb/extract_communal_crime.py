"""
L1 -> L2 for NCRB Crime in India 2022 — communal/religious rioting.

Reads:  sources/ncrb-crime/cii-2022-book1.pdf (pages 35, 67)
Writes: extracted/ncrb-crime/cii-2022-communal-incidents.csv

Captures two views:
  - National time series from Table 1.2 page 35: 2020/2021/2022
  - State-level breakdown from Table 1A.4 page 67

Important caveat (already in source-runbook): several states have stopped
recording 'communal' as a separate crime category since ~2017, which
deflates the published national total over time. The 2020 spike (857) is
partly attributable to communal violence around CAA-NRC protests + Delhi
riots; the subsequent decline (378 -> 272) is contested by civil-society
counts (see, e.g., CJP "Myth of Neutral Data" critique).
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
SOURCE_PATH = REPO_ROOT / "sources" / "ncrb-crime" / "cii-2022-book1.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "ncrb-crime" / "cii-2022-communal-incidents.csv"
EXTRACTOR_VERSION = "1.0.0"

# Page 35: "23.1 Communal/Religious <2020_cases> <2020_rate> <2021_cases> <2021_rate> <2022_cases> <2022_rate> <pct_share>"
NATIONAL_TIME_SERIES_RE = re.compile(
    r"^23\.1\s+Communal/Religious\s+(\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+\.\d+)"
)

# Page 67 state row:
#   "<sl> <state name> <ua_i> <ua_r> <riot_i> <riot_v> <riot_r> <comm_i> <comm_v> <comm_r> <sect_i> <sect_v> <sect_r>"
# State name may have spaces. Anchor on the trailing 11 numbers; first is SL.
NUM = r"\d+(?:\.\d+)?"
STATE_ROW_RE = re.compile(
    rf"^(\d{{1,2}})\s+(.+?)\s+"
    rf"({NUM})\s+({NUM})\s+"             # unlawful assembly I, R
    rf"({NUM})\s+({NUM})\s+({NUM})\s+"   # rioting total I, V, R
    rf"({NUM})\s+({NUM})\s+({NUM})\s+"   # communal/religious I, V, R   <-- want col 8 (comm_I)
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


def verify_source_integrity() -> dict:
    meta_path = SOURCE_PATH.with_suffix(SOURCE_PATH.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text())
    actual_sha = sha256_of(SOURCE_PATH)
    if actual_sha != meta["sha256"]:
        sys.exit(
            f"sha256 mismatch for {SOURCE_PATH.name}: "
            f"archive {actual_sha[:16]} != sidecar {meta['sha256'][:16]}"
        )
    return meta


def extract() -> None:
    meta = verify_source_integrity()

    extraction_run = (
        f"ncrb-cii-communal-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows: list[dict] = []
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        # Page 35: national time series
        text = pdf.pages[34].extract_text() or ""
        for line in text.splitlines():
            m = NATIONAL_TIME_SERIES_RE.match(line.strip())
            if m:
                rows.append({"row_type": "national_year", "year": 2020, "geography": "ALL INDIA",
                             "communal_incidents": int(m.group(1)), "page": 35})
                rows.append({"row_type": "national_year", "year": 2021, "geography": "ALL INDIA",
                             "communal_incidents": int(m.group(3)), "page": 35})
                rows.append({"row_type": "national_year", "year": 2022, "geography": "ALL INDIA",
                             "communal_incidents": int(m.group(5)), "page": 35})
                break

        # Page 67: state-level 2022 only
        text = pdf.pages[66].extract_text() or ""
        for line in text.splitlines():
            line = line.strip()
            m_state = STATE_ROW_RE.match(line)
            m_total = TOTAL_ROW_RE.match(line)
            if m_state:
                rows.append({
                    "row_type": "state_2022", "year": 2022,
                    "geography": m_state.group(2).strip(),
                    "communal_incidents": int(float(m_state.group(8))),
                    "page": 67,
                })
            elif m_total:
                # Group layout: 1=label, 2-3=ua, 4-6=riot, 7-9=communal, 10-12=sectarian.
                # group(7) is communal incidents (col_I). group(8) is victims.
                rows.append({
                    "row_type": "subtotal_2022", "year": 2022,
                    "geography": f"TOTAL {m_total.group(1).strip()}",
                    "communal_incidents": int(float(m_total.group(7))),
                    "page": 67,
                })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "row_type", "year", "geography", "communal_incidents", "page",
        ])
        for r in rows:
            w.writerow([
                "ncrb-crime", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                r["row_type"], r["year"], r["geography"],
                r["communal_incidents"], r["page"],
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    for r in rows:
        if r["row_type"] in ("national_year", "subtotal_2022"):
            print(f"  {r['year']} {r['geography']}: {r['communal_incidents']} incidents")


if __name__ == "__main__":
    extract()
