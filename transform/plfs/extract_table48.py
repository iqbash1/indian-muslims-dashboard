"""
L1 -> L2 for PLFS 2023-24 Table 48 (LFPR/WPR/UR by major religious groups).

Reads:  sources/plfs/annual/plfs-annual-report-2023-24.pdf (pages 396-400)
Writes: extracted/plfs/plfs-2023-24-table48-employment-by-religion.csv

Table 48 spans 5 pages, one religion per page (Hinduism, Islam,
Christianity, Sikhism, all). On each page, 6 indicator rows:
LFPR 15+, LFPR all-age, WPR 15+, WPR all-age, UR 15+, UR all-age.
Each row has 9 trailing numbers: rural(M/F/P), urban(M/F/P), total(M/F/P).
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
SOURCE_PATH = REPO_ROOT / "sources" / "plfs" / "annual" / "plfs-annual-report-2023-24.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "plfs" / "plfs-2023-24-table48-employment-by-religion.csv"
PAGES = range(396, 401)  # 1-indexed
EXTRACTOR_VERSION = "1.0.0"

RELIGION_MAP = {
    "Hinduism": "hindu",
    "Islam": "muslim",
    "Christianity": "christian",
    "Sikhism": "sikh",
    "all": "all",
}

NUM = r"(?:\d+\.\d+|\d+)"
ROW_PATTERN = re.compile(
    rf"^(.+?)\s+({NUM}(?:\s+{NUM}){{8}})\s*$"
)

# 9 cell labels in order
CELL_LABELS = [
    ("rural", "male"), ("rural", "female"), ("rural", "person"),
    ("urban", "male"), ("urban", "female"), ("urban", "person"),
    ("total", "male"), ("total", "female"), ("total", "person"),
]


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


def normalize_religion(raw: str) -> str | None:
    raw = raw.strip()
    return RELIGION_MAP.get(raw)


def identify_indicator_block(line: str) -> str | None:
    """Return 'LFPR' / 'WPR' / 'UR' if this is a section header line, else None."""
    if re.match(r"^Labour Force Participation Rate \(LFPR\)\s*$", line):
        return "LFPR"
    if re.match(r"^Worker Population Ratio \(WPR\)\s*$", line):
        return "WPR"
    if re.match(r"^Unemployment Rate \(UR\)\s*$", line):
        return "UR"
    return None


def extract() -> None:
    meta = verify_source_integrity()

    extraction_run = (
        f"plfs-table48-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    all_rows: list[dict] = []
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        for pn in PAGES:
            page = pdf.pages[pn - 1]
            text = page.extract_text() or ""
            religion = None
            indicator_block = None

            for line in text.splitlines():
                line = line.strip()
                if line.startswith("Religion:"):
                    religion = normalize_religion(line.split(":", 1)[1])
                    indicator_block = None
                    continue

                section = identify_indicator_block(line)
                if section is not None:
                    indicator_block = section
                    continue

                if religion is None or indicator_block is None:
                    continue

                m = ROW_PATTERN.match(line)
                if not m:
                    continue
                label = m.group(1)
                # Identify age cohort: '15 years and above' vs 'all age'
                if "15 years" in label:
                    age = "15plus"
                elif "all age" in label:
                    age = "all_age"
                else:
                    continue
                nums = [float(x) for x in m.group(2).split()]
                if len(nums) != 9:
                    continue
                for val, (residence, sex) in zip(nums, CELL_LABELS):
                    all_rows.append({
                        "religion": religion,
                        "indicator": indicator_block,
                        "age_cohort": age,
                        "residence": residence,
                        "sex": sex,
                        "value": val,
                        "page": pn,
                    })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table", "page",
            "religion", "indicator", "age_cohort", "residence", "sex", "value",
        ])
        for r in all_rows:
            w.writerow([
                "plfs", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                "48", r["page"],
                r["religion"], r["indicator"], r["age_cohort"],
                r["residence"], r["sex"], r["value"],
            ])

    distinct_religions = {r["religion"] for r in all_rows}
    distinct_indicators = {r["indicator"] for r in all_rows}
    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({len(all_rows)} rows; religions: {sorted(distinct_religions)}, "
        f"indicators: {sorted(distinct_indicators)})"
    )


if __name__ == "__main__":
    extract()
