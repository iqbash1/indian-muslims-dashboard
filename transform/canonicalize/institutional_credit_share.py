"""
L2 -> L3 for the `institutional-credit-share` metric.

Reads:  extracted/aidis/aidis-2013-wealth-by-religion.csv
Writes: canonical/institutional-credit-share.csv

Of the cash debt indebted households owe, the share borrowed from
INSTITUTIONAL lenders (banks, co-operatives, government and related agencies)
rather than moneylenders, shopkeepers, relatives and other informal sources -
the credit-access measure the Sachar Committee flagged. From AIDIS 2013 Visit-1
unit-level microdata (reference date 30.06.2012, so year=2012). The published
report gives this by state and social group, never by religion; the extraction
reproduces the published all-India shares exactly (rural 56.0 / urban 84.5,
KI(70/18.2) Table 8). Credit-agency code 09 "others" is non-institutional
despite sitting inside the institutional numeric run (the layout trap recorded
in nada/aidis-layout-map.md).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "aidis" / "aidis-2013-wealth-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "institutional-credit-share.csv"
CANONICALIZER_VERSION = "1.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}

NOTE = (
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


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-institutional-credit-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = []
    with L2_PATH.open() as f:
        for r in csv.DictReader(f):
            rows.append({
                "metric_id": "institutional-credit-share",
                "geography_level": "national",
                "geography_code": "IN", "year": 2012, "religion": r["religion"],
                "residence": r["residence"],
                "value": r["institutional_debt_share_pct"],
                "denominator": "outstanding_cash_debt_of_indebted_households",
                "sample_size": r["n_households"], "ci_lower": "", "ci_upper": "",
                "source_id": "aidis-2013",
                "source_document": "sources/nada/aidis-2013-v1/CSV_NSS_70th_Debt_&_Investment_Visit1_Jan_Dec_2013.zip",
                "extraction_run": extraction_run,
                "methodology_note": NOTE.format(res=RES_WORD[r["residence"]]),
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
            print(f"  {r['religion']:9s}: {r['value']}%")


if __name__ == "__main__":
    canonicalize()
