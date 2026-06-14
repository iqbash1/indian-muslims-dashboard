"""
L2 -> L3 for the `communal-incidents-govt` metric.
MULTI-YEAR (v2): reads the unified cii-communal-incidents.csv L2 that combines
CII 2022 + CII 2023 reports.

Reads:  extracted/ncrb-crime/cii-communal-incidents.csv
Writes: canonical/communal-incidents-govt.csv

Emits two views:
  - National time series 2020-2023 (deduped from Table 1.2 across both reports)
  - State-level 2022 (from CII 2022 Table 1A.4) + 2023 (from CII 2023 Table 1A.4)

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
L2_PATH = REPO_ROOT / "extracted" / "ncrb-crime" / "cii-communal-incidents.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "communal-incidents-govt.csv"
CANONICALIZER_VERSION = "2.0.0"

NATIONAL_NOTE = (
    "NCRB Crime in India (Table 1.2 national time series), row 23.1 "
    "'Communal/Religious' rioting. Incident counts only: no religion of "
    "victim/perpetrator in the published table. Caveat: several states "
    "stopped recording 'communal' as a separate crime category since "
    "~2017, which deflates the national total over time; civil-society "
    "compilations (Documentation of the Oppressed, India Hate Lab) "
    "typically report higher counts."
)


def canonicalize() -> None:
    national_years: list[tuple[int, int, str]] = []   # (year, value, source_doc)
    state_rows: list[tuple[int, str, str, int, str]] = []  # (year, code, name, value, source_doc)
    unmapped: list[str] = []

    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            rt = row["row_type"]
            year = int(row["year"])
            n = int(row["communal_incidents"])
            src_doc = row["source_document"]
            if rt == "national_year":
                national_years.append((year, n, src_doc))
            elif rt.startswith("state_"):
                name = row["geography"]
                code = normalize_state_name(name) or normalize_state_name(name.title())
                if code is None:
                    unmapped.append(name)
                    continue
                state_rows.append((year, code, name, n, src_doc))
    national_years.sort()
    if unmapped:
        print(f"  WARN: unmapped states (skipped): {sorted(set(unmapped))}")

    extraction_run = (
        f"canonicalize-communal-incidents-govt-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_out = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        for year, n, src_doc in national_years:
            w.writerow([
                "communal-incidents-govt", "national", "IN", year, "all",
                n, "incidents_per_year", "", "", "",
                "ncrb-crime", src_doc, extraction_run, NATIONAL_NOTE, "false",
            ])
            n_out += 1
        for year, code, name, n, src_doc in sorted(state_rows, key=lambda x: (x[0], -x[3])):
            w.writerow([
                "communal-incidents-govt", "state", code, year, "all",
                n, "incidents_per_year", "", "", "",
                "ncrb-crime", src_doc, extraction_run,
                (f"NCRB CII {year} Table 1A.4 state-level. {name} reported {n} "
                 f"communal/religious rioting incidents. Caveat: state-to-state "
                 f"comparisons are biased by inconsistent recording practices."),
                "false",
            ])
            n_out += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_out} rows)")
    for year, n, _ in national_years:
        print(f"  national {year}: {n} incidents")
    for yr in sorted({r[0] for r in state_rows}):
        top = sorted([r for r in state_rows if r[0] == yr], key=lambda x: -x[3])[:5]
        print(f"  top 5 states {yr}: " + ", ".join(f"{r[2]}={r[3]}" for r in top))


if __name__ == "__main__":
    canonicalize()
