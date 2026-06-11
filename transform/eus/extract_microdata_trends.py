#!/usr/bin/env python3
"""Extract the pre-PLFS EUS 15+ usual-status employment series by religion (L2).

Source: the three quinquennial NSS Employment & Unemployment Survey (Schedule
10) rounds whose unit data NADA ships as plain CSV zips, banked locally:
  61st  July 2004 - June 2005   ~/Desktop/nada-work/eus-2004-05/
  66th  July 2009 - June 2010   ~/Desktop/nada-work/eus-2009-10/
  68th  July 2011 - June 2012   ~/Desktop/nada-work/eus-2011-12/
(sha256 + provenance committed in sources/nada/eus-<round>/). The 64th round
(2007-08, Sch 10.2) is EXCLUDED: it is the thin annual migration-focused
round and NSSO published no employment-by-religion tables for it (verified in
Report 531), so there is nothing to gate a by-religion extraction against.

Method (usual status ps+ss, mirroring transform/plfs/extract_microdata_trends.py):
  - employed  = principal status in {11,12,21,31,41,51} OR subsidiary status in
    same (block 5.2 rows exist only for persons with a subsidiary activity)
  - unemployed = not employed AND principal status == 81
  - LFPR = (employed+unemployed)/population; WPR = employed/population;
    UR = unemployed/labour force; salaried share = workers whose classifying
    status (ps if ps-employed else ss) == 31 / workers
  - weight = the precomputed combined multiplier shipped on every person row
    (2004-05 WEIGHT_COMBINED, 2009-10 WEIGHT, 2011-12 Multiplier_comb). All
    published rates are weighted ratios, so the multiplier's scale cancels.
  - religion lives in the household-characteristics block (2004-05: the
    merged blocks-1-2-3 level-01 file), joined on HHID; sex joins from block
    4 where block 5.1 lacks it (2009-10 via PID, 2011-12 via
    HHID+person-serial).

Validation gates (script exits without writing the L2 if breached):
  All-ages LFPR / WPR / UR per 1000, by religion (muslim, hindu, christian,
  sikh, all) x sector x sex, must reproduce NSS Report No. 568 Statements
  3.12 / 3.13 / 3.17 (which tabulate all three rounds side by side; Report
  552's overlapping 2004-05/2009-10 columns agree) within +-1.2 per 1000.
  UR is a ratio over the labour force, so published-rounding noise in the
  unemployed population share amplifies by 1000/LFPR. That share is itself
  the difference of two independently rounded published statements (LFPR
  minus WPR, each +-0.5/1000), so its noise bound is +-0.75/1000 (between
  RMS and worst case): per-cell tolerance max(1.5, 750/published-LFPR), which
  only matters for female cells (LFPR 100-350). Verified directly: in every
  such cell the computed LFPR and WPR match the published value at printed
  precision, so the UR residual is second-order arithmetic, not estimation
  error. Salaried share per 1000 workers vs Report 568 Statement 3.16
  (2011-12) and Report 552 Statement 3.16 (2009-10) within +-2. The 2004-05
  salaried share has no reliable digital anchor (Report 521's Statement 3.14
  PDF text fails its own row-sum check), so it rides on the same validated
  machinery and is printed for eyeball reconciliation instead.

Writes extracted/eus/eus-microdata-2004-12-by-religion.csv:
  round,year,religion,residence,sex,n_15plus,lfpr,wpr,ur,salaried_share
(15+ rates in percent, same schema as the PLFS microdata L2; year = start of
the July-June reference period: 2004, 2009, 2011.)

Run:  .venv/bin/python transform/eus/extract_microdata_trends.py [archive-root]
"""
import csv
import io
import os
import pathlib
import sys
import zipfile
from collections import Counter, defaultdict

ARCHIVE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                       else os.path.expanduser("~/Desktop/nada-work"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "extracted" / "eus" / "eus-microdata-2004-12-by-religion.csv"

EMPLOYED = {"11", "12", "21", "31", "41", "51"}
RMAP = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh",
        "5": "jain", "6": "buddhist", "7": "other", "9": "other"}
RELIGIONS = ["muslim", "hindu", "christian", "sikh", "jain", "buddhist",
             "other", "all"]
GATE_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "all")

# Per-round file/column adapters (verified against the zips' own headers;
# 2009-10 block 5.1 lacks Sex -> joined from block 4 by PID; 2011-12 has no
# PID column -> joined by HHID+person-serial).
ROUNDS = [
    {
        "round": "2004-05", "year": 2004, "dir": "eus-2004-05",
        "zip": "Emp_Unemp_2004_2005_CSV.zip",
        "hh_member": "Block_1_2_and_3_level_01.csv",
        "hh_key": "HHID", "hh_rel": "RELIGION",
        "ps_member": "Block_5pt1_level_04.csv",
        "ps_cols": {"hh": "HHID", "pid": "PID", "age": "Age", "sex": "Sex",
                    "status": "Usual_principal_activity_status",
                    "weight": "WEIGHT_COMBINED", "sector": "Sector"},
        "ss_member": "Block_5pt2_level_05.csv",
        "ss_cols": {"pid": "PID",
                    "status": "Usual_subsidiary_economic_activi"},
        "sex_member": None,
    },
    {
        "round": "2009-10", "year": 2009, "dir": "eus-2009-10",
        "zip": "Emp_Unemp_2009_2010_CSV.zip",
        "hh_member": "Block_3_Household characteristics.csv",
        "hh_key": "HHID", "hh_rel": "Religion",
        "ps_member": "Block_5_1_Usual principal activity particulars of household members.csv",
        "ps_cols": {"hh": "HHID", "pid": "PID", "age": "Age", "sex": None,
                    "status": "Usual_Principal_Activity_Status",
                    "weight": "WEIGHT", "sector": "Sector"},
        "ss_member": "Block_5_2_Usual subsidiary economic activity particulars of household members.csv",
        "ss_cols": {"pid": "PID",
                    "status": "Usual_Subsidiary_Activity_Status"},
        "sex_member": "Block_4_Demographic particulars of household members.csv",
        "sex_cols": {"pid": "PID", "sex": "Sex"},
    },
    {
        "round": "2011-12", "year": 2011, "dir": "eus-2011-12",
        "zip": "U_M_2011_2012_CSV.zip",
        "hh_member": "Block_3_Household characteristics.csv",
        # 2011-12's block 3 ships no HHID column; compose it the way block 4
        # spells it: FSU(5) + hamlet-group(1) + SSS(1) + sample-hh-no(2)
        "hh_key": None, "hh_rel": "Religion",
        "hh_key_compose": (("FSU_Serial_No", 5), ("Hamlet_Group_Sub_Block_No", 1),
                           ("Second_Stage_Stratum_No", 1), ("Sample_Hhld_No", 2)),
        "ps_member": "Block_5_1_Usual principal activity particulars of household members.csv",
        "ps_cols": {"hh": "HHID", "pid": None, "serial": "Person_Serial_No",
                    "age": "Age", "sex": None,
                    "status": "Usual_Principal_Activity_Status",
                    "weight": "Multiplier_comb", "sector": "Sector"},
        "ss_member": "Block_5_2_Usual subsidiary economic activity particulars of household members.csv",
        "ss_cols": {"serial": "Person_Serial_No", "hh": "HHID",
                    "status": "Usual_Subsidiary_Activity_Status"},
        "sex_member": "Block_4_Demographic particulars of household members.csv",
        "sex_cols": {"serial": "Person_Serial_No", "hh": "HHID", "sex": "Sex"},
    },
]

# ---- published anchors: per-1000, all-ages, usual status (ps+ss), all-India.
# NSS Report No. 568 Statements 3.12 (LFPR), 3.13 (WPR), 3.17 (UR), which
# tabulate the 61st, 66th and 68th rounds side by side; salaried (regular
# wage/salaried employees per 1000 usually employed) from Report 568
# Statement 3.16 (2011-12) and Report 552 Statement 3.16 (2009-10).
# Cell order: (rural male, rural female, rural person, urban male,
# urban female, urban person); salaried: (RM, RF, UM, UF).
PUB_LFPR = {
    ("2004-05", "muslim"):    (505, 185, 348, 546, 128, 345),
    ("2004-05", "hindu"):     (561, 350, 457, 576, 186, 390),
    ("2004-05", "christian"): (577, 385, 481, 535, 283, 409),
    ("2004-05", "sikh"):      (569, 369, 473, 575, 168, 383),
    ("2004-05", "all"):       (555, 333, 446, 570, 178, 382),
    ("2009-10", "muslim"):    (526, 146, 344, 536, 101, 327),
    ("2009-10", "hindu"):     (560, 279, 423, 563, 151, 368),
    ("2009-10", "christian"): (573, 346, 459, 540, 226, 382),
    ("2009-10", "sikh"):      (550, 268, 415, 568, 167, 380),
    ("2009-10", "all"):       (556, 265, 414, 559, 146, 362),
    ("2011-12", "muslim"):    (511, 159, 337, 553, 109, 342),
    ("2011-12", "hindu"):     (558, 264, 415, 565, 161, 372),
    ("2011-12", "christian"): (560, 304, 431, 565, 277, 417),
    ("2011-12", "sikh"):      (576, 260, 426, 568, 136, 363),
    ("2011-12", "all"):       (553, 253, 406, 563, 155, 367),
}
PUB_WPR = {
    ("2004-05", "muslim"):    (495, 178, 339, 526, 121, 331),
    ("2004-05", "hindu"):     (553, 344, 451, 555, 174, 373),
    ("2004-05", "christian"): (562, 359, 461, 505, 244, 375),
    ("2004-05", "sikh"):      (550, 355, 457, 555, 153, 365),
    ("2004-05", "all"):       (546, 327, 439, 549, 166, 365),
    ("2009-10", "muslim"):    (517, 143, 337, 523, 94, 317),
    ("2009-10", "hindu"):     (551, 275, 417, 547, 142, 355),
    ("2009-10", "christian"): (558, 326, 441, 528, 215, 371),
    ("2009-10", "sikh"):      (535, 263, 405, 536, 153, 356),
    ("2009-10", "all"):       (547, 261, 408, 543, 138, 350),
    ("2011-12", "muslim"):    (499, 153, 328, 532, 105, 328),
    ("2011-12", "hindu"):     (549, 261, 408, 550, 153, 359),
    ("2011-12", "christian"): (541, 284, 412, 540, 252, 392),
    ("2011-12", "sikh"):      (569, 257, 420, 548, 128, 349),
    ("2011-12", "all"):       (543, 248, 399, 546, 147, 355),
}
PUB_UR = {
    ("2004-05", "muslim"):    (20, 38, 23, 37, 55, 41),
    ("2004-05", "hindu"):     (14, 14, 15, 36, 70, 44),
    ("2004-05", "christian"): (26, 68, 44, 56, 141, 86),
    ("2004-05", "sikh"):      (33, 38, 35, 34, 90, 46),
    ("2004-05", "all"):       (16, 18, 16, 39, 67, 45),
    ("2009-10", "muslim"):    (19, 20, 19, 25, 68, 32),
    ("2009-10", "hindu"):     (15, 14, 15, 29, 58, 34),
    ("2009-10", "christian"): (26, 60, 39, 22, 46, 29),
    ("2009-10", "sikh"):      (27, 17, 24, 56, 83, 61),
    ("2009-10", "all"):       (16, 16, 16, 28, 57, 34),
    ("2011-12", "muslim"):    (22, 39, 26, 38, 44, 39),
    ("2011-12", "hindu"):     (17, 14, 16, 28, 52, 33),
    ("2011-12", "christian"): (34, 64, 45, 44, 88, 59),
    ("2011-12", "sikh"):      (13, 13, 13, 35, 55, 38),
    ("2011-12", "all"):       (17, 17, 17, 30, 52, 34),
}
PUB_SAL = {   # (RM, RF, UM, UF) per 1000 usually employed
    ("2009-10", "muslim"):    (79, 39, 298, 216),
    ("2009-10", "hindu"):     (83, 41, 441, 404),
    ("2009-10", "christian"): (168, 114, 450, 607),
    ("2009-10", "sikh"):      (123, 86, 352, 367),
    ("2009-10", "all"):       (85, 44, 419, 393),
    ("2011-12", "muslim"):    (104, 66, 288, 249),
    ("2011-12", "hindu"):     (98, 53, 463, 439),
    ("2011-12", "christian"): (161, 140, 494, 647),
    ("2011-12", "sikh"):      (157, 62, 418, 482),
    ("2011-12", "all"):       (100, 56, 434, 428),
}
CELLS = [("rural", "male"), ("rural", "female"), ("rural", "all"),
         ("urban", "male"), ("urban", "female"), ("urban", "all")]
SAL_CELLS = [("rural", "male"), ("rural", "female"),
             ("urban", "male"), ("urban", "female")]
TOL = {"lfpr": 1.2, "wpr": 1.2, "ur": 1.5, "sal": 2.0}


def norm(s):
    s = (s or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0") or "0"


def fnum(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def open_member(zf, basename):
    name = next(n for n in zf.namelist()
                if n.lower().endswith("/" + basename.lower())
                or n.lower() == basename.lower())
    return csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8",
                                           errors="replace"))


def process_round(cfg):
    rnd = cfg["round"]
    zf = zipfile.ZipFile(ARCHIVE / cfg["dir"] / cfg["zip"])

    # household block: HHID -> religion code
    hh_rel = {}
    for row in open_member(zf, cfg["hh_member"]):
        if cfg["hh_key"]:
            key = (row[cfg["hh_key"]] or "").strip()
        else:
            key = "".join((row[c] or "").strip().zfill(width)
                          for c, width in cfg["hh_key_compose"])
        hh_rel[key] = (row[cfg["hh_rel"]] or "").strip()
    print(f"  {rnd}: {len(hh_rel):,} households "
          f"(religion codes: {dict(Counter(v for v in hh_rel.values() if v).most_common(5))})")

    # subsidiary block: person key -> ss status
    ssc = cfg["ss_cols"]
    ss_status = {}
    for row in open_member(zf, cfg["ss_member"]):
        if "pid" in ssc:
            key = norm(row[ssc["pid"]])
        else:
            key = (row[ssc["hh"]] or "").strip() + "|" + norm(row[ssc["serial"]])
        ss_status[key] = norm(row[ssc["status"]])

    # sex lookup where block 5.1 lacks it
    sex_of = {}
    if cfg["sex_member"]:
        sc = cfg["sex_cols"]
        for row in open_member(zf, cfg["sex_member"]):
            if "pid" in sc:
                key = norm(row[sc["pid"]])
            else:
                key = (row[sc["hh"]] or "").strip() + "|" + norm(row[sc["serial"]])
            sex_of[key] = norm(row[sc["sex"]])

    # person pass: block 5.1
    pc = cfg["ps_cols"]
    acc15 = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])   # 15+: pop, emp, unemp, sal, n
    accAA = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])      # all ages: pop, emp, unemp, sal
    status_seen = Counter()
    unmatched_rel = unmatched_sex = 0
    nrows = 0
    for row in open_member(zf, cfg["ps_member"]):
        nrows += 1
        hh = (row[pc["hh"]] or "").strip()
        relcode = hh_rel.get(hh)
        if not relcode:
            unmatched_rel += 1
            continue
        if pc.get("pid"):
            pkey = norm(row[pc["pid"]])
        else:
            pkey = hh + "|" + norm(row[pc["serial"]])
        w = fnum(row[pc["weight"]])
        if w <= 0:
            continue
        ps = norm(row[pc["status"]])
        status_seen[ps] += 1
        ss = ss_status.get(pkey, "")
        emp = ps in EMPLOYED or ss in EMPLOYED
        unemp = (not emp) and ps == "81"
        sal = emp and ((ps if ps in EMPLOYED else ss) == "31")
        if pc.get("sex"):
            sx_code = norm(row[pc["sex"]])
        else:
            sx_code = sex_of.get(pkey, "")
            if not sx_code:
                unmatched_sex += 1
        religion = RMAP.get(relcode)
        res = {"1": "rural", "2": "urban"}.get(norm(row[pc["sector"]]))
        sx = {"1": "male", "2": "female"}.get(sx_code)
        age = fnum(row[pc["age"]], -1)
        for rl in ({religion, "all"} if religion else {"all"}):
            for rs in ({res, "all"} if res else {"all"}):
                for s2 in ({sx, "all"} if sx else {"all"}):
                    a = accAA[(rl, rs, s2)]
                    a[0] += w
                    a[1] += w * emp
                    a[2] += w * unemp
                    a[3] += w * sal
                    if age >= 15:
                        b = acc15[(rl, rs, s2)]
                        b[0] += w
                        b[1] += w * emp
                        b[2] += w * unemp
                        b[3] += w * sal
                        b[4] += 1
    print(f"  {rnd}: {nrows:,} person rows; principal-status codes: "
          f"{dict(sorted(status_seen.items(), key=lambda kv: -kv[1])[:10])}")
    if unmatched_rel or unmatched_sex:
        print(f"  WARN {rnd}: {unmatched_rel} rows without household religion, "
              f"{unmatched_sex} without sex")

    # gates: all-ages per-1000 vs the published statements
    fails = []
    for (key, pub) in ((PUB_LFPR, "lfpr"), (PUB_WPR, "wpr"), (PUB_UR, "ur")):
        for rel in GATE_RELIGIONS:
            want6 = key.get((rnd, rel))
            if not want6:
                continue
            for i, ((res, sx), want) in enumerate(zip(CELLS, want6)):
                wp, we, wu, _ws = accAA[(rel, res, sx)]
                if pub == "lfpr":
                    got = 1000.0 * (we + wu) / wp
                    tol = TOL["lfpr"]
                elif pub == "wpr":
                    got = 1000.0 * we / wp
                    tol = TOL["wpr"]
                else:
                    lf = we + wu
                    got = 1000.0 * wu / lf if lf else float("nan")
                    # unemployed share = difference of two independently
                    # rounded statements (+-0.75/1000 combined), amplified
                    # by the LF denominator (binds only for female cells)
                    tol = max(TOL["ur"], 750.0 / PUB_LFPR[(rnd, rel)][i])
                if abs(got - want) > tol:
                    fails.append(f"{rnd} {pub} {rel} {res}/{sx}: "
                                 f"computed {got:.1f} vs published {want}")
    for rel in GATE_RELIGIONS:
        want4 = PUB_SAL.get((rnd, rel))
        if not want4:
            continue
        for (res, sx), want in zip(SAL_CELLS, want4):
            wp, we, wu, ws = accAA[(rel, res, sx)]
            # Statement 3.16 distributes all-ages usually employed persons
            got = 1000.0 * ws / we if we else float("nan")
            if abs(got - want) > TOL["sal"]:
                fails.append(f"{rnd} salaried {rel} {res}/{sx}: "
                             f"computed {got:.1f} vs published {want}")
    return acc15, accAA, fails


def main():
    all_rows = []
    all_fails = []
    for cfg in ROUNDS:
        print(f"processing {cfg['round']} ...")
        acc15, accAA, fails = process_round(cfg)
        all_fails.extend(fails)
        for (rl, rs, s2), (wp, we, wu, ws, n) in sorted(acc15.items()):
            if rl not in RELIGIONS or wp <= 0:
                continue
            lf = we + wu
            all_rows.append({
                "round": cfg["round"], "year": cfg["year"], "religion": rl,
                "residence": rs, "sex": s2, "n_15plus": n,
                "lfpr": f"{100*lf/wp:.2f}", "wpr": f"{100*we/wp:.2f}",
                "ur": f"{100*wu/lf:.2f}" if lf > 0 else "",
                "salaried_share": f"{100*ws/we:.2f}" if we > 0 else "",
            })
    print("\n--- gates: all-ages per-1000 vs Reports 568/552 statements ---")
    if all_fails:
        for f in all_fails:
            print("  FAIL", f)
        sys.exit("VALIDATION FAILED - L2 not written")
    print(f"  all {3*5*6*3 + 2*5*4} gate cells within tolerance")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["round", "year", "religion", "residence",
                                          "sex", "n_15plus", "lfpr", "wpr", "ur",
                                          "salaried_share"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(all_rows)} rows)")
    print("\n--- Muslim 15+ national series (the card rows) ---")
    for r in all_rows:
        if r["religion"] == "muslim" and r["residence"] == "all" and r["sex"] == "all":
            print(f"  {r['round']}: LFPR {r['lfpr']}  WPR {r['wpr']}  UR {r['ur']}  "
                  f"salaried {r['salaried_share']}  (n={r['n_15plus']:,})")


if __name__ == "__main__":
    main()
