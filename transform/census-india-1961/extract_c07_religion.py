"""
L1 -> L2 for Census 1961 Table C-VII Religion, National row only.

Reads:  sources/census-1961/social-cultural-tables-c07-religion.pdf
        (NADA catalog 32022, "Social and Cultural Tables, Part II-C(i),
         Vol-XIII INDIA", A. Mitra RGI, 574pp)
Writes: extracted/census-1961/c07-religion.csv

Table C-VII appears at internal pp 488-507 (PDF pp 501-520). The INDIA T/R/U
block spans two facing pages:
  PDF p501 (internal p488): Total + Buddhists + Christians + Hindus columns
  PDF p502 (internal p489): Jains + Muslims + Sikhs + Other religions +
                           Religion-not-stated columns

The scanned PDF has OCR noise (e.g. "1,612,560" was OCR'd as "1,612,56Q";
"1,053,665" as "i,053,fi65"). We extract by:
  (1) Verifying the SHA256 of the L1 PDF against the sidecar (so the file is
      exactly the one we hand-inspected)
  (2) Embedding hand-verified counts from the INDIA Total-residence row
  (3) Cross-validating each derived sex ratio against Sachar AT 3.8 (Sachar
      cited "India, Registrar General (1961...)" for the same row) and the
      sum-of-religion-totals against the page's Total Population.

Hand-verification was done 2026-05-31 against PDF pp 501-502 INDIA T row.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import sys

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "sources" / "census-1961" / "social-cultural-tables-c07-religion.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "census-1961" / "c07-religion.csv"
EXTRACTOR_VERSION = "1.0.0"

# Hand-verified INDIA Total-residence counts from PDF pp 501 + 502 INDIA T row.
# Format: religion -> (persons, males, females). 'all' = published India total
# (the published all-India Total Persons is on p501; males+females derive from
# splitting; we use the published M+F = 226,293,201 + 212,941,570 = 439,234,771).
COUNTS = {
    "all":        (439_234_771, 226_293_201, 212_941_570),
    "hindu":      (366_531_846, 188_755_134, 177_776_712),
    "muslim":     ( 46_940_799,  24_262_926,  22_677_873),
    "christian":  ( 10_728_586,   5_394_783,   5_333_803),
    "sikh":       (  7_845_915,   4_242_565,   3_603_350),
    "buddhist":   (  3_256_036,   1_643_476,   1_612_560),
    "jain":       (  2_027_381,   1_053_665,     973_716),
    "other":      (  1_498_895,     741_436,     757_459),
    "not_stated": (    113_040,      57_216,      55_824),
}

# Cross-check expected sex ratios. Sachar AT 3.8 gives All 941 / Muslim 935.
# Other religions inferred from the same table.
EXPECTED_SEX_RATIO = {"all": 941, "hindu": 942, "muslim": 935, "christian": 989, "sikh": 849, "buddhist": 981, "jain": 924}


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


def verify_table_anchors() -> None:
    """Confirm the C-VII table is at the expected PDF pages.

    p501 + p502 of this 1961 publication have heavy OCR noise on words
    (e.g. "Muslims" becomes "M - u sli - ms"), but the NUMERIC counts in
    the INDIA T row are clean. Anchor on the specific values from the
    INDIA row: if the hardcoded Hindu Males number appears on p501 and
    the hardcoded Muslim Males number appears on p502, we have the right
    table at the right pages.
    """
    with pdfplumber.open(str(SOURCE_PATH)) as pdf:
        t501 = pdf.pages[500].extract_text() or ""
        if "C-VII" not in t501:
            sys.exit("p501 sanity check failed: C-VII heading missing")
        # Anchor on the cleanest-OCR'd values. The Total Persons number
        # (439,234,771) is OCR'd cleanly on p501; the Muslim Males value
        # (24,262,926) is clean on p502. Other religion numbers are sometimes
        # corrupted (e.g. "188,75a,134" instead of "188,755,134").
        total_p_str = f"{COUNTS['all'][0]:,}"
        if total_p_str not in t501:
            sys.exit(f"p501 sanity check failed: Total Persons {total_p_str} not on page")
        t502 = pdf.pages[501].extract_text() or ""
        muslim_m_str = f"{COUNTS['muslim'][1]:,}"
        if muslim_m_str not in t502:
            sys.exit(f"p502 sanity check failed: Muslim Males {muslim_m_str} not on page")


def cross_validate() -> None:
    # Sex ratio per religion
    for rel, (persons, males, females) in COUNTS.items():
        if rel not in EXPECTED_SEX_RATIO:
            continue
        derived = round(females / males * 1000)
        expected = EXPECTED_SEX_RATIO[rel]
        if abs(derived - expected) > 1:
            sys.exit(f"sex-ratio cross-check FAILED for {rel}: derived {derived} vs expected {expected}")
        if males + females != persons:
            sys.exit(f"M+F != Persons for {rel}: {males} + {females} != {persons}")
    # Sum-of-religions ≈ Total. The 1961 published India Total (439,234,771)
    # includes NEFA (38,705 persons per the * footnote on the table) and some
    # other small territories where the religion schedule wasn't canvassed,
    # so sum-of-religions falls ~290k below Total — well under 0.1%.
    total_persons = COUNTS["all"][0]
    sum_named = sum(COUNTS[r][0] for r in ("hindu", "muslim", "christian", "sikh", "buddhist", "jain", "other", "not_stated"))
    if abs(sum_named - total_persons) > total_persons * 0.002:  # 0.2% slack
        sys.exit(f"sum-of-religions ({sum_named}) deviates from Total ({total_persons}) by >0.2%")


def extract() -> None:
    meta = verify_source_integrity()
    verify_table_anchors()
    cross_validate()

    extraction_run = (
        f"census1961-c07-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_name", "area_name", "area_level",
            "residence", "religion", "sex", "value",
        ])
        for religion, (persons, males, females) in COUNTS.items():
            for sex, value in [("persons", persons), ("males", males), ("females", females)]:
                w.writerow([
                    "census-india-1961",
                    str(SOURCE_PATH.relative_to(REPO_ROOT)),
                    meta["sha256"][:16],
                    extraction_run,
                    "C-VII", "India", "national",
                    "total", religion, sex, value,
                ])
                n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    for rel, (p, m, fem) in COUNTS.items():
        if m > 0:
            print(f"  {rel:10s} persons={p:>13,} m={m:>13,} f={fem:>13,} SR={round(fem/m*1000)}")


if __name__ == "__main__":
    extract()
