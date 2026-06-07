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
CANONICALIZER_VERSION = "2.0.0"

# AISHE table-15 columns -> canonical sex dimension. Gender at national level
# only (states stay both-sexes / sex=all; the by-sex card view is national).
SEX_COLS = {"all": "muslim_total", "male": "muslim_male", "female": "muslim_female"}
SEX_WORD = {"all": "both sexes", "male": "males", "female": "females"}
OUTPUT_SEXES = ("all", "male", "female")


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
            "sex", "value", "denominator", "sample_size", "ci_lower", "ci_upper",
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
            for sx in OUTPUT_SEXES:
                if level != "national" and sx != "all":
                    continue
                raw = row.get(SEX_COLS[sx])
                if raw in (None, ""):
                    continue
                note = (f"AISHE 2021-22 Table 15 Muslim Minority"
                        f"{'' if sx == 'all' else ' ' + SEX_WORD[sx]} enrolment. "
                        f"Year=2021 represents the academic year 2021-22.")
                w.writerow([
                    "muslim-higher-ed-enrolment", level, geo_code, 2021, "muslim", sx,
                    int(raw), "students", "", "", "",
                    "aishe",
                    row["source_document"],
                    extraction_run,
                    note,
                    "false",
                ])
                n_rows += 1

    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({n_rows} rows; {n_unmapped} unmapped)"
    )


if __name__ == "__main__":
    canonicalize()
