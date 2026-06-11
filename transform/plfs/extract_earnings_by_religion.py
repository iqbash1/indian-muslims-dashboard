#!/usr/bin/env python3
"""Extract average monthly earnings of regular wage/salaried employees (15+) by religion (L2).

Source: 7 rounds of PLFS unit-level data (July-June, 2017-18 .. 2023-24) pulled from
MoSPI's NADA API and archived locally at ~/Desktop/nada-work/plfs-<round>/ (sha256 +
provenance in sources/nada/). Column map + per-round gotchas: nada/plfs-layout-map.md
(see its "Earnings columns" section for the work behind this script).

Earnings concept (identical in all 7 rounds):
  Block 6 of the schedule ("current weekly activity particulars"), item 9: "for 31, 71
  or 72 in item 5 [current weekly status], earnings (received/receivable) during the
  preceding calendar month for regular salaried/wage activity (Rs.)". In the shipped
  CSVs this is column b6q9_per_fv (2017-20) / b6q9_perv1 (2020-24); CWS status is
  b6q5_per_fv / b6q5_perv1. (Item 10 = self-employment earnings, a different concept;
  the 2017-21 layout xlsx mislabels it "Earnings For Regular Salarid/Wage Activity" -
  empirically it is populated only for CWS 11/12/61/62, i.e. the self-employed.)
  NOTE: exact column-name match is required here - the day-wise casual-wage columns
  (b6q9_Act1_3pt7 etc.) share the b6q9 prefix and would be caught by a loose lookup.

Estimator (replicates the published annual by-occupation earnings table - Table 55 in
the 2021-22 report, Table 33 in 2022-23, Tables 50/33 in 2023-24):
  - population: persons whose current weekly status is 31, 71 or 72 (regular salaried/
    wage employee in CWS, including those who had such a job but did not work that
    week) AND who reported positive earnings in item 9 ("* reported earnings" in the
    published tables; zero/not-reported are excluded, as the reports state for the
    companion self-employment table)
  - first-visit person file only, all four quarters combined; weight
    w = (MULT/100 if NSS == NSC else MULT/200) / NO_QTR  (the README rule, identical
    in all 7 rounds; MULT carries 2 implied decimals)
  - average = sum(w * earnings) / sum(w); no age filter in the published tables
    (validated by exact sample-count match), 15+ applied to the L2 rows only
  - religion lives only in the household first-visit file; person->household join on
    (quarter, FSU, b1q13, b1q14, b1q15) with keys normalised as strings
  - 2020-21 only: drop temporary visitors (person serial b4q1 >= 81)
  The published QUARTERLY earnings statements (e.g. Statement 10, 2023-24) instead mix
  first-visit + revisit schedules in urban areas, so their mean-of-quarters differs
  slightly from the first-visit annual figure replicated here (2023-24 person: 20,702
  vs 21,047). This script follows the annual first-visit definition throughout.

Validation gates (script fails loudly and writes nothing if breached):
  1. structural, every round: item-9 earnings must be reported ONLY by persons with
     CWS in {31, 71, 72}, and >= 95% of that group must report earnings
  2. published, 2021-22 / 2022-23 / 2023-24 (the annual reports archived in
     sources/plfs/annual/): computed all-ages average earnings must match the
     "all occupations" column of the published table within 1.5% for all 9 cells
     (rural/urban/rural+urban x male/female/person), and the unweighted reporter
     count must match the published sample count within 0.5%
  The 2017-18 .. 2020-21 annual report PDFs are not archived in sources/, so those
  rounds carry gate 1 only; the column names, join, weights and code lists are
  byte-identical to the validated rounds (see nada/plfs-layout-map.md).

Writes extracted/plfs/plfs-earnings-2017-24-by-religion.csv:
  round,year,religion,residence,sex,n_workers,avg_monthly_earnings_rs
  (religion in {muslim,hindu,christian,sikh,all}; n_workers = unweighted count of
  15+ reporters in the cell; earnings nominal Rs, weighted mean rounded to int)

Run:  .venv/bin/python transform/plfs/extract_earnings_by_religion.py [archive-root]
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
OUT = ROOT / "extracted" / "plfs" / "plfs-earnings-2017-24-by-religion.csv"

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

# published all-ages annual (first-visit, four quarters combined) average monthly
# earnings of regular wage/salaried employees in CWS, "all occupations" column,
# with the published sample count of employees who reported earnings:
#   (residence, sex) -> (avg Rs, sample n)
# 2021-22: annual report Table 55 (pp. 588-596 of the PDF, A-462..A-470)
# 2022-23: annual report Table 33 (pp. 268-270 of the PDF, A-178..A-180)
# 2023-24: annual report Tables 50 + 33 (pp. 403-405 of the PDF, A-340..A-342;
#          the printed page footers say "PLFS, 2022-23" - a copy-paste slip in the
#          published PDF; the values differ from the 2022-23 report's own table)
PUBLISHED = {
    "2021-22": {
        ("rural", "male"): (16353, 11372), ("rural", "female"): (10638, 3255),
        ("rural", "all"): (15190, 14627), ("urban", "male"): (22936, 21446),
        ("urban", "female"): (18219, 6991), ("urban", "all"): (21784, 28437),
        ("all", "male"): (20016, 32818), ("all", "female"): (15289, 10246),
        ("all", "all"): (18945, 43064),
    },
    "2022-23": {
        ("rural", "male"): (16957, 11676), ("rural", "female"): (11829, 3600),
        ("rural", "all"): (15807, 15276), ("urban", "male"): (24191, 21994),
        ("urban", "female"): (18941, 7603), ("urban", "all"): (22861, 29597),
        ("all", "male"): (20927, 33670), ("all", "female"): (16009, 11203),
        ("all", "all"): (19744, 44873),
    },
    "2023-24": {
        ("rural", "male"): (18042, 11968), ("rural", "female"): (11907, 3897),
        ("rural", "all"): (16635, 15865), ("urban", "male"): (26138, 22233),
        ("urban", "female"): (19780, 8196), ("urban", "all"): (24427, 30429),
        ("all", "male"): (22520, 34201), ("all", "female"): (16671, 12093),
        ("all", "all"): (21047, 46294),
    },
}

SALARIED_CWS = {"31", "71", "72"}   # 71/72: had the job, did not work that week
RMAP = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh"}
RELIGIONS = ["muslim", "hindu", "christian", "sikh", "all"]
RESIDENCES = ["all", "rural", "urban"]
SEXES = ["all", "male", "female"]


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


def exact_col(headers, base):
    """Exact-name lookup for block-6 items: only base, base_per_fv or base_perv1.
    A prefix match would collide with the day-wise b6q9_Act1_3pt7-style columns."""
    low = {h.lower().strip(): h for h in headers}
    for cand in (base, base + "_per_fv", base + "_perv1"):
        if cand in low:
            return low[cand]
    raise KeyError(f"no exact {base}(_per_fv|_perv1) in {sorted(low)[:40]}...")


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

    # person FV: salaried-in-CWS reporters of monthly earnings
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
    cws_c = exact_col(r.fieldnames, "b6q5")    # current weekly status
    earn_c = exact_col(r.fieldnames, "b6q9")   # preceding-calendar-month earnings
    nss_c = find_col(r.fieldnames, "nss")
    nsc_c = find_col(r.fieldnames, "nsc")
    mult_c = find_col(r.fieldnames, "mult")
    nq_c = find_col(r.fieldnames, "no_qtr")
    serial_c = find_col(r.fieldnames, "b4q1") if rnd == "2020-21" else None

    # acc[(religion, residence, sex, is15plus)] = [sum_w, sum_w*earn, n]
    acc = defaultdict(lambda: [0.0, 0.0, 0])
    unmatched = 0
    n_salaried = n_reporters = leak = under15 = 0
    max_earn = 0.0
    for row in r:
        if serial_c and fnum(row[serial_c], 0) >= 81:   # 2020-21 temporary visitors
            continue
        cws = norm(row[cws_c])
        earn = fnum(row[earn_c], -1.0)
        if cws not in SALARIED_CWS:
            if earn > 0:
                leak += 1
            continue
        n_salaried += 1
        if earn <= 0:                                   # zero / not reported
            continue
        key = (norm(row[qtr]), norm(row[fsu]), norm(row[k13]),
               norm(row[k14]), norm(row[k15]))
        relcode = hh_rel.get(key)
        if relcode is None:
            unmatched += 1
            continue
        n_reporters += 1
        max_earn = max(max_earn, earn)
        mult = fnum(row[mult_c])
        w = mult / (100.0 if norm(row[nss_c]) == norm(row[nsc_c]) else 200.0)
        w /= max(fnum(row[nq_c], 1.0), 1.0)
        is15 = fnum(row[age_c], -1) >= 15
        if not is15:
            under15 += 1
        religion = RMAP.get(norm(relcode))
        res = {"1": "rural", "2": "urban"}.get(norm(row[sec]))
        sx = {"1": "male", "2": "female"}.get(norm(row[sex_c]))
        for rl in ({religion, "all"} if religion else {"all"}):
            for rs in {res, "all"} if res else {"all"}:
                for s2 in {sx, "all"} if sx else {"all"}:
                    a = acc[(rl, rs, s2, is15)]
                    a[0] += w
                    a[1] += w * earn
                    a[2] += 1
    if unmatched:
        print(f"  WARN {rnd}: {unmatched} salaried reporters had no household match")
    stats = dict(n_salaried=n_salaried, n_reporters=n_reporters, leak=leak,
                 under15=under15, max_earn=max_earn)
    print(f"  {rnd}: salaried-in-CWS {n_salaried:,}; reported earnings "
          f"{n_reporters:,} ({100*n_reporters/n_salaried:.2f}%); "
          f"under-15 reporters {under15}; max Rs {max_earn:,.0f}")
    return acc, stats


def gate1_structural(rnd, stats):
    ok = True
    if stats["leak"]:
        print(f"  FAIL gate1 {rnd}: {stats['leak']} records report item-9 earnings "
              f"with CWS outside {sorted(SALARIED_CWS)}")
        ok = False
    if stats["n_reporters"] < 0.95 * stats["n_salaried"]:
        print(f"  FAIL gate1 {rnd}: only {stats['n_reporters']}/{stats['n_salaried']} "
              "salaried persons report earnings (< 95%)")
        ok = False
    return ok


def gate2_published(rnd, acc):
    """All-ages computed vs published table; avg within 1.5%, n within 0.5%."""
    ok = True
    print(f"  --- gate 2 ({rnd}): computed vs published annual table ---")
    print(f"  {'cell':18s} {'avg':>8s} {'pub':>8s} {'diff%':>7s} {'n':>7s} {'pub n':>7s}")
    for (res, sx), (pavg, pn) in sorted(PUBLISHED[rnd].items()):
        w = we = n = 0.0
        for is15 in (True, False):
            a = acc.get(("all", res, sx, is15))
            if a:
                w += a[0]; we += a[1]; n += a[2]
        avg = we / w
        d = 100.0 * (avg - pavg) / pavg
        nd = 100.0 * (n - pn) / pn
        flag = "OK " if abs(d) <= 1.5 and abs(nd) <= 0.5 else "FAIL"
        if flag == "FAIL":
            ok = False
        print(f"  {flag} {res+' '+sx:14s} {avg:8,.0f} {pavg:8,} {d:+6.2f}% "
              f"{n:7,.0f} {pn:7,}")
    return ok


def main():
    per_round = {}
    print("pass 1: extraction + structural gate")
    g_ok = True
    for rnd, dirname, zipname, per_base, hh_base in ROUNDS:
        print(f"processing {rnd} ...")
        acc, stats = process_round(rnd, dirname, zipname, per_base, hh_base)
        per_round[rnd] = acc
        g_ok &= gate1_structural(rnd, stats)

    print("pass 2: published-table gate (rounds with archived annual reports)")
    for rnd in PUBLISHED:
        g_ok &= gate2_published(rnd, per_round[rnd])
    if not g_ok:
        sys.exit("VALIDATION FAILED - L2 not written")

    rows = []
    for rnd, _, _, _, _ in ROUNDS:
        acc = per_round[rnd]
        for rl in RELIGIONS:
            for rs in RESIDENCES:
                for sx in SEXES:
                    a = acc.get((rl, rs, sx, True))   # 15+ only
                    if not a or a[0] <= 0:
                        continue
                    rows.append({
                        "round": rnd, "year": int(rnd[:4]), "religion": rl,
                        "residence": rs, "sex": sx, "n_workers": a[2],
                        "avg_monthly_earnings_rs": round(a[1] / a[0]),
                    })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["round", "year", "religion", "residence",
                                          "sex", "n_workers",
                                          "avg_monthly_earnings_rs"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} rows)")
    print("--- 15+ all-India person average monthly earnings (Rs) ---")
    print(f"{'round':8s} {'muslim':>8s} {'hindu':>8s} {'christian':>9s} "
          f"{'sikh':>8s} {'all':>8s}")
    for rnd, _, _, _, _ in ROUNDS:
        vals = {}
        for rl in RELIGIONS:
            r = next((x for x in rows if x["round"] == rnd and x["religion"] == rl
                      and x["residence"] == "all" and x["sex"] == "all"), None)
            vals[rl] = f"{r['avg_monthly_earnings_rs']:,}" if r else "-"
        print(f"{rnd:8s} {vals['muslim']:>8s} {vals['hindu']:>8s} "
              f"{vals['christian']:>9s} {vals['sikh']:>8s} {vals['all']:>8s}")


if __name__ == "__main__":
    main()
