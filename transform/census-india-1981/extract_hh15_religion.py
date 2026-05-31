"""
L1 -> L2 for Census 1981 Table HH-15 (Household Population by Religion of
Head of Household), National row only.

Reads:  sources/census-1981/paper-3-of-1984-hh15-religion.pdf
        (NADA catalog 30879, V.S. Verma RGI, 123pp)
Writes: extracted/census-1981/hh15-religion.csv

The HH-15 table spans 4 facing-page spreads (PDF pp 23-26). Each page carries
the INDIA T/R/U rows + state rows, with a different column-group per page:
  p23: Total Population + Hindus
  p24: Muslims + Christians
  p25: Sikhs + Buddhists
  p26: Jains + Other religions + Religion not stated

For the dashboard we extract only the INDIA Total-residence row's per-
religion Persons / Males / Females counts. Cross-validates each derived sex
ratio against Sachar Committee Report 2006 AT 3.8 (Sachar's 1981 row, which
cites this same RGI 1984 publication as source).

Note: HH-15 is "Household Population by Religion of HEAD". For Indian
census purposes households are religiously homogeneous so this is the
canonical population-by-religion tally — the publication explicitly notes
"This table corresponds to table C-VII Religion of 1961 and 1971."

1981 excludes Assam (Census not held there that round).
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
SOURCE_PATH = REPO_ROOT / "sources" / "census-1981" / "paper-3-of-1984-hh15-religion.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "census-1981" / "hh15-religion.csv"
EXTRACTOR_VERSION = "1.0.0"

# Page indices (0-indexed) for each column-group block. Verified by manual probe.
PAGE_BLOCKS = [
    {"page": 22, "religions": [("all", 0), ("hindu", 1)]},          # p23 in PDF
    {"page": 23, "religions": [("muslim", 0), ("christian", 1)]},   # p24
    {"page": 24, "religions": [("sikh", 0), ("buddhist", 1)]},      # p25
    {"page": 25, "religions": [("jain", 0), ("other", 1), ("not_stated", 2)]},  # p26
]
RESIDENCE_LABELS = ["total", "rural", "urban"]
SEX_LABELS = ["persons", "males", "females"]

# Cross-check expected sex ratios (Sachar AT 3.8 + manual derivation; ±1 tolerance).
EXPECTED_SEX_RATIO = {"hindu": 933, "muslim": 937, "christian": 992, "sikh": 880, "buddhist": 953, "jain": 941}


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source_integrity() -> dict:
    meta_path = SOURCE_PATH.with_suffix(SOURCE_PATH.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text())
    actual = sha256_of(SOURCE_PATH)
    if actual != meta["sha256"]:
        sys.exit(f"sha256 mismatch: {actual[:16]} != sidecar {meta['sha256'][:16]}")
    return meta


def _parse_india_block(page_text: str, n_religions: int) -> dict[str, list[int]]:
    """
    Parse the India T/R/U block. Page layout: 'INDIA*' or 'INDIA' marks the
    Total row; the Rural + Urban rows follow without label. Each row has
    4 * n_religions numbers (No.HH, Persons, Males, Females per religion).

    Returns {residence: [num1, num2, ...]}.
    """
    lines = page_text.splitlines()
    # Find the INDIA row
    india_idx = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s*INDIA\*?\s+T\s", ln):
            india_idx = i
            break
    if india_idx is None:
        # Continuation pages have no INDIA label. India T is the first whitespace-
        # split row of length 4*n_religions where the first token is large (skips
        # the column-number ruler row "11 12 13 14 ..." near the page top).
        for i, ln in enumerate(lines):
            tokens = ln.strip().split()
            if len(tokens) == 4 * n_religions and all(re.fullmatch(r"[\d.,]+", t) for t in tokens):
                first = int(tokens[0].replace(",", ""))
                if first > 100_000:  # India HH count > 100k; ruler row's first num is e.g. 11
                    india_idx = i
                    break
        if india_idx is None:
            sys.exit(f"could not locate India block in page (n_religions={n_religions})")

    out = {}
    for residence_offset, residence in enumerate(RESIDENCE_LABELS):
        ln = lines[india_idx + residence_offset]
        # Strip leading "INDIA T" / "R" / "U" labels and parse all numeric tokens
        cleaned = re.sub(r"^\s*INDIA\*?\s*[TRU]?\s*", "", ln)
        cleaned = re.sub(r"^\s*[TRU]\s*", "", cleaned)
        tokens = re.findall(r"[\d.,]+", cleaned)
        nums = []
        for t in tokens:
            try:
                nums.append(int(t.replace(",", "")))
            except ValueError:
                pass
        if len(nums) < 4 * n_religions:
            sys.exit(f"India {residence} row short: got {len(nums)} tokens, expected {4 * n_religions} in line: {ln!r}")
        out[residence] = nums[: 4 * n_religions]
    return out


def extract() -> None:
    meta = verify_source_integrity()
    extraction_run = (
        f"census1981-hh15-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows: list[list] = []
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        for block in PAGE_BLOCKS:
            page_text = pdf.pages[block["page"]].extract_text() or ""
            parsed = _parse_india_block(page_text, len(block["religions"]))
            for residence, nums in parsed.items():
                for religion, col_group_idx in block["religions"]:
                    # Each column-group occupies 4 consecutive numbers: HH, Persons, Males, Females
                    base = col_group_idx * 4
                    persons = nums[base + 1]
                    males = nums[base + 2]
                    females = nums[base + 3]
                    for sex, value in [("persons", persons), ("males", males), ("females", females)]:
                        rows.append([
                            "census-india-1981",
                            str(SOURCE_PATH.relative_to(REPO_ROOT)),
                            meta["sha256"][:16],
                            extraction_run,
                            "HH-15", "India (excl Assam)", "national",
                            residence, religion, sex, value,
                        ])

    # Cross-validation: derived sex ratios must match expected within ±1
    by_key = {(r[8], r[7], r[9]): r[10] for r in rows}  # (religion, residence, sex) -> value
    for rel, expected in EXPECTED_SEX_RATIO.items():
        m = by_key.get((rel, "total", "males"))
        f = by_key.get((rel, "total", "females"))
        if not m or not f:
            sys.exit(f"missing males/females for religion {rel}")
        derived = round(f / m * 1000)
        if abs(derived - expected) > 1:
            sys.exit(f"sex-ratio cross-check FAILED for {rel}: derived {derived} vs expected {expected}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_name", "area_name", "area_level",
            "residence", "religion", "sex", "value",
        ])
        w.writerows(rows)

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    # Summary print
    for rel in ("hindu", "muslim", "christian", "sikh", "buddhist", "jain"):
        m = by_key[(rel, "total", "males")]
        f_ = by_key[(rel, "total", "females")]
        p = by_key[(rel, "total", "persons")]
        sr = round(f_ / m * 1000)
        print(f"  {rel:10s} persons={p:>13,} m={m:>13,} f={f_:>13,} SR={sr}")


if __name__ == "__main__":
    extract()
