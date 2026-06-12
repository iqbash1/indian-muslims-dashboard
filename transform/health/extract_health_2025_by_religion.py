#!/usr/bin/env python3
"""Out-of-pocket hospitalisation expenditure by religion, NSS 80th round
Schedule 25.0 (Household Social Consumption: Health, January - December 2025)
unit-level CSV.

L1 source: the official CSV distribution pulled from the MoSPI NADA catalog
(id 290, idno DDI-IND-NSO-HSCHealth80R-Jan2025-Dec2025), banked with sha256
provenance in sources/nada/health-2025/ (the 148 MB of CSVs stay local at
~/Desktop/nada-work/health-2025/). Survey of 1,39,732 households; the
release's stated PRIMARY design objective is estimating households'
out-of-pocket medical expenses.

Indicator: average out-of-pocket medical expenditure (OOPME) per
hospitalisation case (excluding childbirth) during the last 365 days,
exactly the press-note construct (PIB press note, April 2026, banked in
sources/nada/health-2025/):
  OOPME = medical expenditure total (b7i12: package, fees, medicines,
          diagnostics, bed charges, other medical; transport and food
          excluded) - amount reimbursed by insurance/employer (b7i16).
Childbirth = nature-of-ailment codes 87/88/89 (b6i5). Type of medical
institution (b6i7): 1 govt/public, 2 charitable/trust/NGO, 3 private
(incl. government-empanelled). Religion of household head: L1 b5i2.
Weight = mult/100 (final multiplier posted; README_HEALTH_25pt0 rule,
no sub-sample halving in this round's design).

Validation gate (abort, nothing written, if any cell misses): OOPME per
case must reproduce all SIX published press-note cells (all-India
all/rural/urban 34,064/31,484/38,688 and by institution public 6,631 /
charitable 39,530 / private 50,508) within 0.5% relative - observed worst
gap 0.01%.

Run:  python transform/health/extract_health_2025_by_religion.py [data-dir]
Writes extracted/health/health-2025-oopme-by-religion.csv and prints the
validation table.
"""
import os
import sys

import pandas as pd

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/nada-work/health-2025/"
    "CSV_data_household_social_consumption_heaith_Jan_Dec25")
OUT = os.path.join(os.path.dirname(__file__), "..", "..",
                   "extracted", "health", "health-2025-oopme-by-religion.csv")

KEY = ["fsu", "sd", "sss", "hhd"]
RELIGION = {1: "hindu", 2: "muslim", 3: "christian", 4: "sikh"}
CHILDBIRTH = {87, 88, 89}

# PIB press note (April 2026) published all-India OOPME anchors.
PRESS_NOTE = [  # (label, sector, institution, published Rs)
    ("all-India", None, None, 34064),
    ("rural", 1, None, 31484),
    ("urban", 2, None, 38688),
    ("govt/public", None, 1, 6631),
    ("charitable/NGO", None, 2, 39530),
    ("private", None, 3, 50508),
]


def main():
    l1 = pd.read_csv(os.path.join(DATA_DIR, "hhscsL1.csv"),
                     usecols=KEY + ["b5i2"])
    assert len(l1) == len(l1.drop_duplicates(KEY)), "household key not unique"
    print(f"households on file: {len(l1):,}")

    l4 = pd.read_csv(os.path.join(DATA_DIR, "hhscsL4.csv"),
                     usecols=KEY + ["sec", "b6i5", "b6i7", "b7i12", "b7i16",
                                    "mult"])
    cases = l4[~l4["b6i5"].isin(CHILDBIRTH)].merge(
        l1, on=KEY, how="left", validate="m:1")
    assert not cases["b5i2"].isna().any(), "case without a household record"
    print(f"hospitalisation cases: {len(l4):,} "
          f"({len(l4) - len(cases):,} childbirth excluded)")

    cases["w"] = cases["mult"] / 100.0
    cases["oop"] = cases["b7i12"].fillna(0) - cases["b7i16"].fillna(0)
    cases["religion"] = cases["b5i2"].map(RELIGION).fillna("other")

    def cells(rel=None, sec=None, inst=None):
        sel = cases
        if rel is not None:
            sel = sel[sel["religion"] == rel]
        if sec is not None:
            sel = sel[sel["sec"] == sec]
        if inst is not None:
            sel = sel[sel["b6i7"] == inst]
        wsum = sel["w"].sum()
        oop = (sel["w"] * sel["oop"]).sum() / wsum
        pub = sel.loc[sel["b6i7"] == 1, "w"].sum() / wsum * 100.0
        return oop, pub, len(sel)

    print("--- gate: press-note OOPME per case ---")
    worst = 0.0
    for label, sec, inst, pub in PRESS_NOTE:
        got = cells(sec=sec, inst=inst)[0]
        diff = 100.0 * (got - pub) / pub
        worst = max(worst, abs(diff))
        print(f"  {label:15s}: {got:10,.0f}  (press note {pub:7,}, "
              f"diff {diff:+.2f}%)")
    if worst > 0.5:
        sys.exit(f"VALIDATION FAILED: worst gap {worst:.2f}% > 0.5% - "
                 "not writing the extract.")
    print(f"validation OK (worst gap {worst:.2f}%)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rows = []
    for rel in ("muslim", "hindu", "christian", "sikh", "all"):
        for res, sec in (("all", None), ("rural", 1), ("urban", 2)):
            oop, pub, n = cells(None if rel == "all" else rel, sec)
            rows.append([rel, res, f"{oop:.0f}", f"{pub:.1f}", n])
    pd.DataFrame(rows, columns=["religion", "residence", "avg_oopme_rs",
                                "pct_cases_public", "n_cases"]).to_csv(
        OUT, index=False)
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
