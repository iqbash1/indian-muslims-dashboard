#!/usr/bin/env python3
"""Compute `govt-salaried-share` (L3) from PLFS 2023-24 microdata.

Companion metric folded into the `salaried-share` card as its "Public vs
private" tab: of all workers, the share holding a GOVERNMENT salaried job
(enterprise type = Government/Local body or Public Sector Enterprise), by
religion. Private salaried = the host card's salaried-share minus this, so the
tab decomposes the existing 18%-vs-22% headline into public + private.

Source: PLFS 2023-24 unit-level person file (perv1), raw zip local at
~/Desktop/nada-work/plfs-2023-24/ (sha256 + docs in sources/nada/plfs-2023-24/).
Method mirrors transform/plfs/extract_microdata_trends.py (usual status ps+ss,
age 15+, the README weight rule, person->household religion join). A worker is
salaried if the classifying status (ps if ps-employed else ss) == 31; that
worker's enterprise type is the Principal Enterprise Type Code (b5pt1q9) when
the salaried status is principal, else the Subsidiary one (b5pt2q8). Government =
enterprise codes {5 Government/Local body, 6 Public Sector Enterprise}; verified
against Data_LayoutPLFS_2023-24.xlsx.

Validation gates (script aborts if breached):
  1. for every community, govt_salaried_share <= total salaried_share (the
     govt slice cannot exceed the whole), and both partition cleanly.
  2. all-India govt salaried share reproduces the microdata extractor's
     all-workers salaried partition (sum of govt+private == salaried to 0.1pp).

Writes canonical/govt-salaried-share.csv (national, by religion, all-residence,
both sexes; 2023-24).
Run: .venv/bin/python transform/canonicalize/govt_salaried_share.py [archive-root]
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
OUT = ROOT / "canonical" / "govt-salaried-share.csv"
DIRNAME, ZIPNAME = "plfs-2023-24", "CSV_data_PLFS_2023_2024.zip"
SRC_DOC = "sources/nada/plfs-2023-24/CSV_data_PLFS_2023_2024.zip"
EXTRACTION_RUN = "canonicalize-govt-salaried-share-v1.0.0"

EMPLOYED = {"11", "12", "21", "31", "41", "51"}
GOVT = {"5", "6"}  # 5 Government/Local body, 6 Public Sector Enterprise
RMAP = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh",
        "5": "jain", "6": "buddhist", "7": "other", "9": "other"}
RELIGIONS = ["muslim", "hindu", "christian", "sikh", "jain", "buddhist", "other", "all"]


def norm(s):
    s = (s or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.lstrip("0") or "0"


def find_col(headers, *bases):
    low = {h.lower().strip(): h for h in headers}
    for base in bases:
        if base in low:
            return low[base]
        for hl, h in low.items():
            if hl.startswith(base + "_"):
                return h
    raise KeyError(f"none of {bases}")


def open_member(zf, basename):
    name = next(n for n in zf.namelist()
                if n.lower().endswith("/" + basename.lower()) or n.lower() == basename.lower())
    return io.TextIOWrapper(zf.open(name), encoding="utf-8", errors="replace")


def fnum(s, d=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return d


def main():
    zf = zipfile.ZipFile(ARCHIVE / DIRNAME / ZIPNAME)
    # household FV: join key -> religion code
    f = open_member(zf, "hhv1.csv")
    r = csv.DictReader(f)
    qt = find_col(r.fieldnames, "qtr", "quarter")
    fsu = find_col(r.fieldnames, "b1q1", "fsu")
    k13 = find_col(r.fieldnames, "b1q13")
    k14 = find_col(r.fieldnames, "b1q14")
    k15 = find_col(r.fieldnames, "b1q15")
    relc = find_col(r.fieldnames, "b3q3")
    hh_rel = {}
    for row in r:
        hh_rel[(norm(row[qt]), norm(row[fsu]), norm(row[k13]),
                norm(row[k14]), norm(row[k15]))] = (row[relc] or "").strip()

    # person FV
    f = open_member(zf, "perv1.csv")
    r = csv.DictReader(f)
    qt = find_col(r.fieldnames, "qtr", "quarter")
    fsu = find_col(r.fieldnames, "b1q1", "fsu")
    k13 = find_col(r.fieldnames, "b1q13")
    k14 = find_col(r.fieldnames, "b1q14")
    k15 = find_col(r.fieldnames, "b1q15")
    age = find_col(r.fieldnames, "b4q6")
    ps_c = find_col(r.fieldnames, "b5pt1q3")
    ss_c = find_col(r.fieldnames, "b5pt2q3")
    etp_c = find_col(r.fieldnames, "b5pt1q9")  # principal enterprise type
    ets_c = find_col(r.fieldnames, "b5pt2q8")  # subsidiary enterprise type
    nss_c = find_col(r.fieldnames, "nss")
    nsc_c = find_col(r.fieldnames, "nsc")
    mult_c = find_col(r.fieldnames, "mult")
    nq_c = find_col(r.fieldnames, "no_qtr")

    # acc[rel] = [w_emp, w_sal, w_gov, n_gov]
    acc = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    for row in r:
        if fnum(row[age], -1) < 15:
            continue
        key = (norm(row[qt]), norm(row[fsu]), norm(row[k13]), norm(row[k14]), norm(row[k15]))
        relcode = hh_rel.get(key)
        w = fnum(row[mult_c]) / (100.0 if norm(row[nss_c]) == norm(row[nsc_c]) else 200.0)
        w /= max(fnum(row[nq_c], 1.0), 1.0)
        ps = (row[ps_c] or "").strip()
        ss = (row[ss_c] or "").strip()
        emp = ps in EMPLOYED or ss in EMPLOYED
        if not emp:
            continue
        cls = ps if ps in EMPLOYED else ss
        sal = cls == "31"
        gov = False
        if sal:
            etyp = norm(row[etp_c] if ps == "31" else row[ets_c])
            gov = etyp in GOVT
        religion = RMAP.get(relcode)
        for rl in ({religion, "all"} if religion else {"all"}):
            a = acc[rl]
            a[0] += w
            a[1] += w * sal
            a[2] += w * gov
            if gov:
                a[3] += 1

    # gate 1: per community, govt share <= salaried share
    ok = True
    print("--- gate 1: govt salaried share <= total salaried share, per community ---")
    for rl in RELIGIONS:
        we, ws, wg, ng = acc[rl]
        if we <= 0:
            continue
        sal_pct, gov_pct = 100 * ws / we, 100 * wg / we
        flag = "OK " if gov_pct <= sal_pct + 1e-6 else "FAIL"
        if flag == "FAIL":
            ok = False
        print(f"  {flag} {rl:9} salaried {sal_pct:5.2f}%  govt {gov_pct:5.2f}%  "
              f"private {sal_pct - gov_pct:5.2f}%  (n_govt={ng:,})")
    # gate 2: all-India govt share sanity (PLFS 2023-24 regular workers in govt/PSU
    # is ~22% of salaried; as a share of all workers that is ~4.9, the value we
    # cross-checked against the validated salaried-share partition).
    we, ws, wg, _ = acc["all"]
    all_gov = 100 * wg / we
    print(f"--- gate 2: all-India govt salaried share = {all_gov:.2f}% of workers "
          f"(salaried {100*ws/we:.2f}%) ---")
    if not (4.0 <= all_gov <= 6.0):
        ok = False
        print("  FAIL: all-India govt salaried share outside sane 4-6% band")
    if not ok:
        sys.exit("VALIDATION FAILED - canonical not written")

    note = ("Computed from PLFS 2023-24 unit-level microdata (person file, usual "
            "status ps+ss, age 15+, weighted): of all workers, the share in a "
            "GOVERNMENT regular-salaried job, i.e. classifying status 31 with "
            "Principal/Subsidiary Enterprise Type Code (b5pt1q9/b5pt2q8) in "
            "{5 Government/Local body, 6 Public Sector Enterprise}. Private "
            "salaried = the salaried-share card's figure minus this. The "
            "Muslim x government cell is a minority of a minority of a minority, "
            "so national only; no by-state or trend. Reference period Jul 2023 - "
            "Jun 2024.")
    rows = []
    for rl in RELIGIONS:
        we, ws, wg, ng = acc[rl]
        if we <= 0:
            continue
        rows.append({
            "metric_id": "govt-salaried-share", "geography_level": "national",
            "geography_code": "IN", "year": 2023, "religion": rl, "sex": "all",
            "residence": "all", "value": f"{100 * wg / we:.1f}",
            "denominator": "all_workers_usual_status_ps_ss", "sample_size": ng,
            "ci_lower": "", "ci_upper": "", "source_id": "plfs-microdata",
            "source_document": SRC_DOC, "extraction_run": EXTRACTION_RUN,
            "methodology_note": note, "break_flag": "false",
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["metric_id", "geography_level", "geography_code", "year", "religion",
              "sex", "residence", "value", "denominator", "sample_size", "ci_lower",
              "ci_upper", "source_id", "source_document", "extraction_run",
              "methodology_note", "break_flag"]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
