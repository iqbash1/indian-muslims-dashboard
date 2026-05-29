"""
L2 -> L3 for the `undertrial-rate-per-100k` metric.

Same cross-source pattern as prison_rate_per_100k.py but filters NCRB L2
to undertrials only.

Emits per-community rates for muslim, hindu, christian, sikh (+ all-India).
NCRB's mixed "others" undertrial bucket is omitted (no clean Census population
denominator).
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
NCRB_L2 = REPO_ROOT / "extracted" / "ncrb-prison" / "psi-2022-religion-by-state.csv"
CENSUS_L2 = REPO_ROOT / "extracted" / "census-2011" / "c01-population-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "undertrial-rate-per-100k.csv"
CANONICALIZER_VERSION = "1.1.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "all")


def load_undertrial_counts() -> dict[str, int]:
    """Returns {religion: undertrial prisoners}. Sums STATES + UTs subtotals.
    'all' sums every religion NCRB reports for the undertrial category.
    """
    counts: dict[str, int] = collections.defaultdict(int)
    with NCRB_L2.open() as f:
        for row in csv.DictReader(f):
            if row["category"] != "undertrials":
                continue
            if row["row_type"] != "subtotal_or_total":
                continue
            label = row["geography_name"]
            if "STATES" not in label and "UTs" not in label:
                continue
            if not row["value"]:
                continue
            v = int(row["value"])
            counts["all"] += v
            counts[row["religion"]] += v
    return counts


def load_national_pop() -> dict[str, int]:
    pops: dict[str, int] = {}
    with CENSUS_L2.open() as f:
        for row in csv.DictReader(f):
            if row["state_code"] != "00" or row["residence"] != "total" or row["sex"] != "persons":
                continue
            if row["religion"] in OUTPUT_RELIGIONS:
                pops[row["religion"]] = int(row["value"])
    return pops


def canonicalize() -> None:
    counts = load_undertrial_counts()
    pops = load_national_pop()

    extraction_run = (
        f"canonicalize-undertrial-rate-per-100k-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    note = (
        "Cross-source: NCRB PSI 2022 undertrial counts (Table 2.11C, STATES+UTs "
        "subtotals) divided by Census 2011 national religious population times "
        "100,000. NCRB 'others' bucket (Buddhist/Jain/Parsi/not-stated) omitted — "
        "no clean population denominator. Caveat: Maharashtra did not report "
        "religion for ~33k undertrials; the religion-reported numerator excludes "
        "those, so rates are mildly understated."
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        for religion in OUTPUT_RELIGIONS:
            cnt = counts.get(religion)
            pop = pops.get(religion)
            if not cnt or not pop:
                print(f"  skip {religion}: count={cnt} pop={pop}")
                continue
            rate = round(cnt / pop * 100_000, 2)
            w.writerow([
                "undertrial-rate-per-100k", "national", "IN", 2022, religion,
                rate,
                f"population_per_100k (count={cnt}, pop={pop})",
                "", "", "",
                "ncrb-prison",
                "sources/ncrb-prison/psi-2022.pdf",
                extraction_run,
                note,
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    for religion in OUTPUT_RELIGIONS:
        cnt = counts.get(religion)
        pop = pops.get(religion)
        if not cnt or not pop:
            continue
        rate = cnt / pop * 100_000
        print(f"  {religion}: count={cnt:,}  pop={pop:,}  rate={rate:.2f}/100k")


if __name__ == "__main__":
    canonicalize()
