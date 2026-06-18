#!/usr/bin/env python3
"""Higher-education Gross Attendance Ratio by religion, NSS 75th round Schedule
25.2 (Household Social Consumption: Education, July 2017 - June 2018) unit-level
fixed-width TXT.

WHY THIS REPLACES THE AISHE GER. AISHE tags only ~7% of all enrolment to a
minority religion (Muslim Minority + one grouped "Other Minority Community");
the rest is religion-not-reported. So the AISHE-derived Muslim GER (~9-10%) is
an administrative UNDERCOUNT, not comparable to the fully-counted national GER,
and AISHE publishes no Hindu figure at all. The tell: AISHE puts "other
minorities" (Christian, Sikh, Jain - among India's most educated communities)
at ~13%, which cannot be their true rate. A household survey samples everyone
and asks religion, so Muslim, Hindu and all-India sit on ONE basis. NSS 75th is
the dedicated education survey; PLFS publishes no attendance ratio and runs ~8pp
above NSS for the same year, so it is not a validatable trend source. The 71st
(2014) education round is Nesstar-locked. Hence: one validated round, a snapshot.

GAR (the NSS-published construct, Report 585 / KI Statement 8) for "post higher
secondary" = persons CURRENTLY ATTENDING graduate or postgraduate education,
over the population aged 18-23 (the official age group for that level), x100.
Numerator counts attenders of ANY age (so GAR can exceed NAR). Level codes from
the questionnaire (block 5 item 6 "level of current enrolment"): 15 graduate,
16 postgraduate & above. Code 14 (diploma/certificate at graduation level) is
EXCLUDED - including it overshoots the published cells by ~6%; {15,16} reproduce
all nine Statement 8 cells to <=0.05pp (graduate + PG IS "post higher secondary"
in the GAR ladder, with diplomas held out).

Byte map (nada/education-layout-map.md + datalay75_252.xls):
  L02 block 3 (household): religion of head byte 53 (0-idx 52).
  L04 block 4 (person roster, the DENOMINATOR): person serial 40-41, gender 43,
      age 44-46.
  L05 block 5 (currently attending, the NUMERATOR): person serial 40-41, level
      of current enrolment 51-52. (No gender in L05 -> join to L04 by serial.)
  Common-ID household key = FSU(4-8) + hamlet(31) + SSS(32) + hhld(33-34); record
  142 chars; weight = MLT/100 if NSS==NSC else MLT/200 (every record here is
  NSS!=NSC, so a uniform /200 - it cancels in the ratio, confirmed by the gate).

Validation gate (abort, nothing written, if any of the 9 all-India cells misses
0.25pp): NSS Report 585 (KI_Education_75th_Final.pdf) Statement 8, post higher
secondary GAR, rural/urban/all x male/female/person. Observed worst gap 0.05pp.
The published statement never splits by religion (same situation as
school-edu-spend); the religion split is the validated pipeline applied to the
religion grouping variable.

Run:  python transform/education/extract_higher_ed_gar_2017_by_religion.py [data-dir]
Writes extracted/education/higher-ed-gar-2017-by-religion.csv.
"""
import csv
import os
import sys
from collections import defaultdict

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/nada-work/education-2017-18-alt")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "extracted",
                   "education", "higher-ed-gar-2017-by-religion.csv")

RELIGION = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh",
            "5": "jain", "6": "buddhist", "7": "zoroastrian", "9": "other"}
HIGHER = {"15", "16"}            # graduate + postgraduate & above (post higher secondary)
SEX = {"1": "male", "2": "female"}

# NSS Report 585 Statement 8, post higher secondary GAR (rural, urban, rural+urban).
PUB = {("1", "person"): 18.3, ("1", "male"): 20.7, ("1", "female"): 15.6,
       ("2", "person"): 33.4, ("2", "male"): 34.1, ("2", "female"): 32.5,
       ("all", "person"): 22.8, ("all", "male"): 24.7, ("all", "female"): 20.7}


def records(level):
    with open(os.path.join(DATA_DIR, f"R75252L{level}.TXT"),
              encoding="ascii", errors="replace") as f:
        for line in f:
            yield line.rstrip("\r\n")


def hhkey(line):
    return line[3:8] + line[30:34]


def weight(line):
    mlt = int(line[132:142])
    return mlt / 100.0 if line[126:129] == line[129:132] else mlt / 200.0


def main():
    religion = {}
    for ln in records("02"):
        religion[hhkey(ln)] = RELIGION.get(ln[52], "other")

    # L04 person roster: denominator (age 18-23) + (religion, sex) lookup keyed
    # on (household, person serial) so the L05 numerator can borrow gender.
    den = defaultdict(float)          # (sex, residence, religion) -> weighted pop 18-23
    den_n = defaultdict(int)
    roster = {}                       # (hhkey, serial) -> (religion, sex)
    for ln in records("04"):
        rel = religion.get(hhkey(ln), "other")
        sx = SEX.get(ln[42], "other")
        roster[(hhkey(ln), ln[39:41])] = (rel, sx)
        a = ln[43:46].strip()
        if a.isdigit() and 18 <= int(a) <= 23:
            res = ln[14]
            w = weight(ln)
            for r in (rel, "all"):
                for s in (sx, "person"):
                    for rs in (res, "all"):
                        den[(s, rs, r)] += w
                        den_n[(s, rs, r)] += 1

    # L05 currently-attending: numerator (level in HIGHER), any age.
    num = defaultdict(float)
    num_n = defaultdict(int)
    for ln in records("05"):
        if ln[50:52] not in HIGHER:
            continue
        rel, sx = roster.get((hhkey(ln), ln[39:41]), ("other", "other"))
        res = ln[14]
        w = weight(ln)
        for r in (rel, "all"):
            for s in (sx, "person"):
                for rs in (res, "all"):
                    num[(s, rs, r)] += w
                    num_n[(s, rs, r)] += 1

    def gar(s, rs, r):
        d = den[(s, rs, r)]
        return 100.0 * num[(s, rs, r)] / d if d else float("nan")

    worst = 0.0
    print("--- gate: Statement 8 post-higher-secondary GAR (all-India) ---")
    for (rs, s), pub in sorted(PUB.items()):
        got = gar(s, rs, "all")
        diff = got - pub
        worst = max(worst, abs(diff))
        rsn = {"1": "rural", "2": "urban", "all": "all"}[rs]
        print(f"  {rsn:6s} {s:7s}: {got:6.2f}  (report {pub:5.1f}, diff {diff:+.2f})")
    if worst > 0.25:
        sys.exit(f"VALIDATION FAILED: worst gap {worst:.2f}pp > 0.25pp - not writing.")
    print(f"validation OK (worst gap {worst:.2f}pp across 9 cells)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["religion", "sex", "residence", "gar_pct",
                     "n_attending", "n_pop_18_23"])
        for r in ("muslim", "hindu", "christian", "sikh", "jain", "buddhist", "all"):
            for s in ("person", "male", "female"):
                for rs in ("all", "1", "2"):
                    g = gar(s, rs, r)
                    if den_n[(s, rs, r)] == 0:
                        continue
                    wr.writerow([r, s, {"1": "rural", "2": "urban", "all": "all"}[rs],
                                 f"{g:.2f}", num_n[(s, rs, r)], den_n[(s, rs, r)]])
    print(f"wrote {os.path.relpath(OUT)}")
    print("national person GAR: " + ", ".join(
        f"{r} {gar('person','all',r):.1f}%" for r in ("muslim", "hindu", "all")))


if __name__ == "__main__":
    main()
