"""
L1 -> L2 for Census 2011 C-1 Population by Religious Community.

Default reads:  sources/census-2011/c-series/c01-population-by-religion.xls
Default writes: extracted/census-2011/c01-population-by-religion.csv

Works on either the all-India MDDS file (states only) or a state-level MDDS
file (state + districts + sub-districts + towns + villages). Long-format:
one row per (area x residence x religion x sex). Verifies the source SHA256
matches its sidecar before extracting.

Usage:
  python extract_c01.py                                   # default all-India
  python extract_c01.py <source.xls> <output.csv>         # custom paths
  python extract_c01.py <source.xls> <output.csv> --district-only
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import sys

import xlrd

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_PATH = REPO_ROOT / "sources" / "census-2011" / "c-series" / "c01-population-by-religion.xls"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "extracted" / "census-2011" / "c01-population-by-religion.csv"
EXTRACTOR_VERSION = "1.1.0"

# Column layout per the multi-row header at rows 1-3 of the C01 sheet.
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


def verify_source_integrity(source_path: pathlib.Path) -> dict:
    meta_path = source_path.with_suffix(source_path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text())
    actual_sha = sha256_of(source_path)
    if actual_sha != meta["sha256"]:
        sys.exit(
            f"sha256 mismatch for {source_path.name}: "
            f"archive {actual_sha[:16]} != sidecar {meta['sha256'][:16]}"
        )
    return meta


def extract(source_path: pathlib.Path = DEFAULT_SOURCE_PATH,
            output_path: pathlib.Path = DEFAULT_OUTPUT_PATH,
            district_only: bool = False) -> None:
    source_path = source_path.resolve()
    output_path = output_path.resolve()
    meta = verify_source_integrity(source_path)
    book = xlrd.open_workbook(str(source_path))
    sheet = book.sheet_by_name("C01")

    extraction_run = (
        f"census-c01-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    n_skipped_granularity = 0
    with output_path.open("w", newline="") as f:
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

            # district_only mode: keep state and district granularity only
            # (skip sub-districts, towns, villages). Heuristic:
            #   tehsil_code != "00000" or town_code != "000000"  -> sub-district or below
            if district_only and (tehsil != "00000" or town != "000000"):
                n_skipped_granularity += 1
                continue

            for religion, base_col in RELIGION_COL_GROUPS:
                for sex_offset, sex in enumerate(SEX_LABELS):
                    raw = sheet.cell_value(r, base_col + sex_offset)
                    if raw == "" or raw is None:
                        continue
                    value = int(raw) if isinstance(raw, (int, float)) else int(float(raw))
                    w.writerow([
                        "census-india-2011",
                        str(source_path.relative_to(REPO_ROOT)),
                        meta["sha256"][:16],
                        extraction_run,
                        table, state, distt, tehsil, town,
                        area, residence, religion, sex, value,
                    ])
                    n_rows += 1

    skip_info = f" (skipped {n_skipped_granularity} sub-district+ rows)" if district_only else ""
    print(f"wrote {output_path.relative_to(REPO_ROOT)} ({n_rows} rows){skip_info}")


def main() -> None:
    p = argparse.ArgumentParser(description="Extract Census 2011 C-1 to L2 CSV.")
    p.add_argument("source", nargs="?", default=str(DEFAULT_SOURCE_PATH),
                   help="Source .xls path (default: all-India MDDS)")
    p.add_argument("output", nargs="?", default=str(DEFAULT_OUTPUT_PATH),
                   help="Output .csv path")
    p.add_argument("--district-only", action="store_true",
                   help="Keep only state + district granularity (skip sub-district / town / village)")
    args = p.parse_args()
    extract(pathlib.Path(args.source), pathlib.Path(args.output),
            district_only=args.district_only)


if __name__ == "__main__":
    main()
