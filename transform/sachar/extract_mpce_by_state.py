#!/usr/bin/env python3
"""L1 -> L2 for Sachar Committee Appendix Tables 8.2 + 8.3 (state-level MPCE by
socio-religious category, NSS 61st round 2004-05).

Reads:  sources/sachar-committee-2006/sachar-comm-report-india-2006.pdf
        - Appendix Table 8.2 (PDF page 385): State level URBAN MPCE
        - Appendix Table 8.3 (PDF page 386): State level RURAL MPCE
Writes: extracted/sachar/sachar-mpce-by-state.csv

Both tables share the layout: one row per state (plus All India + an "All other
States" residual), seven money columns in current 2004-05 rupees:
  All | Hindus-All | Hindus-SC/ST | Hindus-OBC | Hindus-General | Muslims | All-Others
The text layer is clean and space-separated, so a regex over the page lines is
robust. Verified anchors: All-India Muslim urban 804 / rural 553; All-India All
urban 1105 / rural 579.
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
SOURCE_PATH = REPO_ROOT / "sources" / "sachar-committee-2006" / "sachar-comm-report-india-2006.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "sachar" / "sachar-mpce-by-state.csv"
EXTRACTOR_VERSION = "1.0.0"

# (residence, PDF page index (0-based), appendix-table label)
TABLES = [
    ("urban", 384, "Appendix Table 8.2"),
    ("rural", 385, "Appendix Table 8.3"),
]

# Seven money columns, in printed order.
VALUE_COLS = ("all", "hindu_all", "hindu_sc_st", "hindu_obc", "hindu_general",
              "muslim", "all_others")

# state name + exactly 7 integers
ROW_PATTERN = re.compile(r"^([A-Za-z][A-Za-z .&]+?)\s+((?:\d+\s+){6}\d+)\s*$")


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source_integrity() -> dict:
    meta = json.loads(pathlib.Path(str(SOURCE_PATH) + ".meta.json").read_text())
    actual = sha256_of(SOURCE_PATH)
    if actual != meta["sha256"]:
        sys.exit(f"sha256 mismatch for {SOURCE_PATH.name}: {actual[:16]} != {meta['sha256'][:16]}")
    return meta


def parse_table(text: str, residence: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        m = ROW_PATTERN.match(line.strip())
        if not m:
            continue
        state = m.group(1).strip()
        # Skip the two header lines ("States All Hindus Muslims All-Others" has no
        # 7-int tail; the "All Hindus SCs/STs OBCs General" sub-header likewise).
        if state.lower() in ("states", "all hindus"):
            continue
        nums = [int(x) for x in m.group(2).split()]
        if len(nums) != 7:
            continue
        rows.append({"state_name": state, "residence": residence,
                     **{c: nums[i] for i, c in enumerate(VALUE_COLS)}})
    return rows


def extract() -> None:
    meta = verify_source_integrity()
    extraction_run = (
        f"sachar-mpce-by-state-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    all_rows: list[dict] = []
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        for residence, page_idx, label in TABLES:
            text = pdf.pages[page_idx].extract_text() or ""
            rows = parse_table(text, residence)
            for r in rows:
                r["page"] = page_idx + 1
                r["table"] = label
            # Anchor check: the All-India Muslim cell must match the known values.
            ai = next((r for r in rows if r["state_name"].lower() == "all india"), None)
            expect = {"urban": 804, "rural": 553}[residence]
            if not ai or ai["muslim"] != expect:
                sys.exit(f"{label} ({residence}): All-India Muslim != {expect} "
                         f"(got {ai['muslim'] if ai else 'no All India row'})")
            all_rows.extend(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "source_document", "source_sha256_prefix", "extraction_run",
                    "page", "table", "state_name", "residence", *VALUE_COLS])
        for r in all_rows:
            w.writerow(["sachar-committee-2006", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                        meta["sha256"][:16], extraction_run, r["page"], r["table"],
                        r["state_name"], r["residence"], *(r[c] for c in VALUE_COLS)])

    n_urban = sum(1 for r in all_rows if r["residence"] == "urban")
    n_rural = sum(1 for r in all_rows if r["residence"] == "rural")
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(all_rows)} rows; "
          f"{n_urban} urban + {n_rural} rural)")


if __name__ == "__main__":
    extract()
