"""
L2 -> L3 for the `communal-incidents-govt` metric.

Reads:  extracted/ncrb-crime/cii-2022-communal-incidents.csv
Writes: canonical/communal-incidents-govt.csv

National time series of government-recorded communal/religious riot
incidents from NCRB Crime in India 2022, Table 1.2 (national, 2020-2022).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "ncrb-crime" / "cii-2022-communal-incidents.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "communal-incidents-govt.csv"
CANONICALIZER_VERSION = "1.0.0"


def canonicalize() -> None:
    national_years: list[tuple[int, int]] = []
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["row_type"] == "national_year":
                national_years.append((int(row["year"]), int(row["communal_incidents"])))
    national_years.sort()

    extraction_run = (
        f"canonicalize-communal-incidents-govt-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        for year, n in national_years:
            w.writerow([
                "communal-incidents-govt", "national", "IN", year, "all",
                n, "incidents_per_year", "", "", "",
                "ncrb-crime",
                "sources/ncrb-crime/cii-2022-book1.pdf",
                extraction_run,
                ("NCRB Crime in India 2022, Table 1.2 (national time series), "
                 "row 23.1 'Communal/Religious' rioting. Incident counts only — "
                 "no religion of victim/perpetrator in the published table. "
                 "Caveat: several states stopped recording 'communal' as a "
                 "separate crime category since ~2017, which deflates the "
                 "national total over time; civil-society compilations "
                 "(Documentation of the Oppressed, India Hate Lab) typically "
                 "report higher counts."),
                "false",
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(national_years)} rows)")
    for year, n in national_years:
        print(f"  {year}: {n} incidents")


if __name__ == "__main__":
    canonicalize()
