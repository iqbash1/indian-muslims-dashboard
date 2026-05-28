"""
L1 -> L2 for NFHS-5 Table 2.4 (Access to a toilet facility by background).

Reads:  sources/nfhs-5/reports/india-report-fr375.pdf (page 74)
Writes: extracted/nfhs-5/nfhs-5-table24-toilet-access-by-religion.csv

Page is dual-column (Table 2.4 left, Table 2.5 state-wise right). Religion
rows of Table 2.4 have format:
  "<religion_name> <urban_%> <rural_%> <total_%> [optional state label]"
Each religion has 3 numbers (urban/rural/total household % with toilet access).
The trailing text (region/state names) is from the right-column table and ignored.

"India" appears as the all-religion total row (it's labeled as the header but
the numbers on that line are the all-India totals).
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
OUTPUT_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table24-toilet-access-by-religion.csv"
TABLE_PAGE = 74
EXTRACTOR_VERSION = "1.0.0"

RELIGION_MAP = {
    "India": "all",
    "Hindu": "hindu",
    "Muslim": "muslim",
    "Christian": "christian",
    "Sikh": "sikh",
    "Buddhist/Neo-Buddhist": "buddhist",
    "Jain": "jain",
    "Other": "other",
}
RESIDENCES = ["urban", "rural", "total"]

NUM = r"\d+\.\d+"
# Each religion line: name, 3 numbers, then anything (ignored).
# The "India" line is prefixed by "Religion of household head" — so we also
# allow that prefix.
ROW_RE = re.compile(
    rf"^(?:Religion of household head\s+)?"
    rf"([A-Za-z/]+(?:-[A-Za-z]+)?(?:/[A-Za-z]+)?)\s+"
    rf"({NUM})\s+({NUM})\s+({NUM})"
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


def extract() -> None:
    meta = verify_source_integrity()
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        text = pdf.pages[TABLE_PAGE - 1].extract_text() or ""

    extraction_run = (
        f"nfhs-table24-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows: list[dict] = []
    captured: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        m = ROW_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        if name not in RELIGION_MAP:
            continue
        if name in captured:
            continue  # take first hit only
        captured.add(name)
        religion = RELIGION_MAP[name]
        vals = [float(m.group(2)), float(m.group(3)), float(m.group(4))]
        for residence, val in zip(RESIDENCES, vals):
            rows.append({
                "religion": religion,
                "residence": residence,
                "metric": "toilet_access_pct",
                "value": val,
            })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table", "page", "religion", "residence", "metric", "value",
        ])
        for r in rows:
            w.writerow([
                "nfhs-5", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                "2.4", TABLE_PAGE,
                r["religion"], r["residence"], r["metric"], r["value"],
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows; "
          f"religions: {sorted(captured)})")


if __name__ == "__main__":
    extract()
