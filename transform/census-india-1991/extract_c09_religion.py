"""
L1 -> L2 for Census 1991 C-9 Religion (population by religious community).

Reads:  sources/census-1991/c09-religion.xlsx  (sheet "C09T")
Writes: extracted/census-1991/c09-religion.csv

The 1991 Census's C-9 RELIGION table (do not confuse with later "C-9" which
was renumbered to mean education-by-religion). Religion-by-residence-by-sex
counts at India / state / district level. India row is "Excluding J&K"
because the 1991 Census was not held there.

Long-format output: one row per (area x residence x religion x sex). Each
religion block in the source occupies 3 consecutive columns: persons / males
/ females, starting at col 6 for "Total" and offsetting by 3 per religion.
Verifies the source SHA256 against its sidecar before extracting.
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
SOURCE_PATH = REPO_ROOT / "sources" / "census-1991" / "c09-religion.xlsx"
OUTPUT_PATH = REPO_ROOT / "extracted" / "census-1991" / "c09-religion.csv"
EXTRACTOR_VERSION = "1.0.0"
SHEET_NAME = "C09T"

# 1-indexed column positions per the XLSX header (row 10 carries 1..32 ruler).
# Each religion occupies 3 consecutive columns: persons, males, females.
RELIGION_COL_GROUPS = [
    ("all", 6),
    ("hindu", 9),
    ("muslim", 12),
    ("christian", 15),
    ("sikh", 18),
    ("buddhist", 21),
    ("jain", 24),
    ("other", 27),       # "Other Religions and Persuasions"
    ("not_stated", 30),  # "Religion not stated"
]
SEX_LABELS = ["persons", "males", "females"]
RESIDENCE_MAP = {"Total": "total", "Rural": "rural", "Urban": "urban"}
DATA_START_ROW = 11  # row 11 is the first data row (India Excluding J&K)


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


def _norm_name(area: str) -> tuple[str, str]:
    """
    Map 1991 area-name strings to (level, clean_name).

    Examples:
      "India Excluding (J&K)"  -> ("national", "India")
      "State-Andhra Pradesh"   -> ("state", "Andhra Pradesh")
      "District-Srikakulam"    -> ("district", "Srikakulam")
    """
    a = (area or "").strip()
    if a.startswith("India"):
        return "national", a
    if a.startswith("State-"):
        return "state", a[len("State-"):].strip()
    if a.startswith("District-"):
        return "district", a[len("District-"):].strip()
    return "other", a


def extract() -> None:
    meta = verify_source_integrity()
    wb = openpyxl.load_workbook(str(SOURCE_PATH), data_only=True, read_only=True)
    ws = wb[SHEET_NAME]

    extraction_run = (
        f"census1991-c09-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_name", "state_code", "distt_code",
            "area_name", "area_level", "residence", "religion", "sex", "value",
        ])

        for row in ws.iter_rows(min_row=DATA_START_ROW, values_only=True):
            # row is a tuple of 32 cells (1-indexed → row[0] = col 1)
            if not row or not row[0]:
                continue
            table = str(row[0]).strip()
            state = str(row[1] or "").strip()
            distt = str(row[2] or "").strip()
            area = str(row[3] or "").strip()
            tru = str(row[4] or "").strip()
            residence = RESIDENCE_MAP.get(tru)
            if residence is None or not area:
                continue
            level, clean = _norm_name(area)

            for religion, base_col in RELIGION_COL_GROUPS:
                for sex_offset, sex in enumerate(SEX_LABELS):
                    raw = row[base_col - 1 + sex_offset]  # back to 0-indexed
                    if raw is None or raw == "":
                        continue
                    try:
                        value = int(raw) if isinstance(raw, (int, float)) else int(float(raw))
                    except (TypeError, ValueError):
                        continue
                    w.writerow([
                        "census-india-1991",
                        str(SOURCE_PATH.relative_to(REPO_ROOT)),
                        meta["sha256"][:16],
                        extraction_run,
                        table, state, distt,
                        clean, level, residence, religion, sex, value,
                    ])
                    n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    extract()
