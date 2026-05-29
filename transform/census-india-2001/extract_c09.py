"""
L1 -> L2 for Census 2001 C-9 Educational Level by Religious Community.

Reads:  sources/census-2001/c-series/c09-education-by-religion.xls  (sheet "Sheet1")
Writes: extracted/census-2001/c09-education-by-religion.csv

Slim, purpose-built extract for the `lit-7plus` metric. Like the 2011 C-9
extractor it keeps only the Total Population / Illiterate / Literate measures
(not the educational-level breakdowns). It additionally keeps only the three
age-group rows the literacy formula needs — "Total", "0-6", "Age not stated"
— because the 2001 file carries every single-year age 7..19 plus broad bands
(21 age groups in all), and no current metric uses them. Re-extract from the
archived L1 .xls if a future metric needs the full age distribution.

The 2001 layout matches the 2011 C-9 in content but differs in column
positions: this BIFF .xls has Table/State/Distt/Tehsil/Area/TRU/Religion/Age
in cols 0-7, then the three measures as persons/males/females triplets at
cols 8, 11, 14.  Verifies the source SHA256 against its sidecar first.
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
SOURCE_PATH = REPO_ROOT / "sources" / "census-2001" / "c-series" / "c09-education-by-religion.xls"
OUTPUT_PATH = REPO_ROOT / "extracted" / "census-2001" / "c09-education-by-religion.csv"
EXTRACTOR_VERSION = "1.0.0"
SHEET_NAME = "Sheet1"

# Each measure occupies 3 consecutive columns: persons, males, females.
MEASURE_COL_GROUPS = [
    ("total_population", 8),
    ("illiterate", 11),
    ("literate", 14),
]
SEX_LABELS = ["persons", "males", "females"]
RESIDENCE_MAP = {"Total": "total", "Rural": "rural", "Urban": "urban"}
RELIGION_MAP = {
    "All Religious Communities": "all",
    "Hindu": "hindu",
    "Muslim": "muslim",
    "Christian": "christian",
    "Sikh": "sikh",
    "Buddhist": "buddhist",
    "Jain": "jain",
    "Other Religious Communities": "other",
}
KEEP_AGE_GROUPS = {"Total", "0-6", "Age not stated"}


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
        f"census2001-c09-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    n_skipped_religion = 0

    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_name", "state_code", "area_name", "residence", "religion",
            "age_group", "measure", "sex", "value",
        ])

        for r in range(7, sheet.nrows):
            area = str(sheet.cell_value(r, 4)).strip()
            tru_raw = str(sheet.cell_value(r, 5)).strip()
            religion_raw = str(sheet.cell_value(r, 6)).strip()
            age_raw = sheet.cell_value(r, 7)
            if not area or not tru_raw or not religion_raw:
                continue

            residence = RESIDENCE_MAP.get(tru_raw)
            if residence is None:
                continue
            age = str(age_raw).strip()
            if age not in KEEP_AGE_GROUPS:
                continue
            religion = RELIGION_MAP.get(religion_raw)
            if religion is None:
                n_skipped_religion += 1
                continue

            table = str(sheet.cell_value(r, 0)).strip()
            state = str(sheet.cell_value(r, 1)).strip()

            for measure, base_col in MEASURE_COL_GROUPS:
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
                        table, state, area, residence, religion,
                        age, measure, sex, value,
                    ])
                    n_rows += 1

    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({n_rows} rows; skipped {n_skipped_religion} unknown-religion; "
        f"age groups kept: {sorted(KEEP_AGE_GROUPS)})"
    )


if __name__ == "__main__":
    extract()
