#!/usr/bin/env python3
"""School-education expenditure per student by religion, NSS 75th round
Schedule 25.2 (Household Social Consumption: Education, July 2017 - June
2018) unit-level fixed-width TXT.

L1 source: the eight R75252L0*.TXT files MoSPI still serves (unlinked) under
https://www.mospi.gov.in/sites/default/files/NSS75252E/ - the directory that
also hosts KI_Education_75th_Final.pdf (NSS Report 585's key indicators),
whose record counts (113,757 households on L01, 1,190,110 records across 8
levels) these files reproduce byte-exactly at records x 144 - 2. The NADA
catalog-151 distribution ships only a proprietary .Nesstar binary
(sources/nada/education-2017-18/), so this TXT mirror is the parseable
official channel. Files kept LOCAL at
~/Desktop/nada-work/education-2017-18-alt/; URLs + sha256 in
sources/nss75-education/PROVENANCE-note.md; byte map in
nada/education-layout-map.md.

Record = 142 chars (+CRLF), weight = MLT/100 if NSS == NSC else MLT/200
(sub-sample-combined rule), household key = FSU(4-8) + segment(31) +
second-stage stratum(32) + household no(33-34) - all as in Sch 25.0.

Output construct (the CMSE-2025-aligned trend leg): average expenditure per
student enrolled at SCHOOL levels (pre-primary, primary, upper primary,
secondary, higher secondary, diploma/certificate up to higher-secondary
equivalent; enrolment codes 06/07/08/10/11/12/13) on the basic course
during the current academic year, EXCLUDING private coaching (course fee +
books/stationery/uniform + transport + other; block 6 total minus its
coaching item), any course type. Expenditure counts what the household,
other households or non-government institutions incurred. Religion of
household head: level 02 byte 53.

Validation gate (abort, nothing written, if any cell misses 0.5%):
  - Statement 19 of NSS Report 585 (KI_Education_75th_Final.pdf): average
    TOTAL basic-course expenditure per student (including coaching, all
    levels 3-35) for any/general/technical course x rural/urban/all -
    9 cells, observed worst gap 0.01%;
  - Statement 21: the same total for GENERAL-course students at each school
    level x rural/urban/all - 18 cells, observed worst gap 0.01%.
The published statements never split by religion; the carded excl-coaching
school-level construct is the gated pipeline applied to the CMSE-matched
universe.

Run:  python transform/education/extract_education_2017_by_religion.py [data-dir]
Writes extracted/education/education-2017-school-spend-by-religion.csv.
"""
import csv
import os
import sys

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/nada-work/education-2017-18-alt")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "extracted",
                   "education", "education-2017-school-spend-by-religion.csv")

RELIGION = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh"}
SCHOOL_LEVELS = {"06", "07", "08", "10", "11", "12", "13"}
GENERAL = {"01", "02", "03", "04"}   # item 7: general course codes

# NSS Report 585 (KI_Education_75th_Final.pdf) all-India anchors:
# Statement 19 (rural, urban, all) - total basic-course exp incl coaching.
S19 = [("any course", "any", (5887, 19893, 9948)),
       ("general", "gen", (5240, 16308, 8331)),
       ("technical/prof", "tech", (32137, 64763, 50307))]
# Statement 21 - general course, by school level (rural, urban, all).
S21 = [({"06"}, "pre-primary", (5655, 14509, 8997)),
       ({"07"}, "primary", (3545, 13516, 6024)),
       ({"08"}, "upper primary", (3953, 15337, 6866)),
       ({"10"}, "secondary", (5856, 17518, 9013)),
       ({"11"}, "higher secondary", (9148, 23832, 13845)),
       ({"12", "13"}, "diploma below grad", (8545, 22281, 12045))]


def records(level):
    path = os.path.join(DATA_DIR, f"R75252L{level}.TXT")
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
        religion[hhkey(ln)] = RELIGION.get(ln[52], "other")
    print(f"households on file: {len(religion):,}")

    students = {}   # (household key, person serial) -> student dict
    for ln in records("05"):        # block 5: enrolment particulars
        students[(hhkey(ln), ln[39:41])] = {
            "sec": ln[14], "level": ln[50:52], "course": ln[52:54],
            "gov": ln[58] == "1", "w": weight(ln),
            "rel": religion.get(hhkey(ln), "other")}
    for ln in records("06"):        # block 6: basic-course expenditure
        k = (hhkey(ln), ln[39:41])
        if k in students:
            students[k]["total"] = money(ln[84:92])
            students[k]["coaching"] = money(ln[68:76])
    has = [s for s in students.values() if "total" in s]
    print(f"students: {len(students):,} (with expenditure block: {len(has):,})")

    def avg(sel, field="total"):
        den = sum(s["w"] for s in sel)
        return (sum(s["w"] * s[field] for s in sel) / den
                if den else float("nan"))

    worst = 0.0
    print("--- gate A: Statement 19 (total incl coaching, all levels) ---")
    for label, c, pubs in S19:
        for sec, lbl, pub in (("1", "rural", pubs[0]), ("2", "urban", pubs[1]),
                              (None, "all", pubs[2])):
            sel = [s for s in has
                   if (sec is None or s["sec"] == sec)
                   and (c == "any"
                        or (s["course"] in GENERAL) == (c == "gen"))]
            got = avg(sel)
            diff = 100.0 * (got - pub) / pub
            worst = max(worst, abs(diff))
            print(f"  {label:18s} {lbl:5s}: {got:9,.0f}  "
                  f"(report {pub:7,}, diff {diff:+.2f}%)")
    print("--- gate B: Statement 21 (general course, by school level) ---")
    for levs, label, pubs in S21:
        for sec, lbl, pub in (("1", "rural", pubs[0]), ("2", "urban", pubs[1]),
                              (None, "all", pubs[2])):
            sel = [s for s in has if s["level"] in levs
                   and s["course"] in GENERAL
                   and (sec is None or s["sec"] == sec)]
            got = avg(sel)
            diff = 100.0 * (got - pub) / pub
            worst = max(worst, abs(diff))
            print(f"  {label:18s} {lbl:5s}: {got:9,.0f}  "
                  f"(report {pub:7,}, diff {diff:+.2f}%)")
    if worst > 0.5:
        sys.exit(f"VALIDATION FAILED: worst gap {worst:.2f}% > 0.5% - "
                 "not writing the extract.")
    print(f"validation OK (worst gap {worst:.2f}% across 27 cells)")

    school = [s for s in has if s["level"] in SCHOOL_LEVELS]
    for s in school:
        s["school_exp"] = s["total"] - s["coaching"]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["religion", "residence", "avg_school_spend_rs",
                     "avg_coaching_rs", "pct_students_govt", "n_students"])
        for rel in ("muslim", "hindu", "christian", "sikh", "all"):
            for res, sec in (("all", None), ("rural", "1"), ("urban", "2")):
                sel = [s for s in school
                       if (rel == "all" or s["rel"] == rel)
                       and (sec is None or s["sec"] == sec)]
                den = sum(s["w"] for s in sel)
                gov = 100.0 * sum(s["w"] for s in sel if s["gov"]) / den
                wr.writerow([rel, res,
                             f"{avg(sel, 'school_exp'):.0f}",
                             f"{avg(sel, 'coaching'):.0f}",
                             f"{gov:.1f}", len(sel)])
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
