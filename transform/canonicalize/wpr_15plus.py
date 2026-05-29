"""
L2 -> L3 for the `wpr-15plus` metric (Worker Population Ratio, 15+).

Reads:  extracted/plfs/plfs-2023-24-table48-employment-by-religion.csv
Writes: canonical/wpr-15plus.csv

Same structure as lfpr-15plus canonicalizer but filters to indicator=WPR.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "plfs" / "plfs-2023-24-table48-employment-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "wpr-15plus.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")


def canonicalize() -> None:
    by_religion: dict[str, float] = {}
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if (row["indicator"] == "WPR" and row["age_cohort"] == "15plus"
                    and row["residence"] == "total" and row["sex"] == "person"):
                by_religion[row["religion"]] = float(row["value"])

    extraction_run = (
        f"canonicalize-wpr-15plus-v{CANONICALIZER_VERSION}-"
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
        for religion in OUTPUT_RELIGIONS:
            val = by_religion.get(religion)
            if val is None:
                print(f"  skip {religion}: not in L2")
                continue
            w.writerow([
                "wpr-15plus", "national", "IN", 2023, religion,
                val, "population_age_15plus", "", "", "",
                "plfs",
                "sources/plfs/annual/plfs-annual-report-2023-24.pdf",
                extraction_run,
                ("PLFS 2023-24 Table 48 (page 396-400). Usual status (ps+ss), "
                 "total residence, person-level."),
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    canonicalize()
