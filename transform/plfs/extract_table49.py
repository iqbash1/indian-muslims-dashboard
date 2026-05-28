"""
L1 -> L2 for PLFS 2023-24 Table 49 (Employment status by religion).

Reads:  sources/plfs/annual/plfs-annual-report-2023-24.pdf (pages 401-402)
Writes: extracted/plfs/plfs-2023-24-table49-employment-status-by-religion.csv

Table 49 spans 2 pages, one religion per ~9-row section:
  Hinduism, Islam, Christianity (page 401)
  Sikhism, all (page 402)

Each religion section has 9 rows (rural/urban/rural+urban × male/female/person)
and 6 data columns + a constant 100.0 total:
  own_account_worker, helper_in_household, all_self_employed,
  regular_wage_salary, casual_labour, total(=100)
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
OUTPUT_PATH = REPO_ROOT / "extracted" / "plfs" / "plfs-2023-24-table49-employment-status-by-religion.csv"
PAGES = [401, 402]
EXTRACTOR_VERSION = "1.0.0"

RELIGION_MAP = {
    "Hinduism": "hindu",
    "Islam": "muslim",
    "Christianity": "christian",
    "Sikhism": "sikh",
    "all": "all",
}

# Map row label -> (residence, sex)
ROW_MAP = {
    "rural male":              ("rural", "male"),
    "rural female":            ("rural", "female"),
    "rural person":            ("rural", "person"),
    "urban male":              ("urban", "male"),
    "urban female":            ("urban", "female"),
    "urban person":            ("urban", "person"),
    "rural + urban male":      ("total", "male"),
    "rural + urban female":    ("total", "female"),
    "rural + urban person":    ("total", "person"),
}

COLUMNS = ["own_account_worker", "helper_in_household", "all_self_employed",
           "regular_wage_salary", "casual_labour"]

NUM = r"\d+\.\d+"
ROW_RE = re.compile(
    rf"^(.+?)\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+(100\.0)\s*$"
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

    extraction_run = (
        f"plfs-table49-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows: list[dict] = []
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        for pn in PAGES:
            page = pdf.pages[pn - 1]
            text = page.extract_text() or ""
            current_religion = None
            for line in text.splitlines():
                line = line.strip()
                # Religion section header
                m_rel = re.match(r"^Religion\s*:\s*(\w+)\s*$", line)
                if m_rel:
                    current_religion = RELIGION_MAP.get(m_rel.group(1))
                    continue
                if current_religion is None:
                    continue
                m = ROW_RE.match(line)
                if not m:
                    continue
                label = m.group(1).strip()
                if label not in ROW_MAP:
                    continue
                residence, sex = ROW_MAP[label]
                values = [float(m.group(i + 2)) for i in range(5)]
                for col, val in zip(COLUMNS, values):
                    rows.append({
                        "religion": current_religion,
                        "residence": residence,
                        "sex": sex,
                        "metric": col,
                        "value": val,
                        "page": pn,
                    })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table", "page", "religion", "residence", "sex", "metric", "value",
        ])
        for r in rows:
            w.writerow([
                "plfs", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                "49", r["page"],
                r["religion"], r["residence"], r["sex"], r["metric"], r["value"],
            ])

    religions = sorted({r["religion"] for r in rows})
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows; religions: {religions})")


if __name__ == "__main__":
    extract()
