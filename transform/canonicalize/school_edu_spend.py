"""
L2 -> L3 for the `school-edu-spend` metric.

Reads:  extracted/education/education-2017-school-spend-by-religion.csv
        extracted/education/education-2025-school-spend-by-religion.csv
Writes: canonical/school-edu-spend.csv

Average household expenditure per student enrolled in school education
(pre-primary up to higher secondary, incl. diploma/certificate up to
higher-secondary equivalent) during the current academic year, Rs nominal,
by religion of household head, EXCLUDING private coaching (collected as a
separate block in both rounds' instruments and outside the CMSE published
headline). Two rounds:

- NSS 75th round Sch 25.2, July 2017 - June 2018 (year=2017), via MoSPI's
  fixed-width TXT distribution surviving in the unlinked NSS75252E/
  directory (the NADA copy is a proprietary .Nesstar binary; see
  sources/nss75-education/PROVENANCE-note.md). The estimator reproduces all
  27 anchor cells of NSS Report 585 Statements 19 and 21 within 0.01%; the
  carded school-level excl-coaching construct is that gated pipeline on the
  CMSE-matched universe.
- CMS:E, NSS 80th round, April - June 2025 (year=2025), via the NADA CSV
  distribution (sources/nada/education-2025/). Reproduces all seven
  published Report 595 per-student cells within 0.01%.

break_flag=true on the 2025 rows: Report 595's own comparability section
lists concept revisions vs the 75th round (school-only coverage, anganwadi
counted as pre-primary, age universe 3+ rather than 3-35, itemised
coaching), so the connector renders dashed.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_DIR = REPO_ROOT / "extracted" / "education"
OUTPUT_PATH = REPO_ROOT / "canonical" / "school-edu-spend.csv"
CANONICALIZER_VERSION = "1.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}

NOTE_2017 = (
    "Computed from NSS 75th round Sch 25.2 (Household Social Consumption: "
    "Education, July 2017 - June 2018) unit-level microdata, MoSPI's "
    "original fixed-width TXT distribution (the NADA copy is a proprietary "
    "binary; provenance in sources/nss75-education/): average expenditure "
    "per student enrolled at school levels (pre-primary to higher "
    "secondary, incl. diploma/certificate up to higher-secondary "
    "equivalent) on the basic course during the current academic year, "
    "{res}, weighted by the official multiplier (sub-sample-combined "
    "rule). Counts course fees, books, stationery and uniform, transport "
    "and other items; private coaching excluded to match the CMS:E 2025 "
    "headline construct. The estimator reproduces all 27 published anchor "
    "cells of NSS Report 585 Statements 19 and 21 (total basic-course "
    "expenditure by course type, and by school level for general-course "
    "students) within 0.01%; the report never splits expenditure by "
    "religion. Values are nominal rupees of 2017-18. NSO unit-data rider: "
    "religion is self-reported and the survey is stratified for states, "
    "not religions, so the split is indicative and no sub-state estimates "
    "are made."
)

NOTE_2025 = (
    "Computed from the Comprehensive Modular Survey: Education (CMS:E, NSS "
    "80th round, April - June 2025) unit-level microdata via the MoSPI "
    "NADA CSV distribution (sources/nada/education-2025/): average "
    "expenditure per student currently enrolled in school education "
    "(pre-primary incl. anganwadi up to higher secondary, incl. "
    "diploma/certificate up to higher-secondary equivalent) during the "
    "current academic year, {res}, weighted by the official multiplier. "
    "Counts course fees, textbooks and stationery, uniform, transport and "
    "other items; private coaching is collected separately and excluded, "
    "matching the published headline. The estimator reproduces all seven "
    "published Report 595 per-student cells (all-India 12,616, rural "
    "8,382, urban 23,470; government 2,863, private aided 15,364, private "
    "unaided 28,693, others 14,315) within 0.01%; the report stops at "
    "school type, level and state, never religion. break_flag marks the "
    "round: Report 595's comparability section lists concept revisions vs "
    "the 75th round (school-only coverage, anganwadi as pre-primary, age "
    "3+, itemised coaching), so read the step from 2017-18 with care. "
    "Values are nominal rupees of 2025. NSO unit-data rider: religion is "
    "self-reported and the survey is stratified for states, not "
    "religions, so the split is indicative and no sub-state estimates are "
    "made."
)

ROUNDS = [
    {
        "year": 2017,
        "l2": "education-2017-school-spend-by-religion.csv",
        "source_id": "nss75-education",
        "source_document": "sources/nss75-education/PROVENANCE-note.md",
        "note": NOTE_2017,
        "break_flag": "false",
    },
    {
        "year": 2025,
        "l2": "education-2025-school-spend-by-religion.csv",
        "source_id": "education-2025",
        "source_document": "sources/nada/education-2025/Data in CSV.zip.meta.json",
        "note": NOTE_2025,
        "break_flag": "true",
    },
]


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-school-edu-spend-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = []
    for rnd in ROUNDS:
        with (L2_DIR / rnd["l2"]).open() as f:
            for r in csv.DictReader(f):
                rows.append({
                    "metric_id": "school-edu-spend",
                    "geography_level": "national",
                    "geography_code": "IN", "year": rnd["year"],
                    "religion": r["religion"],
                    "residence": r["residence"],
                    "value": int(round(float(r["avg_school_spend_rs"]))),
                    "denominator": "per_enrolled_student",
                    "sample_size": r["n_students"], "ci_lower": "", "ci_upper": "",
                    "source_id": rnd["source_id"],
                    "source_document": rnd["source_document"],
                    "extraction_run": extraction_run,
                    "methodology_note": rnd["note"].format(
                        res=RES_WORD[r["residence"]]),
                    "break_flag": rnd["break_flag"],
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
