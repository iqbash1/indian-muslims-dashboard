"""
L2 -> L3 for the `muslim-higher-ed-enrolment` metric.

Reads:  extracted/aishe/aishe-2021-22-table15-state-minority-enrolment.csv
Writes: canonical/muslim-higher-ed-enrolment.csv

Maps AISHE state names to canonical state codes via transform/geography_codes.py
and emits one row per geography (religion=muslim, value=muslim_total).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from geography_codes import normalize_state_name

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "aishe" / "aishe-2021-22-table15-state-minority-enrolment.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "muslim-higher-ed-enrolment.csv"
CANONICALIZER_VERSION = "1.0.0"


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-muslim-higher-ed-enrolment-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    n_unmapped = 0
    with L2_PATH.open() as fin, OUTPUT_PATH.open("w", newline="") as fout:
        w = csv.writer(fout)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])

        for row in csv.DictReader(fin):
            state_name = row["state_name"]
            geo_code = normalize_state_name(state_name)
            if geo_code is None:
                print(f"  WARN unmapped state: {state_name!r}")
                n_unmapped += 1
                continue
            level = "national" if geo_code == "IN" else "state"
            value = int(row["muslim_total"])
            w.writerow([
                "muslim-higher-ed-enrolment", level, geo_code, 2021, "muslim",
                value, "students", "", "", "",
                "aishe",
                row["source_document"],
                extraction_run,
                "AISHE 2021-22 Table 15 Muslim Minority enrolment. Year=2021 represents the academic year 2021-22.",
                "false",
            ])
            n_rows += 1

    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({n_rows} rows; {n_unmapped} unmapped)"
    )


if __name__ == "__main__":
    canonicalize()
