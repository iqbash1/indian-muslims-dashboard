"""
L2 -> L3 for the NSS-76th-round housing & basic-services cards (one script,
three canonical files - the indicators share one source, one method, one
validation gate, so they canonicalise together):

  improved-water-premises -> canonical/improved-water-premises.csv
  household-electricity   -> canonical/household-electricity.csv
  pucca-house             -> canonical/pucca-house.csv

Reads extracted/nss76/nss76-2018-housing-by-religion.csv, written by
transform/nss76/extract_housing_2018_by_religion.py from the original
fixed-width TXT distribution still served by mospi.gov.in (the NADA-channel
rar holds only a proprietary .Nesstar binary; the TXT mirror is the parseable
channel - sha256 + URLs in sources/nss76/PROVENANCE-note.md). The extraction's
validation gate reproduces NSS Report 584's all-India values across 24 cells
to a worst gap of 0.24pp (18 cells exact to the printed decimal).

The L2 carries 9 indicators; the latrine measures are NOT carded (the NFHS-5
toilet-access card covers sanitation; the NSS latrine numbers stay in the L2
and the runbook to avoid two near-identical cards with different definitions).
Survey period July-December 2018 -> year=2018.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "nss76" / "nss76-2018-housing-by-religion.csv"
CANONICALIZER_VERSION = "1.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}

# metric id -> (L2 indicator key, indicator phrase for the note)
CARDS = {
    "improved-water-premises": (
        "water_improved_within_premises",
        "households whose principal source of drinking water is an improved "
        "source located within the household premises"),
    "household-electricity": (
        "electricity",
        "households with electricity for domestic use"),
    "pucca-house": (
        "pucca_structure",
        "households living in a pucca (permanent-material) structure"),
}

NOTE = (
    "Computed from NSS 76th round Schedule 1.2 (Drinking Water, Sanitation, "
    "Hygiene and Housing Condition, July-December 2018) unit-level microdata: "
    "share of {what}, {res}, by religion of household head, weighted by the "
    "official multiplier. Source data is the original fixed-width TXT "
    "distribution still served by mospi.gov.in (MoSPI's current NADA catalog "
    "ships this survey only as a proprietary binary); sha256 + re-fetch URLs "
    "committed in sources/nss76/. The extraction reproduces the published "
    "Report 584 all-India values across 24 validation cells to a worst gap of "
    "0.24 percentage points. NSO unit-data rider: religion is self-reported "
    "and the survey is stratified for states, so the split is indicative and "
    "no sub-state estimates are made. Year=2018 = survey period (Jul-Dec 2018)."
)


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-nss76-housing-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    l2 = list(csv.DictReader(L2_PATH.open()))
    for mid, (key, what) in CARDS.items():
        rows = []
        for r in l2:
            if r["indicator"] != key:
                continue
            rows.append({
                "metric_id": mid, "geography_level": "national",
                "geography_code": "IN", "year": 2018, "religion": r["religion"],
                "residence": r["residence"], "value": r["value_pct"],
                "denominator": "households",
                "sample_size": r["n_households"], "ci_lower": "", "ci_upper": "",
                "source_id": "nss76-housing",
                "source_document": "sources/nss76/PROVENANCE-note.md",
                "extraction_run": extraction_run,
                "methodology_note": NOTE.format(what=what, res=RES_WORD[r["residence"]]),
                "break_flag": "false",
            })
        out = REPO_ROOT / "canonical" / f"{mid}.csv"
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            w.writerows(rows)
        vals = {r["religion"]: r["value"] for r in rows if r["residence"] == "all"}
        print(f"wrote canonical/{mid}.csv ({len(rows)} rows)  "
              f"muslim {vals.get('muslim')} hindu {vals.get('hindu')} all {vals.get('all')}")


if __name__ == "__main__":
    canonicalize()
