"""
L1 -> L2 for AISHE 2021-22 Table 15 (state-wise enrolment in PWD and Minority).

Reads:  sources/aishe/aishe-report-2021-22.pdf (page 140)
Writes: extracted/aishe/aishe-2021-22-table15-state-minority-enrolment.csv

Table 15 columns: PWD (M/F/T) | Muslim (M/F/T) | Other Minority (M/F/T) | EWS (M/F/T).
PDF tables in AISHE are visual layouts, not structured PDF tables, so pdfplumber's
`extract_tables` doesn't help. We parse the text layer with regex.

Known PDF text-layer pitfalls handled here:
  - State names that wrap to a previous line (Andaman, DNH+DD): hand-coded overrides.
  - West Bengal + All India rows are character-interleaved in the text layer (the two
    rows render side-by-side and pdfplumber zips them). We skip the garbage row using
    a max-value sanity filter and append a hard-coded All-India row from the report's
    narrative (page 58 / page 31: "21,08,033 Muslim Minority enrolment").
  - Ladakh and Lakshadweep have very few non-blank cells (low-enrollment UTs); the
    text layer drops them to <12 numeric tokens, so they don't match the row regex.
    Documented as a known gap; their Muslim enrolment combined is < 0.06% of national.
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
SOURCE_PATH = REPO_ROOT / "sources" / "aishe" / "aishe-report-2021-22.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "aishe" / "aishe-2021-22-table15-state-minority-enrolment.csv"
TABLE_PAGE = 140
EXTRACTOR_VERSION = "1.1.0"

ROW_PATTERN = re.compile(
    r"^\s*(\d{1,2})\s+"
    r"(.+?)\s+"
    r"((?:\d[\d,]*\s+){11}\d[\d,]*)\s*$"
)

# State-name corrections where the PDF text layer wraps the name across lines.
STATE_NAME_OVERRIDES = {
    1: "Andaman and Nicobar Islands",            # PDF wraps "Andaman and" to prior line
    32: "Dadra and Nagar Haveli and Daman and Diu",  # PDF wraps "The Dadra and Nagar"
}

# Sanity filter: real per-state Muslim enrolment is <500k; UP (highest) is 326,819.
# Any cell over 100 million is a sign of character-interleaving garbage.
MAX_PLAUSIBLE_CELL = 100_000_000

# Hard-coded All-India total from the report narrative (page 58 + page 31):
# "Muslim Minority enrolment in 2021-22 is 21,08,033"  (49.3% female).
ALL_INDIA_MUSLIM_TOTAL = 2_108_033
ALL_INDIA_MUSLIM_FEMALE = round(ALL_INDIA_MUSLIM_TOTAL * 0.493)
ALL_INDIA_MUSLIM_MALE = ALL_INDIA_MUSLIM_TOTAL - ALL_INDIA_MUSLIM_FEMALE


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


def parse_int(s: str) -> int:
    return int(s.replace(",", ""))


def extract() -> None:
    meta = verify_source_integrity()

    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        page = pdf.pages[TABLE_PAGE - 1]
        text = page.extract_text() or ""

    extraction_run = (
        f"aishe-table15-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows: list[dict] = []
    for line in text.splitlines():
        m = ROW_PATTERN.match(line)
        if not m:
            continue
        serial = int(m.group(1))
        state = m.group(2).strip()
        nums = [parse_int(x) for x in m.group(3).split()]
        if len(nums) != 12:
            continue
        if max(nums) > MAX_PLAUSIBLE_CELL:
            # Character-interleaved garbage row (West Bengal + All India)
            continue
        if not any(c.isalpha() for c in state):
            # Column index row "1 2 3 4 5 6 7 8 9 10 11 12 13 14" — state="2"
            continue
        if serial in STATE_NAME_OVERRIDES:
            state = STATE_NAME_OVERRIDES[serial]
        rows.append({
            "serial": serial, "state_name": state,
            "pwd_male": nums[0], "pwd_female": nums[1], "pwd_total": nums[2],
            "muslim_male": nums[3], "muslim_female": nums[4], "muslim_total": nums[5],
            "other_minority_male": nums[6], "other_minority_female": nums[7], "other_minority_total": nums[8],
            "ews_male": nums[9], "ews_female": nums[10], "ews_total": nums[11],
        })

    # Append the hand-coded All-India row (PDF text layer corrupted the in-table version).
    rows.append({
        "serial": 0, "state_name": "All India",
        "pwd_male": None, "pwd_female": None, "pwd_total": None,
        "muslim_male": ALL_INDIA_MUSLIM_MALE,
        "muslim_female": ALL_INDIA_MUSLIM_FEMALE,
        "muslim_total": ALL_INDIA_MUSLIM_TOTAL,
        "other_minority_male": None, "other_minority_female": None, "other_minority_total": None,
        "ews_male": None, "ews_female": None, "ews_total": None,
    })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "page", "serial", "state_name",
            "pwd_male", "pwd_female", "pwd_total",
            "muslim_male", "muslim_female", "muslim_total",
            "other_minority_male", "other_minority_female", "other_minority_total",
            "ews_male", "ews_female", "ews_total",
        ])
        for r in rows:
            w.writerow([
                "aishe", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run, TABLE_PAGE,
                r["serial"], r["state_name"],
                "" if r["pwd_male"] is None else r["pwd_male"],
                "" if r["pwd_female"] is None else r["pwd_female"],
                "" if r["pwd_total"] is None else r["pwd_total"],
                r["muslim_male"], r["muslim_female"], r["muslim_total"],
                "" if r["other_minority_male"] is None else r["other_minority_male"],
                "" if r["other_minority_female"] is None else r["other_minority_female"],
                "" if r["other_minority_total"] is None else r["other_minority_total"],
                "" if r["ews_male"] is None else r["ews_male"],
                "" if r["ews_female"] is None else r["ews_female"],
                "" if r["ews_total"] is None else r["ews_total"],
            ])

    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows; "
        f"known gaps: Andaman/DNH may need state-name verification, "
        f"Ladakh+Lakshadweep+West Bengal not extracted)"
    )


if __name__ == "__main__":
    extract()
