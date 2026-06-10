"""
L1 -> L2 for AISHE 2020-21 Table 15 (state-wise enrolment in PWD and Minority).

Reads:  sources/aishe/aishe-report-2020-21.pdf (page 136)
Writes: extracted/aishe/aishe-2020-21-table15-state-minority-enrolment.csv

Sibling to extract_table15.py (which handles the 2021-22 report, page 140). Kept
separate so the committed 2021-22 L2 stays byte-identical: the two reports need
different handling of the West Bengal + All-India rows.

Table 15 columns: PWD (M/F/T) | Muslim (M/F/T) | Other Minority (M/F/T) | EWS (M/F/T).

Clean state rows (serials 1-35) parse from the text layer with the same regex as
the 2021-22 extractor. The bottom two rows (West Bengal, serial 36, and the
All-India aggregate) render character-interleaved in extract_text() output, but
at the CHARACTER level they sit on distinct y-coordinates (WB ~0.9pt above
All-India). So we recover both by re-extracting words with a tight y-tolerance
and taking the two 12-number rows with the largest `top` (WB then All-India).

This is verified correct against the 2021-22 report: the same word-level method
reproduces that report's published All-India Muslim total (2,108,033) and the
narrative-stated minority-by-sex totals exactly. For 2020-21 it yields All-India
Muslim 1,921,713 (= 4.64% of the 4,13,80,713 total enrolment on report p30,
matching the narrative's "4.6% Muslim Minority") and recovers West Bengal
(Muslim 238,170), which the 2021-22 text-layer extraction had to drop.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
from collections import defaultdict

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "sources" / "aishe" / "aishe-report-2020-21.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "aishe" / "aishe-2020-21-table15-state-minority-enrolment.csv"
TABLE_PAGE = 136
EXTRACTOR_VERSION = "1.0.0"

ROW_PATTERN = re.compile(
    r"^\s*(\d{1,2})\s+"
    r"(.+?)\s+"
    r"((?:\d[\d,]*\s+){11}\d[\d,]*)\s*$"
)

# State-name corrections where the PDF text layer wraps the name across lines.
STATE_NAME_OVERRIDES = {
    1: "Andaman and Nicobar Islands",                 # PDF wraps "Andaman and" to prior line
    32: "Dadra and Nagar Haveli and Daman and Diu",   # PDF wraps "The Dadra and Nagar"/"and Diu"
}

# Sanity filter: real per-state Muslim enrolment is <500k; any cell over 100M is a
# sign of character-interleaving garbage (the merged West Bengal + All-India row).
MAX_PLAUSIBLE_CELL = 100_000_000

COLS = ("pwd_male", "pwd_female", "pwd_total",
        "muslim_male", "muslim_female", "muslim_total",
        "other_minority_male", "other_minority_female", "other_minority_total",
        "ews_male", "ews_female", "ews_total")


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def parse_clean_rows(text: str) -> list[dict]:
    """Serials 1-35 from the text layer (the un-interleaved rows)."""
    out: list[dict] = []
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
            continue  # character-interleaved garbage row (West Bengal + All India)
        if not any(c.isalpha() for c in state):
            continue  # the "1 2 3 ... 14" column-index row
        if serial in STATE_NAME_OVERRIDES:
            state = STATE_NAME_OVERRIDES[serial]
        out.append({"serial": serial, "state_name": state,
                    **{c: nums[i] for i, c in enumerate(COLS)}})
    return out


def recover_wb_and_all_india(page) -> tuple[dict, dict]:
    """West Bengal (serial 36) + the All-India aggregate, de-interleaved by precise
    y-coordinate. Returns (west_bengal_row, all_india_row)."""
    words = page.extract_words(y_tolerance=1)
    by_top: dict[float, list] = defaultdict(list)
    for w in words:
        txt = w["text"].replace(",", "")
        if txt.isdigit():
            by_top[round(w["top"], 1)].append((w["x0"], int(txt)))
    twelves = [(top, [v for _, v in sorted(vs)])
               for top, vs in sorted(by_top.items()) if len(vs) == 12]
    if len(twelves) < 2:
        sys.exit("could not isolate the West Bengal + All-India 12-number rows")
    # The two largest `top` values are West Bengal (upper) then All India (lower).
    (_, wb_nums), (_, ai_nums) = twelves[-2], twelves[-1]
    wb = {"serial": 36, "state_name": "West Bengal",
          **{c: wb_nums[i] for i, c in enumerate(COLS)}}
    ai = {"serial": 0, "state_name": "All India",
          **{c: ai_nums[i] for i, c in enumerate(COLS)}}
    return wb, ai


def extract() -> None:
    meta = verify_source_integrity()
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        page = pdf.pages[TABLE_PAGE - 1]
        text = page.extract_text() or ""
        rows = parse_clean_rows(text)
        wb, all_india = recover_wb_and_all_india(page)

    # Internal consistency check: All-India Muslim M + F == Muslim total (a typo or
    # mis-deinterleave would break this).
    if all_india["muslim_male"] + all_india["muslim_female"] != all_india["muslim_total"]:
        sys.exit(f"All-India Muslim M+F != total: {all_india}")

    rows = sorted(rows + [wb], key=lambda r: r["serial"]) + [all_india]

    extraction_run = (
        f"aishe-table15-2020-21-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "source_document", "source_sha256_prefix",
                    "extraction_run", "page", "serial", "state_name", *COLS])
        for r in rows:
            w.writerow(["aishe", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                        meta["sha256"][:16], extraction_run, TABLE_PAGE,
                        r["serial"], r["state_name"], *(r[c] for c in COLS)])

    mus_total = all_india["muslim_total"]
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows; "
          f"35 states + West Bengal + All-India; All-India Muslim total {mus_total:,})")


if __name__ == "__main__":
    extract()
