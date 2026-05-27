"""
L1 -> L2 for NFHS-5 Table 7.2 (Early childhood mortality by background characteristics).

Reads:  sources/nfhs-5/reports/india-report-fr375.pdf (page 284)
Writes: extracted/nfhs-5/nfhs-5-table72-mortality-by-religion.csv

Table 7.2 is laid out dual-column (URBAN on the left, RURAL on the right).
pdfplumber linearizes each row, so a religion line in the text reads:
  "Hindu 18.4 8.5 26.9 4.9 31.7 Hindu 27.9 11.0 38.9 7.9 46.6"
i.e. religion + 5 urban numbers + religion + 5 rural numbers.

5 columns per side: NN (neonatal), PNN (postneonatal), IMR (1q0),
4q1 (child), 5q0 (under-5).
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
OUTPUT_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table72-mortality-by-religion.csv"
TABLE_PAGE = 284
EXTRACTOR_VERSION = "1.0.0"

RELIGIONS_RAW = ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist/Neo-Buddhist", "Other"]
RELIGION_NORM = {
    "Hindu": "hindu",
    "Muslim": "muslim",
    "Christian": "christian",
    "Sikh": "sikh",
    "Buddhist/Neo-Buddhist": "buddhist",
    "Other": "other",
}

# Match: <religion_word(s)> <5 numbers (poss. parenthesised)> <religion_word(s)> <5 numbers>
# Parens around values indicate "based on small sample" — we strip them.
NUM = r"\(?-?\d+(?:\.\d+)?\)?"
ROW_PATTERNS = {
    "Hindu":                 re.compile(rf"^Hindu\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+Hindu\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$"),
    "Muslim":                re.compile(rf"^Muslim\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+Muslim\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$"),
    "Christian":             re.compile(rf"^Christian\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+Christian\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$"),
    "Sikh":                  re.compile(rf"^Sikh\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+Sikh\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$"),
    "Buddhist/Neo-Buddhist": re.compile(rf"^Buddhist/Neo-Buddhist\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+Buddhist/Neo-Buddhist\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$"),
    "Other":                 re.compile(rf"^Other\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+Other\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s*$"),
}

METRIC_COLS = ["nn", "pnn", "imr", "child_4q1", "u5_5q0"]


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
    """Return (value, is_small_sample). Parentheses denote small-sample warnings."""
    is_small = s.startswith("(") and s.endswith(")")
    return float(s.strip("()")), is_small


def extract() -> None:
    meta = verify_source_integrity()

    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        page = pdf.pages[TABLE_PAGE - 1]
        text = page.extract_text() or ""

    extraction_run = (
        f"nfhs-table72-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows: list[dict] = []
    matched_religions: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        for raw_name, pattern in ROW_PATTERNS.items():
            m = pattern.match(line)
            if not m:
                continue
            g = m.groups()
            religion = RELIGION_NORM[raw_name]
            for residence, offset in (("urban", 0), ("rural", 5)):
                for col_idx, col in enumerate(METRIC_COLS):
                    raw = g[offset + col_idx]
                    val, small = parse_value(raw)
                    rows.append({
                        "religion": religion,
                        "residence": residence,
                        "metric": col,
                        "value": val,
                        "small_sample": small,
                    })
            matched_religions.add(raw_name)
            break

    missing = set(RELIGIONS_RAW) - matched_religions
    if missing:
        print(f"  WARN: missing religion rows: {sorted(missing)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table", "page",
            "religion", "residence", "metric", "value", "small_sample",
        ])
        for r in rows:
            w.writerow([
                "nfhs-5", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                "7.2", TABLE_PAGE,
                r["religion"], r["residence"], r["metric"], r["value"],
                "true" if r["small_sample"] else "false",
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows; {len(matched_religions)}/6 religions matched)")


if __name__ == "__main__":
    extract()
