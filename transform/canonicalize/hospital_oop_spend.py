"""
L2 -> L3 for the `hospital-oop-spend` metric.

Reads:  extracted/health/health-2017-oopme-by-religion.csv
        extracted/health/health-2025-oopme-by-religion.csv
Writes: canonical/hospital-oop-spend.csv

Average out-of-pocket medical expenditure (OOPME) per hospitalisation case
(excluding childbirth) during the last 365 days, Rs nominal, by religion of
household head - the headline construct of the NSS health-consumption
surveys (the 2025 release states estimating households' out-of-pocket
medical expenses as the survey's primary design objective). Two rounds:

- NSS 75th round Sch 25.0, July 2017 - June 2018 (year=2017), via MoSPI's
  own fixed-width TXT distribution surviving in the unlinked NSS75250H/
  directory (the NADA copy is a proprietary .Nesstar binary; see
  sources/nss75-health/PROVENANCE-note.md). Gross medical expenditure
  reproduces all nine cells of NSS Report 586 Statement 3.15 within 0.01%
  and the reimbursement shares of Statement 3.19 exactly; OOPME = the two
  gated components combined (med - reimb; the report publishes no single
  net figure).
- NSS 80th round Sch 25.0, January - December 2025 (year=2025), via the
  NADA CSV distribution (sources/nada/health-2025/). Reproduces all six
  press-note OOPME cells (April 2026) within 0.01%.

OOPME counts doctor's/surgeon's fees, medicines, diagnostics, bed charges,
package components and other medical expenses, net of any insurance or
employer reimbursement; transport and food are excluded. Values are NOMINAL
rupees of each round. Whole rupees (the published convention).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_DIR = REPO_ROOT / "extracted" / "health"
OUTPUT_PATH = REPO_ROOT / "canonical" / "hospital-oop-spend.csv"
CANONICALIZER_VERSION = "1.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}

NOTE_2017 = (
    "Computed from NSS 75th round Sch 25.0 (Household Social Consumption: "
    "Health, July 2017 - June 2018) unit-level microdata, MoSPI's original "
    "fixed-width TXT distribution (the NADA copy is a proprietary binary; "
    "provenance in sources/nss75-health/): average out-of-pocket medical "
    "expenditure per hospitalisation case excluding childbirth during the "
    "last 365 days, {res}, weighted by the official multiplier "
    "(sub-sample-combined rule). OOPME = medical expenditure (fees, "
    "medicines, diagnostics, bed charges, package and other medical items; "
    "transport and food excluded) minus the amount reimbursed by insurance "
    "or employer. The estimator reproduces all nine published cells of NSS "
    "Report 586 Statement 3.15 (gross medical expenditure by hospital type "
    "and sector) within 0.01% and the Statement 3.19 reimbursement shares "
    "(rural 4.4%, urban 16.8%) exactly; the report publishes no by-religion "
    "expenditure table. Values are nominal rupees of 2017-18. NSO unit-data "
    "rider: religion is self-reported and the survey is stratified for "
    "states, not religions, so the split is indicative and no sub-state "
    "estimates are made."
)

NOTE_2025 = (
    "Computed from NSS 80th round Sch 25.0 (Household Social Consumption: "
    "Health, January - December 2025) unit-level microdata via the MoSPI "
    "NADA CSV distribution (sources/nada/health-2025/): average "
    "out-of-pocket medical expenditure per hospitalisation case excluding "
    "childbirth during the last 365 days, {res}, weighted by the official "
    "multiplier. OOPME = medical expenditure (fees, medicines, diagnostics, "
    "bed charges, package and other medical items; transport and food "
    "excluded) minus the amount reimbursed by insurance or employer - the "
    "release's own headline construct; estimating out-of-pocket medical "
    "expenses is the survey's stated primary design objective. The "
    "estimator reproduces all six published press-note OOPME cells (April "
    "2026: all-India 34,064, rural 31,484, urban 38,688; public 6,631, "
    "charitable 39,530, private 50,508) within 0.01%; the publication "
    "stops at quintile and state, never religion. Values are nominal "
    "rupees of 2025. NSO unit-data rider: religion is self-reported and "
    "the survey is stratified for states, not religions, so the split is "
    "indicative and no sub-state estimates are made."
)

ROUNDS = [
    {
        "year": 2017,
        "l2": "health-2017-oopme-by-religion.csv",
        "source_id": "nss75-health",
        "source_document": "sources/nss75-health/PROVENANCE-note.md",
        "note": NOTE_2017,
    },
    {
        "year": 2025,
        "l2": "health-2025-oopme-by-religion.csv",
        "source_id": "health-2025",
        "source_document": "sources/nada/health-2025/CSV_data_household_social_consumption_heaith_Jan_Dec25.zip.meta.json",
        "note": NOTE_2025,
    },
]


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-hospital-oop-spend-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = []
    for rnd in ROUNDS:
        with (L2_DIR / rnd["l2"]).open() as f:
            for r in csv.DictReader(f):
                rows.append({
                    "metric_id": "hospital-oop-spend",
                    "geography_level": "national",
                    "geography_code": "IN", "year": rnd["year"],
                    "religion": r["religion"],
                    "residence": r["residence"],
                    "value": int(round(float(r["avg_oopme_rs"]))),
                    "denominator": "per_hospitalisation_case",
                    "sample_size": r["n_cases"], "ci_lower": "", "ci_upper": "",
                    "source_id": rnd["source_id"],
                    "source_document": rnd["source_document"],
                    "extraction_run": extraction_run,
                    "methodology_note": rnd["note"].format(
                        res=RES_WORD[r["residence"]]),
                    "break_flag": "false",
                })
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    for r in rows:
        if r["residence"] == "all":
            print(f"  {r['year']} {r['religion']:9s}: Rs {r['value']:,}")


if __name__ == "__main__":
    canonicalize()
