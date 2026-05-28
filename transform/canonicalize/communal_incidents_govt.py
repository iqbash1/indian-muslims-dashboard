"""
L2 -> L3 for the `communal-incidents-govt` metric.

Reads:  extracted/ncrb-crime/cii-2022-communal-incidents.csv
Writes: canonical/communal-incidents-govt.csv

Emits both views:
  - National time series (2020-2022) from NCRB Crime in India 2022 Table 1.2
  - State-level breakdown (2022 only) from Table 1A.4 — same source PDF

The state-level view shows which states record the most communal incidents
under the NCRB classification (caveat: several states do not record
'communal' as a separate category, biasing the comparison).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from geography_codes import normalize_state_name

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "ncrb-crime" / "cii-2022-communal-incidents.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "communal-incidents-govt.csv"
CANONICALIZER_VERSION = "1.1.0"


def canonicalize() -> None:
    national_years: list[tuple[int, int]] = []
    states_2022: list[tuple[str, str, int]] = []  # (geography_code, original_name, incidents)
    unmapped_states: list[str] = []
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["row_type"] == "national_year":
                national_years.append((int(row["year"]), int(row["communal_incidents"])))
            elif row["row_type"] == "state_2022":
                name = row["geography"]
                # Normalize name (NCRB uses uppercase, e.g., "ANDHRA PRADESH")
                code = normalize_state_name(name)
                if code is None:
                    # Try title-case fallback for multi-word names
                    code = normalize_state_name(name.title())
                if code is None:
                    unmapped_states.append(name)
                    continue
                states_2022.append((code, name, int(row["communal_incidents"])))
    national_years.sort()
    if unmapped_states:
        print(f"  WARN: unmapped state names (skipped): {unmapped_states}")

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
        for code, name, n in sorted(states_2022, key=lambda x: -x[2]):
            w.writerow([
                "communal-incidents-govt", "state", code, 2022, "all",
                n, "incidents_per_year", "", "", "",
                "ncrb-crime",
                "sources/ncrb-crime/cii-2022-book1.pdf",
                extraction_run,
                (f"NCRB CII 2022 Table 1A.4 state-level. {name} reported {n} "
                 f"communal/religious rioting incidents. Caveat: state-to-state "
                 f"comparisons are biased by inconsistent recording practices."),
                "false",
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(national_years) + len(states_2022)} rows)")
    for year, n in national_years:
        print(f"  national {year}: {n} incidents")
    print(f"  top 5 states (2022):")
    for code, name, n in sorted(states_2022, key=lambda x: -x[2])[:5]:
        print(f"    {name} [{code}]: {n}")


if __name__ == "__main__":
    canonicalize()
