"""
L2 -> L3 for the `household-net-worth` metric.

Reads:  extracted/aidis/aidis-2013-wealth-by-religion.csv
Writes: canonical/household-net-worth.csv

Average household net worth (assets minus outstanding debt, Rs nominal) by
religion of household head, from AIDIS (All-India Debt & Investment Survey)
NSS 70th round Visit 1 unit-level microdata - the stock-of-wealth measure the
spending (flow) cards cannot show. Reference date 30.06.2012, so year=2012.
The published report (NSS KI 70/18.2) breaks wealth down by social group but
never by religion; the extraction (transform/aidis/extract_wealth_2013_by_religion.py)
reproduces the published all-India AOD/IOI exactly and AVA within 0.75% (the
residual is a documented empty-column defect in MoSPI's CSV conversion of
block 10, worth exactly the published 0.25-0.76% share of that block).
Values rounded to the nearest Rs 1,000 (sampling error far exceeds this).
AIDIS 2019 would be the second point but NADA ships it only as a proprietary
.Nesstar binary; its published anchors are recorded in nada/aidis-layout-map.md.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "aidis" / "aidis-2013-wealth-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "household-net-worth.csv"
CANONICALIZER_VERSION = "1.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}

NOTE = (
    "Computed from AIDIS 2013 (NSS 70th round, Sch 18.2) Visit-1 unit-level "
    "microdata pulled via the MoSPI NADA API: average household assets (land, "
    "buildings, livestock, agricultural machinery, transport, financial assets; "
    "the published asset concept, which excludes gold/ornaments worth ~4% more) "
    "minus outstanding cash debt, {res}, as on 30.06.2012, weighted by the "
    "official multiplier. The estimator reproduces the published all-India "
    "average debt and incidence of indebtedness EXACTLY and average assets "
    "within 0.75% (a documented empty-column defect in MoSPI's own CSV "
    "conversion of the non-farm-equipment block). Land is valued at "
    "normative/guideline rates, not market prices. Rounded to the nearest "
    "Rs 1,000. NSO unit-data rider: religion is self-reported and the survey "
    "is stratified for states, not religions, so the split is indicative and "
    "no sub-state estimates are made. Year=2012 is the assets-as-on date; the "
    "survey was fielded January-December 2013."
)


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-household-net-worth-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = []
    with L2_PATH.open() as f:
        for r in csv.DictReader(f):
            rows.append({
                "metric_id": "household-net-worth", "geography_level": "national",
                "geography_code": "IN", "year": 2012, "religion": r["religion"],
                "residence": r["residence"],
                "value": int(round(float(r["avg_net_worth_rs"]) / 1000.0) * 1000),
                "denominator": "per_household",
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
            print(f"  {r['religion']:9s}: Rs {r['value']:,}")


if __name__ == "__main__":
    canonicalize()
