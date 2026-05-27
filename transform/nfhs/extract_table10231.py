"""
L1 -> L2 for NFHS-5 Table 10.23.1 (Prevalence of anaemia in women 15-49).

Reads:  sources/nfhs-5/reports/india-report-fr375.pdf (page 468)
Writes: extracted/nfhs-5/nfhs-5-table10231-women-anaemia-by-religion.csv

Single-column religion rows (not dual like Table 7.2):
  "Hindu 25.7 29.0 2.7 57.4 558,120"
Columns: Mild (11-11.9 g/dl) | Moderate (8-10.9) | Severe (<8) | Any anaemia (<12) | N women

Also captures the "Total" row for the all-religion baseline.
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
SOURCE_PATH = REPO_ROOT / "sources" / "nfhs-5" / "reports" / "india-report-fr375.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table10231-women-anaemia-by-religion.csv"
TABLE_PAGE = 468
EXTRACTOR_VERSION = "1.0.0"

RELIGIONS = [
    ("Hindu", "hindu"),
    ("Muslim", "muslim"),
    ("Christian", "christian"),
    ("Sikh", "sikh"),
    ("Buddhist/Neo-Buddhist", "buddhist"),
    ("Jain", "jain"),
    ("Other", "other"),
]
METRIC_COLS = ["mild", "moderate", "severe", "any_anaemia"]

NUM = r"\(?-?\d+(?:\.\d+)?\)?"
INT_WITH_COMMA = r"[\d,]+"

# Hindu 25.7 29.0 2.7 57.4 558,120
ROW_RE = re.compile(
    rf"^([A-Za-z/]+(?:-[A-Za-z]+)?(?:/[A-Za-z]+)?)\s+"
    rf"({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({INT_WITH_COMMA})\s*$"
)

# Total 25.6 28.7 2.7 57.0 682,035
TOTAL_RE = re.compile(
    rf"^Total\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({INT_WITH_COMMA})\s*$"
)


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


def parse_value(s: str) -> tuple[float, bool]:
    is_small = s.startswith("(") and s.endswith(")")
    return float(s.strip("()")), is_small


def extract() -> None:
    meta = verify_source_integrity()

    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        page = pdf.pages[TABLE_PAGE - 1]
        text = page.extract_text() or ""

    extraction_run = (
        f"nfhs-table10231-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    # Track which religions we found; we look for the row pattern anywhere on the page
    # and filter by religion name.
    religion_name_set = {raw for raw, _ in RELIGIONS}
    norm = {raw: code for raw, code in RELIGIONS}

    rows: list[dict] = []
    in_religion_section = False
    for line in text.splitlines():
        line = line.strip()
        if line == "Religion":
            in_religion_section = True
            continue
        if in_religion_section:
            m = ROW_RE.match(line)
            if m:
                name = m.group(1)
                if name not in religion_name_set:
                    # Religion section ended (next section started, e.g. "Caste/tribe")
                    in_religion_section = False
                    continue
                vals = m.group(2), m.group(3), m.group(4), m.group(5)
                n_women = int(m.group(6).replace(",", ""))
                for col, raw_val in zip(METRIC_COLS, vals):
                    val, small = parse_value(raw_val)
                    rows.append({
                        "religion": norm[name],
                        "metric": col,
                        "value": val,
                        "n_women": n_women,
                        "small_sample": small,
                    })
            elif line and line != "Religion":
                # Hit a non-religion-row, religion section over
                in_religion_section = False

        # Always check for the all-religion Total row
        tm = TOTAL_RE.match(line)
        if tm:
            vals = tm.group(1), tm.group(2), tm.group(3), tm.group(4)
            n_women = int(tm.group(5).replace(",", ""))
            for col, raw_val in zip(METRIC_COLS, vals):
                val, small = parse_value(raw_val)
                rows.append({
                    "religion": "all",
                    "metric": col,
                    "value": val,
                    "n_women": n_women,
                    "small_sample": small,
                })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table", "page", "religion", "metric", "value", "n_women", "small_sample",
        ])
        for r in rows:
            w.writerow([
                "nfhs-5", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                "10.23.1", TABLE_PAGE,
                r["religion"], r["metric"], r["value"], r["n_women"],
                "true" if r["small_sample"] else "false",
            ])

    distinct_religions = {r["religion"] for r in rows}
    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({len(rows)} rows; {len(distinct_religions)} distinct religions: {sorted(distinct_religions)})"
    )


if __name__ == "__main__":
    extract()
