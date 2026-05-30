"""
L1 -> L2 for NCRB Prison Statistics India — religion-by-category tables.

MULTI-YEAR (v2). Extracts Tables 2.10C (convicts), 2.11C (undertrials),
2.12C (detenues), 2.13C (other prisoners) — each State/UT x religion — for
every PSI year we archive.

Reads:  sources/ncrb-prison/psi-<year>.pdf  (+ .meta.json sha256 sidecar)
Writes: extracted/ncrb-prison/psi-<year>-religion-by-state.csv  (one per year)

Layout per table: Sl.No State/UT Hindu Muslim Sikh Christian Others Total
- 28 states + TOTAL (STATES); 8 UTs + TOTAL (UTs); TOTAL (ALL-INDIA).
- "-" indicates non-reporting (e.g. Maharashtra in some categories/years).

Page numbers DRIFT across years (2018/2019 -> 105/109/113/117; 2021-2023 ->
103/107/111/115), so we LOCATE each table by its "Religion of <Category>"
caption and require >=1 TOTAL (STATES/UTs) data row on the page — the caption
alone also appears on the list-of-tables / executive-summary pages, which
carry no data and must be skipped. (Validated: re-extracting 2022 reproduces
the canonical Muslim share of 20.17% / 540,148 religion-reported.)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "sources" / "ncrb-prison"
OUT_DIR = REPO_ROOT / "extracted" / "ncrb-prison"
EXTRACTOR_VERSION = "2.0.0"

# PSI years whose religion-by-state tables we archive. (2015 has no religion
# table; 2016/2017/2020 are not available from primary/archive sources — see
# manifest + runbook.)
YEARS = [2018, 2019, 2021, 2022, 2023]

# (table_id, category, caption regex). Table ids are stable across all years.
CATEGORIES = [
    ("2.10C", "convicts",    re.compile(r"Religion of Convicts", re.I)),
    ("2.11C", "undertrials", re.compile(r"Religion of Undertrial", re.I)),
    ("2.12C", "detenues",    re.compile(r"Religion of Detenues", re.I)),
    ("2.13C", "other",       re.compile(r"Religion of Other", re.I)),
]
RELIGION_COLS = ["hindu", "muslim", "sikh", "christian", "others"]

NUM_OR_DASH = r"(?:\d+|-)"
STATE_ROW = re.compile(
    rf"^\s*(\d{{1,2}})\s+(.+?)\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+(\d+)\s*$"
)
TOTAL_ROW = re.compile(
    rf"^(TOTAL\s*\([^)]+\))\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+"
    rf"({NUM_OR_DASH})\s+({NUM_OR_DASH})\s+(\d+)\s*$"
)


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


def parse_int_or_none(s: str) -> int | None:
    return None if s == "-" else int(s)


def _has_data_row(text: str) -> bool:
    """True if the page carries a STATES/UTs subtotal row (i.e. it is the real
    data table, not the caption-only contents/summary page)."""
    for line in text.splitlines():
        m = TOTAL_ROW.match(line.strip())
        if m and ("STATES" in m.group(1) or "UTs" in m.group(1)):
            return True
    return False


def locate_tables(pdf) -> dict[str, int]:
    """Return {category: page_index} by scanning for caption + data rows.
    Stops once all four categories are located."""
    found: dict[str, int] = {}
    for i, page in enumerate(pdf.pages):
        if len(found) == len(CATEGORIES):
            break
        text = page.extract_text() or ""
        if not _has_data_row(text):
            continue
        for _tid, cat, pat in CATEGORIES:
            if cat not in found and pat.search(text):
                found[cat] = i
                break
    return found


def extract_year(year: int) -> int:
    source_path = SRC_DIR / f"psi-{year}.pdf"
    output_path = OUT_DIR / f"psi-{year}-religion-by-state.csv"
    if not source_path.exists():
        sys.exit(f"missing L1 archive: {source_path.relative_to(REPO_ROOT)} (run ingest/pull.py)")
    meta = verify_source_integrity(source_path)

    extraction_run = (
        f"ncrb-prison-extract-v{EXTRACTOR_VERSION}-{year}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    all_rows: list[dict] = []
    with pdfplumber.open(str(source_path)) as pdf:
        pages = locate_tables(pdf)
        missing = [cat for _t, cat, _p in CATEGORIES if cat not in pages]
        if missing:
            sys.exit(f"psi-{year}: could not locate religion table(s): {missing}")
        for table_id, category, _pat in CATEGORIES:
            page_idx = pages[category]
            page_num = page_idx + 1
            text = pdf.pages[page_idx].extract_text() or ""
            n_state = n_total = 0
            for line in text.splitlines():
                line = line.strip()
                m_state = STATE_ROW.match(line)
                m_total = TOTAL_ROW.match(line)
                if m_state:
                    g = m_state.groups()
                    vals = [parse_int_or_none(g[2 + i]) for i in range(5)]
                    for col, val in zip(RELIGION_COLS, vals):
                        all_rows.append({
                            "table_id": table_id, "category": category, "page": page_num,
                            "row_type": "state", "serial": int(g[0]),
                            "geography_name": g[1].strip(), "religion": col, "value": val,
                            "row_total": int(g[7]),
                        })
                    n_state += 1
                elif m_total:
                    vals = [parse_int_or_none(m_total.group(2 + i)) for i in range(5)]
                    for col, val in zip(RELIGION_COLS, vals):
                        all_rows.append({
                            "table_id": table_id, "category": category, "page": page_num,
                            "row_type": "subtotal_or_total", "serial": None,
                            "geography_name": m_total.group(1), "religion": col, "value": val,
                            "row_total": int(m_total.group(7)),
                        })
                    n_total += 1
            print(f"  {year} {table_id} ({category}) p{page_num}: {n_state} states + {n_total} totals")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_id", "category", "page",
            "row_type", "serial", "geography_name", "religion", "value", "row_total",
        ])
        for r in all_rows:
            w.writerow([
                "ncrb-prison", str(source_path.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                r["table_id"], r["category"], r["page"],
                r["row_type"], r["serial"] if r["serial"] is not None else "",
                r["geography_name"], r["religion"],
                "" if r["value"] is None else r["value"],
                r["row_total"],
            ])
    print(f"wrote {output_path.relative_to(REPO_ROOT)} ({len(all_rows)} rows)")
    return len(all_rows)


def main() -> None:
    p = argparse.ArgumentParser(description="Extract NCRB PSI religion-by-state tables (multi-year).")
    p.add_argument("--year", type=int, help="Extract a single year (default: all configured years)")
    args = p.parse_args()
    years = [args.year] if args.year else YEARS
    for y in years:
        extract_year(y)


if __name__ == "__main__":
    main()
