"""
L1 -> L2 for Census 1971 Religion (national Summary table).

Reads:  sources/census-1971/religion-paper-2-of-1972.pdf  (p17 in the NADA PDF
        = p.xiii of the printed paper, "A Summary" table)
Writes: extracted/census-1971/religion-summary.csv

The 1971 RGI publication "Paper 2 of 1972: Religion" (Series-1, India, by
A. Chandra Sekhar) printed the all-India religion-by-sex breakdown in its
Introductory Note as a Summary table of "main religious communities that
accounted for at least a million population in the country as a whole."

This extractor:
  (1) verifies the PDF's SHA256 against its sidecar,
  (2) opens p17 with pdfplumber, locates the Summary table by anchor strings,
  (3) parses each religion row's Persons / Males / Females from the table,
  (4) cross-validates the printed Sex Ratio column against (females/males*1000).

The Summary covers six named religions (Hindu / Muslim / Christian / Sikh /
Buddhist / Jain). "Other religions and persuasions" + small minorities are
NOT in this Summary — they'd require parsing the per-state tables.
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
SOURCE_PATH = REPO_ROOT / "sources" / "census-1971" / "religion-paper-2-of-1972.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "census-1971" / "religion-summary.csv"
EXTRACTOR_VERSION = "1.0.0"
SUMMARY_PAGE_INDEX = 16  # zero-indexed; printed as p.xiii / NADA PDF p17

# Each row in the Summary table is "<Religion> <Persons> <Males> <Females> <SexRatio>"
RELIGION_LABELS = {
    "Hindus": "hindu",
    "Muslims": "muslim",
    "Christians": "christian",
    "Sikhs": "sikh",
    "Buddhists": "buddhist",
    "Jains": "jain",
}


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


# Each row: religion-label followed by 4 numbers (persons, males, females, sex ratio).
# The PDF has OCR-style punctuation noise (~, *, etc.) sprinkled around labels —
# tolerate trailing non-letter chars after the label.
_ROW_RE = re.compile(
    r"^(Hindus|Muslims|Christians|Sikhs|Buddhists|Jains)\b[^\d]*"
    r"([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(\d+)\s*$"
)


def parse_summary_table(text: str) -> list[tuple[str, int, int, int, int]]:
    """Return list of (religion_label, persons, males, females, printed_sex_ratio)."""
    out: list[tuple[str, int, int, int, int]] = []
    for line in text.splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        religion, persons_s, males_s, females_s, ratio_s = m.groups()
        out.append((
            religion,
            int(persons_s.replace(",", "")),
            int(males_s.replace(",", "")),
            int(females_s.replace(",", "")),
            int(ratio_s),
        ))
    return out


def extract() -> None:
    meta = verify_source_integrity()
    extraction_run = (
        f"census1971-religion-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        text = pdf.pages[SUMMARY_PAGE_INDEX].extract_text() or ""

    if "A Summary" not in text and "Sex Ratio" not in text:
        sys.exit(
            f"sanity check failed: p{SUMMARY_PAGE_INDEX+1} of {SOURCE_PATH.name} "
            f"does not look like the religion Summary page"
        )

    rows = parse_summary_table(text)
    if len(rows) != len(RELIGION_LABELS):
        sys.exit(
            f"expected {len(RELIGION_LABELS)} religion rows in the Summary, "
            f"parsed {len(rows)}: {[r[0] for r in rows]}"
        )

    # Cross-check derived sex ratio against printed value (tolerate ±1 for rounding).
    for religion, persons, males, females, printed_sr in rows:
        derived_sr = round(females / males * 1000)
        if abs(derived_sr - printed_sr) > 1:
            sys.exit(
                f"sex ratio cross-check failed for {religion}: "
                f"derived {derived_sr} vs printed {printed_sr}"
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_name", "area_name", "area_level", "religion", "sex", "value",
        ])
        # Emit (national, religion, sex) triples — persons/males/females.
        for religion_label, persons, males, females, _ in rows:
            religion = RELIGION_LABELS[religion_label]
            for sex, value in [("persons", persons), ("males", males), ("females", females)]:
                w.writerow([
                    "census-india-1971",
                    str(SOURCE_PATH.relative_to(REPO_ROOT)),
                    meta["sha256"][:16],
                    extraction_run,
                    "Paper-2-of-1972-Summary", "India", "national",
                    religion, sex, value,
                ])
                n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    for religion_label, persons, males, females, printed_sr in rows:
        derived_sr = round(females / males * 1000)
        print(f"  {RELIGION_LABELS[religion_label]:10s} persons={persons:>13,} m={males:>13,} f={females:>13,} SR={derived_sr} (printed {printed_sr})")


if __name__ == "__main__":
    extract()
