"""
L2 -> L3 for the `undertrial-rate-per-100k` metric.

Same cross-source pattern as prison_rate_per_100k.py but filters NCRB L2
to undertrials only.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
NCRB_L2 = REPO_ROOT / "extracted" / "ncrb-prison" / "psi-2022-religion-by-state.csv"
CENSUS_L2 = REPO_ROOT / "extracted" / "census-2011" / "c01-population-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "undertrial-rate-per-100k.csv"
CANONICALIZER_VERSION = "1.0.0"


def load_undertrial_counts() -> dict[str, int]:
    counts: dict[str, int] = {"muslim": 0, "hindu": 0, "all": 0}
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
            rel = row["religion"]
            counts["all"] += v
            if rel == "muslim":
                counts["muslim"] += v
            elif rel == "hindu":
                counts["hindu"] += v
    return counts


def load_national_pop() -> dict[str, int]:
    pops: dict[str, int] = {}
    with CENSUS_L2.open() as f:
        for row in csv.DictReader(f):
            if row["state_code"] != "00" or row["residence"] != "total" or row["sex"] != "persons":
                continue
            if row["religion"] in ("muslim", "hindu", "all"):
                pops[row["religion"]] = int(row["value"])
    return pops


def canonicalize() -> None:
    counts = load_undertrial_counts()
    pops = load_national_pop()

    extraction_run = (
        f"canonicalize-undertrial-rate-per-100k-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
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
        for religion in ("muslim", "hindu", "all"):
            cnt = counts[religion]
            pop = pops[religion]
            rate = round(cnt / pop * 100_000, 2)
            w.writerow([
                "undertrial-rate-per-100k", "national", "IN", 2022, religion,
                rate,
                f"population_per_100k (count={cnt}, pop={pop})",
                "", "", "",
                "ncrb-prison",
                "sources/ncrb-prison/psi-2022.pdf",
                extraction_run,
                ("Cross-source: NCRB PSI 2022 undertrial counts (Table 2.11C, "
                 "STATES+UTs subtotals) divided by Census 2011 national religious "
                 "population times 100,000. Caveat: Maharashtra did not report religion "
                 "for ~33k undertrials; religion-reported numerator excludes those."),
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    for religion in ("muslim", "hindu", "all"):
        cnt = counts[religion]
        pop = pops[religion]
        rate = cnt / pop * 100_000
        print(f"  {religion}: count={cnt:,}  pop={pop:,}  rate={rate:.2f}/100k")


if __name__ == "__main__":
    canonicalize()
