#!/usr/bin/env python3
"""School-education expenditure per student by religion, Comprehensive
Modular Survey: Education (CMS:E), NSS 80th round, April - June 2025,
unit-level CSV.

L1 source: the official CSV distribution pulled from the MoSPI NADA catalog
(id 255, idno DDI-IND-MOSPI-NSS-CMSE80-2025), banked with sha256 provenance
in sources/nada/education-2025/ (the CSVs stay local at
~/Desktop/nada-work/education-2025/). 52,085 households, 57,742 students
currently enrolled in school education (pre-primary including anganwadi up
to higher secondary, plus diploma/certificate up to higher-secondary
equivalent). Published as NSS Report 595 (banked alongside), whose primary
objective is estimating household expenditure on school education.

Indicator: average expenditure per enrolled student on school education
during the current academic year (course fee, textbooks/stationery,
uniform, transport, other items; private coaching is collected separately
and EXCLUDED, matching the published headline construct). Weight =
mult/100 (README_CMSE_2025 rule). Religion of household head from the
household file. Universe: current household members enrolled in school
(the report's 57,742-student count reproduces exactly on this universe;
erstwhile hostel-resident members ride in a separate thin file and are
outside the published per-student tables).

Validation gate (abort, nothing written, if any cell misses): the seven
published Report 595 cells - all-India 12,616 / rural 8,382 / urban 23,470
and by school type government 2,863 / private aided 15,364 / private
unaided recognised 28,693 / others 14,315 (school-type codes 4+5 combined;
the report's "others" bar) - within 0.5% relative. Observed worst gap
0.01%.

Run:  python transform/education/extract_education_2025_by_religion.py [data-dir]
Writes extracted/education/education-2025-school-spend-by-religion.csv.
"""
import os
import sys
import zipfile

import pandas as pd

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/nada-work/education-2025")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "extracted",
                   "education", "education-2025-school-spend-by-religion.csv")

KEY = ["fsu_serial_no", "second_stage_stratum_no", "sample_hhld_no"]
RELIGION = {1: "hindu", 2: "muslim", 3: "christian", 4: "sikh"}

# NSS Report 595 published all-India anchors (average school-education
# expenditure per enrolled student, Rs, current academic year).
REPORT_595 = [  # (label, sector, school-type codes, published Rs)
    ("all-India", None, None, 12616),
    ("rural", 1, None, 8382),
    ("urban", 2, None, 23470),
    ("government", None, {1}, 2863),
    ("private aided", None, {2}, 15364),
    ("private unaided", None, {3}, 28693),
    ("others", None, {4, 5}, 14315),
]


def _csv(name):
    z = os.path.join(DATA_DIR, "Data in CSV.zip")
    if os.path.exists(z):
        with zipfile.ZipFile(z) as zf:
            with zf.open(name) as f:
                return pd.read_csv(f)
    return pd.read_csv(os.path.join(DATA_DIR, name))


def main():
    hh = _csv("CMSE80HH25.csv")[KEY + ["religion"]]
    assert len(hh) == len(hh.drop_duplicates(KEY)), "household key not unique"
    print(f"households on file: {len(hh):,}")

    per = _csv("CMSE80PER25.csv")
    st = per[per["currently_enrolled_school"] == 1].merge(
        hh, on=KEY, how="left", validate="m:1")
    assert not st["religion"].isna().any(), "student without a household row"
    print(f"students enrolled in school: {len(st):,}")

    st["w"] = st["mult"] / 100.0
    st["exp"] = st["school_exp_total"].fillna(0)
    st["coach"] = st["private_coaching_exp_total"].fillna(0)
    st["rel"] = st["religion"].map(RELIGION).fillna("other")

    def avg(sel, field="exp"):
        return (sel["w"] * sel[field]).sum() / sel["w"].sum()

    print("--- gate: Report 595 per-student school expenditure ---")
    worst = 0.0
    for label, sec, types, pub in REPORT_595:
        sel = st
        if sec is not None:
            sel = sel[sel["sector"] == sec]
        if types is not None:
            sel = sel[sel["school_type"].isin(types)]
        got = avg(sel)
        diff = 100.0 * (got - pub) / pub
        worst = max(worst, abs(diff))
        print(f"  {label:16s}: {got:9,.0f}  (report {pub:7,}, "
              f"diff {diff:+.2f}%)")
    if worst > 0.5:
        sys.exit(f"VALIDATION FAILED: worst gap {worst:.2f}% > 0.5% - "
                 "not writing the extract.")
    print(f"validation OK (worst gap {worst:.2f}%)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rows = []
    for rel in ("muslim", "hindu", "christian", "sikh", "all"):
        sub = st if rel == "all" else st[st["rel"] == rel]
        for res, sec in (("all", None), ("rural", 1), ("urban", 2)):
            sel = sub if sec is None else sub[sub["sector"] == sec]
            gov = 100.0 * sel.loc[sel["school_type"] == 1, "w"].sum() / sel["w"].sum()
            rows.append([rel, res, f"{avg(sel):.0f}", f"{avg(sel, 'coach'):.0f}",
                         f"{gov:.1f}", len(sel)])
    pd.DataFrame(rows, columns=["religion", "residence", "avg_school_spend_rs",
                                "avg_coaching_rs", "pct_students_govt",
                                "n_students"]).to_csv(OUT, index=False)
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
