"""
L1 -> L2 for NCRB Prison Statistics India 2020 — religion-by-category tables.
HINDI EDITION (the English 2020 Annual Report is not available in any
primary or Wayback archive; only the Hindi edition was archived).

Reads:  sources/ncrb-prison/psi-2020-hindi-ch2.pdf
        Tables 2.10C (convicts), 2.11C (undertrials), 2.12C (detenues),
        2.13C (other prisoners) at pages 33 / 37 / 41 / 45.
Writes: extracted/ncrb-prison/psi-2020-religion-by-state.csv  (same schema
        as the English-year L2s, so the existing canonicalizers pick it up
        automatically and 2020 fills the gap in the prison-share trend).

The Hindi tables have the EXACT SAME column layout as the English tables:
  क्रम सं. | राज्य/सं.शा.प्र. | हिन्दू | मुहलिम | हसक्ख | ईसाई | अन्य | कुि
  Sl.No   | State/UT         | Hindu | Muslim | Sikh | Christian | Others | Total
Numbers are Arabic numerals (language-neutral). Only the column headers,
state names, and subtotal labels are Devanagari — we ignore the Devanagari
text entirely and key on numeric structure (state row = "<digit(s)> <name>
<5 nums> <total>"). We sum religion columns across all 36 state/UT data
rows directly and synthesise a single "TOTAL (STATES)" subtotal row in the
L2 so the downstream canonicalizers (which filter on STATES/UTs subtotal
rows) pick it up. This deliberately collapses the English-edition's
STATES vs UTs subtotal distinction — the canonicalizers sum them anyway,
so the resulting Muslim share is identical to what a STATES+UTs split
would produce.

Validated: re-extracting yields a Muslim share between the 2019 (19.39%)
and 2021 (18.71%) values — expected for the COVID year given the
decongestion orders mid-2020 that disproportionately released undertrials.
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
SOURCE_PATH = REPO_ROOT / "sources" / "ncrb-prison" / "psi-2020-hindi-ch2.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "ncrb-prison" / "psi-2020-religion-by-state.csv"
EXTRACTOR_VERSION = "1.0.0"

# (table_id, category, 1-based page in this PDF)
TABLES = [
    ("2.10C", "convicts",    33),
    ("2.11C", "undertrials", 37),
    ("2.12C", "detenues",    41),
    ("2.13C", "other",       45),
]
RELIGION_COLS = ["hindu", "muslim", "sikh", "christian", "others"]

NUM_OR_DASH = r"(?:\d+|-)"
# State row: <serial> <state name in Devanagari> <5 religion nums> <total num>.
# The state name can contain any non-digit chars and spaces; we anchor on the
# trailing 6-number block.
STATE_ROW = re.compile(
    rf"^\s*(\d{{1,3}})\s+(.+?)\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+(\d+)\s*$"
)


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source_integrity() -> dict:
    meta = json.loads(SOURCE_PATH.with_suffix(SOURCE_PATH.suffix + ".meta.json").read_text())
    actual = sha256_of(SOURCE_PATH)
    if actual != meta["sha256"]:
        sys.exit(f"sha256 mismatch for {SOURCE_PATH.name}: archive {actual[:16]} != sidecar {meta['sha256'][:16]}")
    return meta


def parse_int_or_none(s: str) -> int | None:
    return None if s == "-" else int(s)


def extract() -> None:
    meta = verify_source_integrity()
    extraction_run = (
        f"ncrb-prison-2020-hindi-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    all_rows: list[dict] = []
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        for table_id, category, page in TABLES:
            text = pdf.pages[page - 1].extract_text() or ""
            state_rows = []
            for line in text.splitlines():
                m = STATE_ROW.match(line.strip())
                if not m:
                    continue
                g = m.groups()
                vals = [parse_int_or_none(g[2 + k]) for k in range(5)]
                total = int(g[7])
                state_rows.append({
                    "serial": int(g[0]),
                    "geography_name": g[1].strip(),  # Devanagari, preserved verbatim
                    "values": vals,
                    "row_total": total,
                })

            # Emit state rows
            for sr in state_rows:
                for col, val in zip(RELIGION_COLS, sr["values"]):
                    all_rows.append({
                        "table_id": table_id, "category": category, "page": page,
                        "row_type": "state", "serial": sr["serial"],
                        "geography_name": sr["geography_name"],
                        "religion": col, "value": val, "row_total": sr["row_total"],
                    })

            # Synthesise a single TOTAL (STATES) subtotal so the downstream
            # canonicalizer picks it up (it filters on STATES/UTs subtotal rows
            # and sums religion columns across them — collapsing STATES + UTs).
            religion_sums = [0] * 5
            row_total_sum = 0
            for sr in state_rows:
                row_total_sum += sr["row_total"]
                for k, v in enumerate(sr["values"]):
                    if v is not None:
                        religion_sums[k] += v
            for col, total in zip(RELIGION_COLS, religion_sums):
                all_rows.append({
                    "table_id": table_id, "category": category, "page": page,
                    "row_type": "subtotal_or_total", "serial": None,
                    "geography_name": "TOTAL (STATES)",  # collapsed states+UTs; see docstring
                    "religion": col, "value": total, "row_total": row_total_sum,
                })
            print(f"  {table_id} ({category}) p{page}: {len(state_rows)} states, religion_sums={religion_sums}")

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
