"""
L2 -> L3 for the `prison-rate-per-100k` metric (incarceration rate per
100,000 of religious population).

Cross-source canonicalizer:
  Reads:  extracted/ncrb-prison/psi-2022-religion-by-state.csv  (prisoner counts)
          extracted/census-2011/c01-population-by-religion.csv  (population denominators)
  Writes: canonical/prison-rate-per-100k.csv

Rate = (total prisoners of religion R) / (population of religion R) * 100,000

Sum across all 4 prison categories (convicts + undertrials + detenues + other)
using STATES + UTs subtotals (= ALL-INDIA by construction). Population from
Census 2011 C-1 national row (most recent authoritative population by religion;
2021 Census delayed).

Emits per-community rates for the religions NCRB reports against a clean Census
population denominator: muslim, hindu, christian, sikh (+ the all-India total).
NCRB's mixed "others" prisoner bucket (Buddhist/Jain/Parsi/not-stated) is
omitted — there is no single clean population group to divide it by.

Caveat documented in methodology: Maharashtra didn't report a religion breakdown
for ~33k undertrials/detenues in PSI 2022. The religion-reported numerator
excludes those; the full national population is the denominator, so rates are
mildly understated.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
NCRB_L2 = REPO_ROOT / "extracted" / "ncrb-prison" / "psi-2022-religion-by-state.csv"
CENSUS_L2 = REPO_ROOT / "extracted" / "census-2011" / "c01-population-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "prison-rate-per-100k.csv"
CANONICALIZER_VERSION = "1.1.0"

# Communities emitted, in canonical order. NCRB's "others" is intentionally
# excluded (mixed bucket, no clean Census population denominator).
OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "all")


def load_prisoner_counts() -> dict[str, int]:
    """Returns {religion: total prisoners across all 4 categories}.

    Sums STATES + UTs subtotals (equals ALL-INDIA). 'all' sums every religion
    NCRB reports (hindu / muslim / sikh / christian / others), so each community
    is accumulated and per-community rates become possible.
    """
    counts: dict[str, int] = collections.defaultdict(int)
    with NCRB_L2.open() as f:
        for row in csv.DictReader(f):
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
    """Returns {religion: national population} from Census 2011 C-1."""
    pops: dict[str, int] = {}
    with CENSUS_L2.open() as f:
        for row in csv.DictReader(f):
            if row["state_code"] != "00" or row["residence"] != "total" or row["sex"] != "persons":
                continue
            if row["religion"] in OUTPUT_RELIGIONS:
                pops[row["religion"]] = int(row["value"])
    return pops


def canonicalize() -> None:
    counts = load_prisoner_counts()
    pops = load_national_pop()

    extraction_run = (
        f"canonicalize-prison-rate-per-100k-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    note = (
        "Cross-source: NCRB PSI 2022 prisoner counts (STATES+UTs subtotals across "
        "all 4 categories: convicts + undertrials + detenues + other prisoners) "
        "divided by Census 2011 national religious population times 100,000. NCRB "
        "'others' bucket (Buddhist/Jain/Parsi/not-stated) omitted — no clean "
        "population denominator. Caveat: Maharashtra did not report religion for "
        "~33k undertrials/detenues; the religion-reported numerator excludes those, "
        "so rates are mildly understated."
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
                "prison-rate-per-100k", "national", "IN", 2022, religion,
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
