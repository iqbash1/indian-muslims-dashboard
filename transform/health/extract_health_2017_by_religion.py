#!/usr/bin/env python3
"""Out-of-pocket hospitalisation expenditure by religion, NSS 75th round
Schedule 25.0 (Household Social Consumption: Health, July 2017 - June 2018)
unit-level fixed-width TXT.

L1 source: the thirteen R75250L0*.TXT files MoSPI still serves (unlinked)
under https://www.mospi.gov.in/sites/default/files/NSS75250H/ - the same
directory that hosts KI_Health_75th_Final.pdf (NSS Report 586's key
indicators) and README75_250.doc, whose record counts (113,823 households on
L01, 1,342,307 records across the 13 levels) these files reproduce
byte-exactly at records x 144 - 2. The NADA catalog-152 distribution of the
same survey ships only a proprietary .Nesstar binary
(sources/nada/health-2017-18/), so this TXT mirror is the parseable official
channel. Files are kept LOCAL at ~/Desktop/nada-work/health-2017-18-alt/;
URLs + sha256 in sources/nss75-health/PROVENANCE-note.md; byte map in
nada/health-layout-map.md.

Record = 142 chars (+CRLF): bytes 1-126 data, 127-129 NSS, 130-132 NSC,
133-142 final multiplier with two implied decimals. Weight = MLT/100 if
NSS == NSC else MLT/200 (sub-sample-combined estimates; README75_250 rule -
unlike NSS 76th Sch 1.2 there IS a halving here). Household key =
FSU(4-8) + segment(31) + second-stage stratum(32) + household no(33-34).

Indicator: average out-of-pocket medical expenditure (OOPME) per
hospitalisation case (excluding childbirth) during the last 365 days, the
headline construct of the 2025 round's release, computed identically here:
  OOPME = medical expenditure (block 7 item 11: package, fees, medicines,
          diagnostics, bed charges, other medical; transport and food
          excluded) - amount reimbursed by insurance/employer (item 15).
Childbirth = nature-of-ailment codes 87/88/89 (block 6 item 4). Type of
medical institution (block 6 item 6): 1 govt/public, 2 charitable/trust/NGO,
3 private. Religion of household head: level 02 byte 54.

Validation gate (abort, nothing written, if any cell misses):
  - gross medical expenditure per case must reproduce all NINE cells of
    NSS Report 586 Statement 3.15 (public/private/all x rural/urban/all)
    within 0.5% relative - observed worst gap 0.01%;
  - reimbursement as % of medical expenditure must reproduce Statement 3.19
    (rural 4.4, urban 16.8) within 0.2pp - observed exact.

Run:  python transform/health/extract_health_2017_by_religion.py [data-dir]
Writes extracted/health/health-2017-oopme-by-religion.csv and prints the
validation table.
"""
import csv
import os
import sys

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/nada-work/health-2017-18-alt")
OUT = os.path.join(os.path.dirname(__file__), "..", "..",
                   "extracted", "health", "health-2017-oopme-by-religion.csv")

RELIGION = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh"}
CHILDBIRTH = {"87", "88", "89"}

# NSS Report 586 (KI_Health_75th_Final.pdf) published all-India anchors.
S315 = [  # Statement 3.15: gross medical exp per case (rural, urban, all)
    ("all hospitals", None, (16676, 26475, 20135)),
    ("public", "1", (4290, 4837, 4452)),
    ("private", "3", (27347, 38822, 31845)),
]
S319 = [("1", 4.4), ("2", 16.8)]  # Statement 3.19: reimb % of medical exp


def records(level):
    """Yield raw lines of one R75250L{level}.TXT file."""
    path = os.path.join(DATA_DIR, f"R75250L{level}.TXT")
    with open(path, encoding="ascii", errors="replace") as f:
        for line in f:
            yield line.rstrip("\r\n")


def hhkey(line):
    return line[3:8] + line[30:34]


def weight(line):
    mlt = int(line[132:142])
    return mlt / 100.0 if line[126:129] == line[129:132] else mlt / 200.0


def money(s):
    s = s.strip()
    return int(s) if s else 0


def main():
    religion = {}
    for ln in records("02"):
        religion[hhkey(ln)] = RELIGION.get(ln[53], "other")
    print(f"households on file: {len(religion):,}")

    cases = {}   # (household key, case serial) -> case dict
    for ln in records("05"):        # block 6: case particulars
        cases[(hhkey(ln), ln[37:39])] = {
            "sec": ln[14], "ail": ln[44:46], "inst": ln[47],
            "w": weight(ln)}
    for ln in records("06"):        # block 7 items 1-14: expenditure
        cases[(hhkey(ln), ln[37:39])]["med"] = money(ln[93:101])
    for ln in records("07"):        # block 7 items 15-20: reimbursement
        cases[(hhkey(ln), ln[37:39])]["reimb"] = money(ln[44:52])

    nc = [(k, c) for k, c in cases.items() if c["ail"] not in CHILDBIRTH]
    print(f"hospitalisation cases: {len(cases):,} "
          f"({len(cases) - len(nc):,} childbirth excluded)")
    assert all("med" in c and "reimb" in c for _, c in nc), \
        "case missing its block-7 expenditure record"

    def cells(rel=None, sec=None, inst=None):
        sel = [c for k, c in nc
               if (rel is None or religion.get(k[0]) == rel)
               and (sec is None or c["sec"] == sec)
               and (inst is None or c["inst"] == inst)]
        wsum = sum(c["w"] for c in sel)
        med = sum(c["w"] * c["med"] for c in sel)
        oop = sum(c["w"] * (c["med"] - c["reimb"]) for c in sel)
        pub = sum(c["w"] for c in sel if c["inst"] == "1")
        return (med / wsum if wsum else float("nan"),
                oop / wsum if wsum else float("nan"),
                100.0 * pub / wsum if wsum else float("nan"),
                len(sel))

    print("--- gate: Statement 3.15 gross medical expenditure per case ---")
    worst = 0.0
    for label, inst, pubs in S315:
        for sec, lbl, pub in (("1", "rural", pubs[0]), ("2", "urban", pubs[1]),
                              (None, "all", pubs[2])):
            got = cells(sec=sec, inst=inst)[0]
            diff = 100.0 * (got - pub) / pub
            worst = max(worst, abs(diff))
            print(f"  {label:14s} {lbl:6s}: {got:10,.0f}  "
                  f"(report {pub:7,}, diff {diff:+.2f}%)")
    if worst > 0.5:
        sys.exit(f"VALIDATION FAILED: worst gap {worst:.2f}% > 0.5% - "
                 "not writing the extract.")

    print("--- gate: Statement 3.19 reimbursement share of medical exp ---")
    for sec, pub in S319:
        sel = [c for _, c in nc if c["sec"] == sec]
        got = (100.0 * sum(c["w"] * c["reimb"] for c in sel)
               / sum(c["w"] * c["med"] for c in sel))
        lbl = "rural" if sec == "1" else "urban"
        print(f"  {lbl:6s}: {got:5.1f}  (report {pub}, diff {got - pub:+.2f}pp)")
        if abs(got - pub) > 0.2:
            sys.exit(f"VALIDATION FAILED: reimbursement share {lbl} "
                     f"{got:.2f} vs published {pub}.")
    print(f"validation OK (worst expenditure gap {worst:.2f}%)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["religion", "residence", "avg_oopme_rs", "avg_medical_rs",
                     "pct_cases_public", "n_cases"])
        for rel in ("muslim", "hindu", "christian", "sikh", "all"):
            for res, sec in (("all", None), ("rural", "1"), ("urban", "2")):
                med, oop, pub, n = cells(None if rel == "all" else rel, sec)
                wr.writerow([rel, res, f"{oop:.0f}", f"{med:.0f}",
                             f"{pub:.1f}", n])
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
