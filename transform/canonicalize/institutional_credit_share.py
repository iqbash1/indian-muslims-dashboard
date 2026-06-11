"""
L2 -> L3 for the `institutional-credit-share` metric.

Reads:  extracted/aidis/aidis-2013-wealth-by-religion.csv
        extracted/aidis/aidis-2018-wealth-by-religion.csv
Writes: canonical/institutional-credit-share.csv

Of the cash debt indebted households owe, the share borrowed from
INSTITUTIONAL lenders (banks, co-operatives, government and related agencies)
rather than moneylenders, shopkeepers, relatives and other informal sources -
the credit-access measure the Sachar Committee flagged. Two AIDIS rounds:
NSS 70th (as on 30.06.2012, year=2012, NADA CSV) and NSS 77th (as on
30.06.2018, year=2018, MoSPI's own TXT mirror; the NADA copy is a proprietary
binary). Both rounds reproduce the published all-India shares (2012: rural
56.0 / urban 84.5 exactly, KI(70/18.2) Table 8; 2018: rural 66 / urban 87 at
printed precision, press note 24.08.2021). Both questionnaires hide the same
trap: credit-agency code 09 "others" is non-institutional despite sitting
inside the institutional numeric run (documented in nada/aidis-layout-map.md;
for 2019 the serial-number ranges independently confirm the split).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_DIR = REPO_ROOT / "extracted" / "aidis"
OUTPUT_PATH = REPO_ROOT / "canonical" / "institutional-credit-share.csv"
CANONICALIZER_VERSION = "2.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}

NOTE_2012 = (
    "Computed from AIDIS 2013 (NSS 70th round, Sch 18.2) Visit-1 unit-level "
    "microdata pulled via the MoSPI NADA API: institutional share of outstanding "
    "cash debt (credit-agency codes 01-08, 10, 11; code 09 'others' is "
    "non-institutional), {res}, as on 30.06.2012, weighted. Reproduces the "
    "published all-India shares exactly (rural 56.0 / urban 84.5, KI(70/18.2) "
    "Table 8). Computed among indebted households only (incidence of "
    "indebtedness: Muslim 23.8% vs Hindu 29.0% - Muslims borrow least), so "
    "religion x residence cells ride on smaller samples (about 1,700 indebted "
    "rural Muslim households); sample_size shows all surveyed households in the "
    "cell. NSO unit-data rider: religion is self-reported; the split is "
    "indicative; no sub-state estimates. Year=2012 is the as-on date; fielded "
    "January-December 2013."
)

NOTE_2018 = (
    "Computed from AIDIS 2019 (NSS 77th round, Sch 18.2) Visit-1 unit-level "
    "microdata, MoSPI's original fixed-width TXT distribution (the NADA copy "
    "is a proprietary binary; provenance in sources/nss77-aidis/): "
    "institutional share of outstanding cash debt (credit-agency codes 01-08 "
    "and 10-13 per the instructions; code 09 'other' is non-institutional, "
    "and the questionnaire's serial-number ranges - institutional loans at "
    "serials 1-50 - confirm the split to the decimal), {res}, as on "
    "30.06.2018, weighted. Reproduces the published all-India shares at "
    "printed precision (rural 66 / urban 87, MoSPI press note 24.08.2021). "
    "Computed among indebted households only (incidence of indebtedness: "
    "Muslim 26.8% vs Hindu 31.4% - Muslims still borrow least), so religion "
    "x residence cells ride on smaller samples; sample_size shows all "
    "surveyed households in the cell. NSO unit-data rider: religion is "
    "self-reported; the split is indicative; no sub-state estimates. "
    "Year=2018 is the as-on date; fielded January-December 2019."
)

ROUNDS = [
    {
        "year": 2012,
        "l2": "aidis-2013-wealth-by-religion.csv",
        "source_id": "aidis-2013",
        "source_document": "sources/nada/aidis-2013-v1/CSV_NSS_70th_Debt_&_Investment_Visit1_Jan_Dec_2013.zip",
        "note": NOTE_2012,
    },
    {
        "year": 2018,
        "l2": "aidis-2018-wealth-by-religion.csv",
        "source_id": "aidis-2019",
        "source_document": "sources/nss77-aidis/PROVENANCE-note.md",
        "note": NOTE_2018,
    },
]


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-institutional-credit-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = []
    for rnd in ROUNDS:
        with (L2_DIR / rnd["l2"]).open() as f:
            for r in csv.DictReader(f):
                rows.append({
                    "metric_id": "institutional-credit-share",
                    "geography_level": "national",
                    "geography_code": "IN", "year": rnd["year"],
                    "religion": r["religion"],
                    "residence": r["residence"],
                    "value": r["institutional_debt_share_pct"],
                    "denominator": "outstanding_cash_debt_of_indebted_households",
                    "sample_size": r["n_households"], "ci_lower": "", "ci_upper": "",
                    "source_id": rnd["source_id"],
                    "source_document": rnd["source_document"],
                    "extraction_run": extraction_run,
                    "methodology_note": rnd["note"].format(res=RES_WORD[r["residence"]]),
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
            print(f"  {r['year']} {r['religion']:9s}: {r['value']}%")


if __name__ == "__main__":
    canonicalize()
