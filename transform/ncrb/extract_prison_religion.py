"""
L1 -> L2 for NCRB Prison Statistics India 2022 — religion-by-category tables.

Reads:  sources/ncrb-prison/psi-2022.pdf
        Tables 2.10C (convicts), 2.11C (undertrials), 2.12C (detenues),
        2.13C (other prisoners). One per page span: 103, 107, 111, 115.
Writes: extracted/ncrb-prison/psi-2022-religion-by-state.csv

Layout per table: Sl.No State/UT Hindu Muslim Sikh Christian Others Total
- 28 states + TOTAL (STATES)
- 8 UTs + TOTAL (UTs)
- TOTAL (ALL-INDIA)

Dashes "-" indicate non-reporting (Maharashtra in some tables).
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
SOURCE_PATH = REPO_ROOT / "sources" / "ncrb-prison" / "psi-2022.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "ncrb-prison" / "psi-2022-religion-by-state.csv"
EXTRACTOR_VERSION = "1.0.0"

TABLES = [
    ("2.10C", "convicts", 103),
    ("2.11C", "undertrials", 107),
    ("2.12C", "detenues", 111),
    ("2.13C", "other", 115),
]

# Row patterns. Numbers can be "-" for non-reporting.
NUM_OR_DASH = r"(?:\d+|-)"
# State row: serial, state-name, 5 religion ints, total. Some PDFs may have
# state name spanning words (e.g., "ARUNACHAL PRADESH"), so we use a greedy state-name
# match anchored on the trailing 6-number block.
STATE_ROW = re.compile(
    rf"^\s*(\d{{1,2}})\s+(.+?)\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+(\d+)\s*$"
)
TOTAL_ROW = re.compile(
    rf"^(TOTAL\s+\([^)]+\))\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+(\d+)\s*$"
)

RELIGION_COLS = ["hindu", "muslim", "sikh", "christian", "others"]


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


def parse_int_or_none(s: str) -> int | None:
    if s == "-":
        return None
    return int(s)


def extract() -> None:
    meta = verify_source_integrity()

    extraction_run = (
        f"ncrb-prison-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    all_rows: list[dict] = []
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        for table_id, category, page_num in TABLES:
            page = pdf.pages[page_num - 1]
            text = page.extract_text() or ""
            n_state_rows = 0
            n_total_rows = 0
            for line in text.splitlines():
                line = line.strip()
                m_state = STATE_ROW.match(line)
                m_total = TOTAL_ROW.match(line)
                if m_state:
                    g = m_state.groups()
                    serial = int(g[0])
                    state_name = g[1].strip()
                    religion_vals = [parse_int_or_none(g[2 + i]) for i in range(5)]
                    total = int(g[7])
                    for col, val in zip(RELIGION_COLS, religion_vals):
                        all_rows.append({
                            "table_id": table_id, "category": category, "page": page_num,
                            "row_type": "state", "serial": serial,
                            "geography_name": state_name, "religion": col, "value": val,
                            "row_total": total,
                        })
                    n_state_rows += 1
                elif m_total:
                    label = m_total.group(1)
                    religion_vals = [parse_int_or_none(m_total.group(2 + i)) for i in range(5)]
                    total = int(m_total.group(7))
                    for col, val in zip(RELIGION_COLS, religion_vals):
                        all_rows.append({
                            "table_id": table_id, "category": category, "page": page_num,
                            "row_type": "subtotal_or_total", "serial": None,
                            "geography_name": label, "religion": col, "value": val,
                            "row_total": total,
                        })
                    n_total_rows += 1
            print(f"  table {table_id} ({category}) p{page_num}: {n_state_rows} states + {n_total_rows} totals")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_id", "category", "page",
            "row_type", "serial", "geography_name", "religion", "value", "row_total",
        ])
        for r in all_rows:
            w.writerow([
                "ncrb-prison", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                r["table_id"], r["category"], r["page"],
                r["row_type"], r["serial"] if r["serial"] is not None else "",
                r["geography_name"], r["religion"],
                "" if r["value"] is None else r["value"],
                r["row_total"],
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(all_rows)} rows)")


if __name__ == "__main__":
    extract()
