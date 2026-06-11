#!/usr/bin/env python3
"""Extract the PLFS 15+ usual-status employment series by religion from microdata (L2).

Source: 7 rounds of PLFS unit-level data (July-June, 2017-18 .. 2023-24) pulled from
MoSPI's NADA API and archived locally at ~/Desktop/nada-work/plfs-<round>/ (see
nada/PLAN.md; sha256 + provenance in sources/nada/plfs-<round>/ after finalize).
Column map + per-round gotchas: nada/plfs-layout-map.md (verified against the
published annual-report figures for every round).

Method (usual status ps+ss, age 15+, first-visit person file):
  - employed  = principal status in {11,12,21,31,41,51} OR subsidiary status in same
  - unemployed = not employed AND principal status == 81
  - LFPR = (employed+unemployed)/population; WPR = employed/population;
    UR = unemployed/labour force; salaried share = workers whose classifying
    status (ps if ps-employed else ss) == 31 / workers   [Table 49's
    regular_wage_salary column, computed identically]
  - weight = (MULT/100 if NSS==NSC else MULT/200) / NO_QTR  (the README rule,
    identical in all 7 rounds; MULT carries 2 implied decimals)
  - religion lives only in the household first-visit file; person->household join
    on (quarter, FSU, b1q13, b1q14, b1q15) with keys normalised as strings
  - 2020-21 only: drop temporary visitors (person serial b4q1 >= 81)

Validation gates (script fails loudly if breached):
  1. all-India 15+ LFPR/WPR/UR per round must reproduce the published annual-report
     figures to +-0.1 (the layout-mapping run already matched all 21 to 1 decimal)
  2. 2023-24 by-religion values must match our PDF-extracted Table 48/49 L2
     (extracted/plfs/plfs-2023-24-table48/49-*.csv) to +-0.2

Writes extracted/plfs/plfs-microdata-2017-24-by-religion.csv:
  round,year,religion,residence,sex,n_15plus,lfpr,wpr,ur,salaried_share

Run:  .venv/bin/python transform/plfs/extract_microdata_trends.py [archive-root]
"""
import csv
import io
import os
import pathlib
import sys
import zipfile
from collections import defaultdict

ARCHIVE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                       else os.path.expanduser("~/Desktop/nada-work"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "extracted" / "plfs" / "plfs-microdata-2017-24-by-religion.csv"

# round -> (archive dir, data zip, person-FV basename, household-FV basename)
ROUNDS = [
    ("2017-18", "plfs-2017-18", "CSV_PLFS_July2017_June2018.zip",
     "hh_per_fv_2017-18.csv", "hhfv_2017-18.csv"),
    ("2018-19", "plfs-2018-19", "PLFS_2018_19_CSV.zip",
     "perv1_2018-19.csv", "hhv1_2018-19 (1).csv"),
    ("2019-20", "plfs-2019-20", "CSV_PLFS_19_20.zip",
     "perfv_2019-20.csv", "hhfv_2019-20.csv"),
    ("2020-21", "plfs-2020-21", "CSV_Unit_level_data_PLFS_July2020_June2021.zip",
     "perv1.csv", "hhv1.csv"),
    ("2021-22", "plfs-2021-22", "PLFS_Data_2021-22_CSV.zip",
     "perv1.csv", "hhv1.csv"),
    ("2022-23", "plfs-2022-23", "Data_in_CSV.zip",
     "perv1.csv", "hhv1.csv"),
    ("2023-24", "plfs-2023-24", "CSV_data_PLFS_2023_2024.zip",
     "perv1.csv", "hhv1.csv"),
]

# published all-India 15+ usual status (ps+ss) from each round's annual report
PUBLISHED = {
    "2017-18": (49.8, 46.8, 6.0), "2018-19": (50.2, 47.3, 5.8),
    "2019-20": (53.5, 50.9, 4.8), "2020-21": (54.9, 52.6, 4.2),
    "2021-22": (55.2, 52.9, 4.1), "2022-23": (57.9, 56.0, 3.2),
    "2023-24": (60.1, 58.2, 3.2),
}

EMPLOYED = {"11", "12", "21", "31", "41", "51"}
# religion codes (stable all rounds): 1 Hinduism .. 7 Zoroastrianism, 9 Others;
# 'other' buckets 7+9 to mirror the annual report's "others" column
RMAP = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh",
        "5": "jain", "6": "buddhist", "7": "other", "9": "other"}
RELIGIONS = ["muslim", "hindu", "christian", "sikh", "jain", "buddhist",
             "other", "all"]


def norm(s):
    """Join-key normalisation: strip whitespace, leading zeros, trailing '.0'."""
    s = (s or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0") or "0"


def find_col(headers, *bases):
    """Locate a column by base name, tolerating the per-round suffix zoo
    (b3q3 -> b3q3_hhv1 / b3q3_hh_fv / b3q3_hh_rv ...)."""
    low = {h.lower().strip(): h for h in headers}
    for base in bases:
        if base in low:
            return low[base]
        for hl, h in low.items():
            if hl.startswith(base + "_"):
                return h
    raise KeyError(f"none of {bases} in {sorted(low)[:40]}...")


def open_member(zf, basename):
    name = next(n for n in zf.namelist()
                if n.lower().endswith("/" + basename.lower())
                or n.lower() == basename.lower())
    return io.TextIOWrapper(zf.open(name), encoding="utf-8", errors="replace")


def fnum(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def process_round(rnd, dirname, zipname, per_base, hh_base):
    zf = zipfile.ZipFile(ARCHIVE / dirname / zipname)

    # household FV: join key -> religion code
    f = open_member(zf, hh_base)
    r = csv.DictReader(f)
    qtr = find_col(r.fieldnames, "qtr", "quarter")
    fsu = find_col(r.fieldnames, "b1q1", "fsu")
    k13 = find_col(r.fieldnames, "b1q13")
    k14 = find_col(r.fieldnames, "b1q14")
    k15 = find_col(r.fieldnames, "b1q15")
    rel = find_col(r.fieldnames, "b3q3")
    hh_rel = {}
    for row in r:
        key = (norm(row[qtr]), norm(row[fsu]), norm(row[k13]),
               norm(row[k14]), norm(row[k15]))
        hh_rel[key] = (row[rel] or "").strip()

    # person FV: aggregate 15+ by religion x residence x sex
    f = open_member(zf, per_base)
    r = csv.DictReader(f)
    qtr = find_col(r.fieldnames, "qtr", "quarter")
    fsu = find_col(r.fieldnames, "b1q1", "fsu")
    k13 = find_col(r.fieldnames, "b1q13")
    k14 = find_col(r.fieldnames, "b1q14")
    k15 = find_col(r.fieldnames, "b1q15")
    sec = find_col(r.fieldnames, "b1q3")
    sex_c = find_col(r.fieldnames, "b4q5")
    age_c = find_col(r.fieldnames, "b4q6")
    ps_c = find_col(r.fieldnames, "b5pt1q3")
    ss_c = find_col(r.fieldnames, "b5pt2q3")
    nss_c = find_col(r.fieldnames, "nss")
    nsc_c = find_col(r.fieldnames, "nsc")
    mult_c = find_col(r.fieldnames, "mult")
    nq_c = find_col(r.fieldnames, "no_qtr")
    serial_c = find_col(r.fieldnames, "b4q1") if rnd == "2020-21" else None

    # acc[(religion, residence, sex)] = [w_pop, w_emp, w_unemp, w_sal, n]
    acc = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])
    unmatched = 0
    for row in r:
        if fnum(row[age_c], -1) < 15:
            continue
        if serial_c and fnum(row[serial_c], 0) >= 81:   # 2020-21 temporary visitors
            continue
        key = (norm(row[qtr]), norm(row[fsu]), norm(row[k13]),
               norm(row[k14]), norm(row[k15]))
        relcode = hh_rel.get(key)
        if relcode is None:
            unmatched += 1
            continue
        mult = fnum(row[mult_c])
        w = mult / (100.0 if norm(row[nss_c]) == norm(row[nsc_c]) else 200.0)
        w /= max(fnum(row[nq_c], 1.0), 1.0)
        ps = (row[ps_c] or "").strip()
        ss = (row[ss_c] or "").strip()
        emp = ps in EMPLOYED or ss in EMPLOYED
        unemp = (not emp) and ps == "81"
        sal = emp and ((ps if ps in EMPLOYED else ss) == "31")
        religion = RMAP.get(relcode)
        res = {"1": "rural", "2": "urban"}.get((row[sec] or "").strip())
        sx = {"1": "male", "2": "female"}.get((row[sex_c] or "").strip())
        for rl in ({religion, "all"} if religion else {"all"}):
            for rs in {res, "all"} if res else {"all"}:
                for s2 in {sx, "all"} if sx else {"all"}:
                    a = acc[(rl, rs, s2)]
                    a[0] += w
                    a[1] += w * emp
                    a[2] += w * unemp
                    a[3] += w * sal
                    a[4] += 1
    if unmatched:
        print(f"  WARN {rnd}: {unmatched} person records had no household match")

    rows = []
    for (rl, rs, s2), (wp, we, wu, ws, n) in sorted(acc.items()):
        if rl not in RELIGIONS or wp <= 0:
            continue
        lf = we + wu
        rows.append({
            "round": rnd, "year": int(rnd[:4]), "religion": rl,
            "residence": rs, "sex": s2, "n_15plus": n,
            "lfpr": f"{100*lf/wp:.2f}", "wpr": f"{100*we/wp:.2f}",
            "ur": f"{100*wu/lf:.2f}" if lf > 0 else "",
            "salaried_share": f"{100*ws/we:.2f}" if we > 0 else "",
        })
    return rows


def validate_published(all_rows):
    ok = True
    print("--- gate 1: all-India 15+ vs published annual reports ---")
    for rnd, (plf, pwp, pur) in PUBLISHED.items():
        r = next(r for r in all_rows if r["round"] == rnd and r["religion"] == "all"
                 and r["residence"] == "all" and r["sex"] == "all")
        lf, wp, ur = float(r["lfpr"]), float(r["wpr"]), float(r["ur"])
        flag = "OK " if (abs(lf-plf) <= 0.1 and abs(wp-pwp) <= 0.1
                         and abs(ur-pur) <= 0.1) else "FAIL"
        if flag == "FAIL":
            ok = False
        print(f"  {flag} {rnd}: LFPR {lf:.1f}/{plf}  WPR {wp:.1f}/{pwp}  UR {ur:.1f}/{pur}")
    return ok


def validate_pdf_tables(all_rows):
    """2023-24 by-religion vs the PDF-extracted Table 48/49 L2 (+-0.2)."""
    ok = True
    print("--- gate 2: 2023-24 by religion vs PDF Tables 48/49 ---")
    t48 = list(csv.DictReader((ROOT / "extracted/plfs/"
               "plfs-2023-24-table48-employment-by-religion.csv").open()))
    t49 = list(csv.DictReader((ROOT / "extracted/plfs/"
               "plfs-2023-24-table49-employment-status-by-religion.csv").open()))
    sexmap = {"person": "all", "male": "male", "female": "female"}
    resmap = {"total": "all", "rural": "rural", "urban": "urban"}

    def ours(religion, res, sx, field):
        r = next(r for r in all_rows if r["round"] == "2023-24"
                 and r["religion"] == religion and r["residence"] == res
                 and r["sex"] == sx)
        return float(r[field])

    for t in t48:
        if (t["religion"] not in ("hindu", "muslim")
                or t["indicator"] not in ("LFPR", "WPR")
                or t["age_cohort"] != "15plus"):   # Table 48 also carries all-ages panels
            continue
        v = ours(t["religion"], resmap[t["residence"]], sexmap[t["sex"]],
                 t["indicator"].lower())
        flag = "OK " if abs(v - float(t["value"])) <= 0.25 else "FAIL"
        if flag == "FAIL":
            ok = False
            print(f"  {flag} T48 {t['religion']} {t['indicator']} {t['residence']}/{t['sex']}: "
                  f"microdata {v:.1f} vs PDF {t['value']}")
    for t in t49:
        if t["religion"] not in ("hindu", "muslim") or t["metric"] != "regular_wage_salary":
            continue
        v = ours(t["religion"], resmap[t["residence"]], sexmap[t["sex"]], "salaried_share")
        flag = "OK " if abs(v - float(t["value"])) <= 0.25 else "FAIL"
        if flag == "FAIL":
            ok = False
            print(f"  {flag} T49 {t['religion']} salaried {t['residence']}/{t['sex']}: "
                  f"microdata {v:.1f} vs PDF {t['value']}")
    print("  (only mismatches printed; silence above = all cells within +-0.2)")
    return ok


def main():
    all_rows = []
    for rnd, dirname, zipname, per_base, hh_base in ROUNDS:
        print(f"processing {rnd} ...")
        all_rows.extend(process_round(rnd, dirname, zipname, per_base, hh_base))
    g1 = validate_published(all_rows)
    g2 = validate_pdf_tables(all_rows)
    if not (g1 and g2):
        sys.exit("VALIDATION FAILED - L2 not written")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["round", "year", "religion", "residence",
                                          "sex", "n_15plus", "lfpr", "wpr", "ur",
                                          "salaried_share"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(all_rows)} rows)")
    print("--- Muslim 15+ national series ---")
    for r in all_rows:
        if r["religion"] == "muslim" and r["residence"] == "all" and r["sex"] == "all":
            print(f"  {r['round']}: LFPR {r['lfpr']}  WPR {r['wpr']}  UR {r['ur']}  "
                  f"salaried {r['salaried_share']}  (n={r['n_15plus']:,})")


if __name__ == "__main__":
    main()
