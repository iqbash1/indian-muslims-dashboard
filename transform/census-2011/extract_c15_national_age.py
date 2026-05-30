"""
L1 -> L2 for Census 2011 Table C-15 — national population by religion x age group.

Reads:  sources/census-2011/c-series/c15-religion-by-age-sex.xlsx
Writes: extracted/census-2011/c15-national-age-by-religion.csv

C-15 lists, for each (State/UT, residence) x age group, the population of each
of seven religious communities (Hindu, Muslim, Christian, Sikh, Buddhist, Jain,
Other) plus the all-religions Total — separately for Persons, Males, Females.
This extractor pulls the NATIONAL TOTAL-RESIDENCE Persons rows for every age
group; downstream metrics (e.g. ger-higher-ed) combine specific bands to form
denominators.

Column map (verified row 2-3 headers):
  col 1-6 : Table | State | Distt | Total/Rural/Urban | Area | Age-group
  col 7-9 : Total Persons | Males | Females
  col 10-12 : Hindu Persons/Males/Females
  col 13-15 : Muslim ...; 16-18 Christian; 19-21 Sikh; 22-24 Buddhist;
  col 25-27 : Jain; 28-30 Other religions and persuasions.
We emit only Persons (col offset 0 within each block).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import sys

import openpyxl

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "sources" / "census-2011" / "c-series" / "c15-religion-by-age-sex.xlsx"
OUTPUT_PATH = REPO_ROOT / "extracted" / "census-2011" / "c15-national-age-by-religion.csv"
EXTRACTOR_VERSION = "1.0.0"

# religion -> (column index for Persons, 1-based)
RELIGION_COLS = [
    ("all",       7),
    ("hindu",     10),
    ("muslim",    13),
    ("christian", 16),
    ("sikh",      19),
    ("buddhist",  22),
    ("jain",      25),
    ("other",     28),
]


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
        sys.exit(f"sha256 mismatch for {SOURCE_PATH.name}")
    return meta


def extract() -> None:
    meta = verify_source_integrity()
    extraction_run = (
        f"census-c15-national-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    wb = openpyxl.load_workbook(str(SOURCE_PATH), data_only=True, read_only=True)
    sh = wb.active
    rows_out: list[dict] = []
    for row in sh.iter_rows(values_only=True):
        if not row or len(row) < 30:
            continue
        # filter to national, total-residence
        state_code = row[1]
        area_name = row[4]
        residence = row[3]
        if str(state_code) != "00" or str(area_name).strip().upper() != "INDIA":
            continue
        if str(residence).strip().lower() != "total":
            continue
        age_group = row[5]
        if not age_group:
            continue
        for rel, col_idx in RELIGION_COLS:
            val = row[col_idx - 1]
            if val is None or val == "":
                continue
            try:
                ival = int(val)
            except (ValueError, TypeError):
                continue
            rows_out.append({
                "age_group": str(age_group).strip(),
                "religion": rel,
                "persons": ival,
            })

    if not rows_out:
        sys.exit("no national C-15 rows found")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_name", "geography_level", "geography_code", "area_name",
            "residence", "age_group", "religion", "persons",
        ])
        for r in rows_out:
            w.writerow([
                "census-india-2011", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                "C1500", "national", "IN", "INDIA",
                "total", r["age_group"], r["religion"], r["persons"],
            ])
    n_age = len({r["age_group"] for r in rows_out})
    n_rel = len({r["religion"] for r in rows_out})
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows_out)} rows, "
          f"{n_age} age groups x {n_rel} religions)")


if __name__ == "__main__":
    extract()
