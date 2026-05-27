"""
L1 -> L2 for NFHS-5 Table 8.13 (Place of delivery by background characteristics).

Reads:  sources/nfhs-5/reports/india-report-fr375.pdf (page 324)
Writes: extracted/nfhs-5/nfhs-5-table813-place-of-delivery-by-religion.csv

The page is dual-column (Table 8.12 on left, 8.13 on right). pdfplumber
linearizes them, so religion rows have data from BOTH tables interleaved
on the same line. Table 8.13 columns (right): public, ngo, private, home,
home_with_skilled, other, missing, total, % institutional delivery, N.
Total live births at end. We want the institutional-delivery percentage
(col 9 from the right table).
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
OUTPUT_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table813-place-of-delivery-by-religion.csv"
TABLE_PAGE = 324
EXTRACTOR_VERSION = "1.0.0"

RELIGIONS = [
    ("Hindu", "hindu"), ("Muslim", "muslim"), ("Christian", "christian"),
    ("Sikh", "sikh"), ("Buddhist/Neo-Buddhist", "buddhist"),
    ("Jain", "jain"), ("Other", "other"),
]

# Religion lines have 8 cols from Table 8.12 then 8 cols from Table 8.13, then
# the institutional-delivery % and N from Table 8.13. From sample:
#   "Hindu 63.3 0.4 25.8 8.8 1.3 0.1 0.2 100.0 89.5 183,338"
# 10 numbers after religion name on the right table:
#   - cols 1-7: place distribution (public, ngo, private, home, home_skilled, other, missing)
#   - col 8: total (100.0)
#   - col 9: % delivered in health facility = INSTITUTIONAL DELIVERY (what we want)
#   - col 10: N live births (formatted with commas)
NUM = r"(?:\d+\.\d+|\d+)"
ROW_RE = re.compile(
    rf"^([A-Za-z/]+(?:-[A-Za-z]+)?(?:/[A-Za-z]+)?)\s+"
    rf"({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+"
    rf"(100\.0)\s+({NUM})\s+([\d,]+)\s*$"
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
        f"nfhs-table813-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    norm = {raw: code for raw, code in RELIGIONS}
    rows: list[dict] = []
    in_religion = False
    for line in text.splitlines():
        line = line.strip()
        if line == "Religion":
            in_religion = True
            continue
        if not in_religion:
            continue
        m = ROW_RE.match(line)
        if not m:
            # Religion section ended (e.g. "Caste/tribe" line)
            if line and not line[0].isdigit():
                in_religion = False
            continue
        name = m.group(1)
        if name not in norm:
            in_religion = False
            continue
        inst_delivery = float(m.group(10))
        n_births = int(m.group(11).replace(",", ""))
        rows.append({
            "religion": norm[name],
            "metric": "institutional_delivery",
            "value": inst_delivery,
            "n_live_births": n_births,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table", "page", "religion", "metric", "value", "n_live_births",
        ])
        for r in rows:
            w.writerow([
                "nfhs-5", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                "8.13", TABLE_PAGE,
                r["religion"], r["metric"], r["value"], r["n_live_births"],
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows; religions: {sorted(r['religion'] for r in rows)})")


if __name__ == "__main__":
    extract()
