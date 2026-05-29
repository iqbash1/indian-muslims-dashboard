"""
L1 -> L2 for Census 2001 C-1 Population by Religious Community.

Reads:  sources/census-2001/c-series/c01-population-by-religion.xls  (sheet "C01T")
Writes: extracted/census-2001/c01-population-by-religion.csv

All-India 2001 C-1 file: national + states/UTs (no districts), one block per
(area x residence). Long-format output: one row per (area x residence x
religion x sex). Column layout is identical to the 2011 C-1 MDDS file — each
religion occupies 3 consecutive columns (persons, males, females) starting at
col 7 — only the sheet name differs ("C01T" vs "C01"). Verifies the source
SHA256 against its sidecar before extracting.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import sys

import xlrd

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "sources" / "census-2001" / "c-series" / "c01-population-by-religion.xls"
OUTPUT_PATH = REPO_ROOT / "extracted" / "census-2001" / "c01-population-by-religion.csv"
EXTRACTOR_VERSION = "1.0.0"
SHEET_NAME = "C01T"

# Each religion occupies 3 consecutive columns: persons, males, females.
RELIGION_COL_GROUPS = [
    ("all", 7),
    ("hindu", 10),
    ("muslim", 13),
    ("christian", 16),
    ("sikh", 19),
    ("buddhist", 22),
    ("jain", 25),
    ("other", 28),       # "Other religions and persuasions"
    ("not_stated", 31),  # "Religion not stated"
]
SEX_LABELS = ["persons", "males", "females"]
RESIDENCE_MAP = {"Total": "total", "Rural": "rural", "Urban": "urban"}


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
    book = xlrd.open_workbook(str(SOURCE_PATH))
    sheet = book.sheet_by_name(SHEET_NAME)

    extraction_run = (
        f"census2001-c01-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_name", "state_code", "distt_code", "tehsil_code", "town_code",
            "area_name", "residence", "religion", "sex", "value",
        ])

        for r in range(7, sheet.nrows):
            area = str(sheet.cell_value(r, 5)).strip()
            tru = str(sheet.cell_value(r, 6)).strip()
            if not area or not tru:
                continue
            residence = RESIDENCE_MAP.get(tru)
            if residence is None:
                continue

            table = str(sheet.cell_value(r, 0)).strip()
            state = str(sheet.cell_value(r, 1)).strip()
            distt = str(sheet.cell_value(r, 2)).strip()
            tehsil = str(sheet.cell_value(r, 3)).strip()
            town = str(sheet.cell_value(r, 4)).strip()

            for religion, base_col in RELIGION_COL_GROUPS:
                for sex_offset, sex in enumerate(SEX_LABELS):
                    raw = sheet.cell_value(r, base_col + sex_offset)
                    if raw == "" or raw is None:
                        continue
                    value = int(raw) if isinstance(raw, (int, float)) else int(float(raw))
                    w.writerow([
                        "census-india-2001",
                        str(SOURCE_PATH.relative_to(REPO_ROOT)),
                        meta["sha256"][:16],
                        extraction_run,
                        table, state, distt, tehsil, town,
                        area, residence, religion, sex, value,
                    ])
                    n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    extract()
