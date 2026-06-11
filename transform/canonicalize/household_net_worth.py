"""
L2 -> L3 for the `household-net-worth` metric.

Reads:  extracted/aidis/aidis-2013-wealth-by-religion.csv
        extracted/aidis/aidis-2018-wealth-by-religion.csv
Writes: canonical/household-net-worth.csv

Average household net worth (assets minus outstanding debt, Rs nominal) by
religion of household head, from AIDIS (All-India Debt & Investment Survey)
unit-level microdata, Visit 1 - the stock-of-wealth measure the spending
(flow) cards cannot show. Two rounds, same survey design:

- NSS 70th round, reference date 30.06.2012 (year=2012), via the NADA API CSV
  conversion. Reproduces published AOD/IOI exactly and AVA within 0.75% (a
  documented empty-column defect in MoSPI's CSV conversion of block 10).
- NSS 77th round, reference date 30.06.2018 (year=2018), via MoSPI's own
  fixed-width TXT distribution surviving in the unlinked NSS7718/ directory
  (the NADA copy is a proprietary .Nesstar binary; see
  sources/nss77-aidis/PROVENANCE-note.md). Reproduces the published AVA and
  AOD EXACTLY to the rupee and IOI/institutional share at printed precision
  (MoSPI press note 24.08.2021).

Both rounds use the published asset concept (excludes bullion/ornaments,
roughly +3% if included, and durables). Values rounded to the nearest
Rs 1,000 (sampling error far exceeds this). Values are NOMINAL per round.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_DIR = REPO_ROOT / "extracted" / "aidis"
OUTPUT_PATH = REPO_ROOT / "canonical" / "household-net-worth.csv"
CANONICALIZER_VERSION = "2.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}

NOTE_2012 = (
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
    "survey was fielded January-December 2013. Values are nominal rupees of "
    "the round's reference date."
)

NOTE_2018 = (
    "Computed from AIDIS 2019 (NSS 77th round, Sch 18.2) Visit-1 unit-level "
    "microdata, MoSPI's original fixed-width TXT distribution (the NADA copy "
    "is a proprietary binary; provenance in sources/nss77-aidis/): average "
    "household assets (land, buildings, livestock, agricultural machinery, "
    "transport, financial assets including receivables; the published asset "
    "concept, which excludes gold/ornaments worth ~3% more) minus outstanding "
    "cash debt, {res}, as on 30.06.2018, weighted by the official multiplier. "
    "The estimator reproduces the published all-India average value of assets "
    "and average debt EXACTLY to the rupee, and the incidence of indebtedness "
    "and institutional share at printed precision (MoSPI press note "
    "24.08.2021). Land is valued at normative/guideline rates, not market "
    "prices. Rounded to the nearest Rs 1,000. NSO unit-data rider: religion "
    "is self-reported and the survey is stratified for states, not religions, "
    "so the split is indicative and no sub-state estimates are made. "
    "Year=2018 is the assets-as-on date; the survey was fielded "
    "January-December 2019. Values are nominal rupees of the round's "
    "reference date."
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
        f"canonicalize-household-net-worth-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = []
    for rnd in ROUNDS:
        with (L2_DIR / rnd["l2"]).open() as f:
            for r in csv.DictReader(f):
                rows.append({
                    "metric_id": "household-net-worth",
                    "geography_level": "national",
                    "geography_code": "IN", "year": rnd["year"],
                    "religion": r["religion"],
                    "residence": r["residence"],
                    "value": int(round(float(r["avg_net_worth_rs"]) / 1000.0) * 1000),
                    "denominator": "per_household",
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
            print(f"  {r['year']} {r['religion']:9s}: Rs {r['value']:,}")


if __name__ == "__main__":
    canonicalize()
