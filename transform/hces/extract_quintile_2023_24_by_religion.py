#!/usr/bin/env python3
"""Consumption-quintile shares by religion from HCES 2023-24 microdata (L2).

Metric: of all persons in a community, what share lives in households whose
MPCE falls in each FIFTH (quintile) of the national person-weighted MPCE
distribution. By construction every all-India share is 20.0 (the built-in
validation gate). The headline finding (2023-24): Muslims sit at par in the
bottom quintile (20.5 vs 20.0) but only 13.7% reach the TOP quintile - the
distribution is compressed below the top, not crowded at the bottom. Same
validated MPCE machinery as extract_mpce_2023_24_by_state.py (NSS estimation
procedure 3.5), one extra step: person-weighted national quintile cuts, then
per-religion shares against those cuts.

Writes extracted/hces/hces-2023-24-quintile-by-religion.csv:
  religion,residence,q1_share..q5_share,n_households
(residence rows are computed against the SAME national cuts, so they read as
"share of that community's rural population in the national Q1..Q5", not
sector-specific quintiles.)

Run:  .venv/bin/python transform/hces/extract_quintile_2023_24_by_religion.py [zip]
"""
import csv
import io
import os
import pathlib
import sys
import zipfile
from collections import defaultdict

ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/hces-work/HCES_Data_2023-24_Csv.zip")
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "extracted" / "hces" / "hces-2023-24-quintile-by-religion.csv"

VALUE_COL = {
    "05": ("Total_Consumption_Value", "30"),
    "06": ("Total_Consumption_Value", "30"),
    "08": ("Total_consumption_value_rs", "30"),
    "10": ("Total_Consumption_Value_12_serie", "30"),
    "12": ("VALUE", "365"),
    "13": ("TOTAL_EXPENDITURE", "365"),
}
KEYCOLS = ["FSU_Serial_No", "Sector", "State",
           "Second_Stage_Stratum_No", "Sample_Household_No"]


def _open(zf, level_glob):
    g = level_glob.lower()
    name = next(n for n in zf.namelist()
                if g in n.lower() and n.endswith(".csv"))
    return io.TextIOWrapper(zf.open(name), encoding="utf-8", errors="replace")


def l09_is_30day(item_code):
    try:
        it = int(item_code)
    except (TypeError, ValueError):
        return True
    return it < 400 or (440 <= it <= 479)


def main():
    e30 = defaultdict(float)
    e365 = defaultdict(float)
    with zipfile.ZipFile(ZIP) as zf:
        for glob, (col, period) in VALUE_COL.items():
            r = csv.DictReader(_open(zf, f"LEVEL - {glob} "))
            bucket = e30 if period == "30" else e365
            for row in r:
                key = "|".join(row[c] for c in KEYCOLS)
                try:
                    bucket[key] += float(row[col] or 0)
                except ValueError:
                    pass
        r = csv.DictReader(_open(zf, "LEVEL - 09 "))
        for row in r:
            key = "|".join(row[c] for c in KEYCOLS)
            try:
                v = float(row["Value_Rs_9_1_to_11_4"] or 0)
            except ValueError:
                continue
            (e30 if l09_is_30day(row["Item_Code_9_1_to_11_4"]) else e365)[key] += v

        mult = {}
        for row in csv.DictReader(_open(zf, "LEVEL - 01")):
            key = "|".join(row[c] for c in KEYCOLS)
            mult[key] = float(row["Multiplier"]) / 100.0
        relig, size = {}, {}
        for row in csv.DictReader(_open(zf, "LEVEL - 03.csv")):
            key = "|".join(row[c] for c in KEYCOLS)
            relig[key] = row["Religion_of_HH_Head"]
            size[key] = float(row["HH_Size_FDQ"])

    rmap = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh"}
    hh = [k for k in mult if k in relig and k in size]
    sector = lambda k: k.split("|")[1]

    # person-weighted national MPCE distribution -> quintile cuts
    recs = []   # (mpce, person_weight, religion, sector)
    for k in hh:
        m = (e30[k] + e365[k] / 12.0) / size[k] if size[k] else 0.0
        recs.append((m, mult[k] * size[k], rmap.get(relig[k], "other"), sector(k)))
    recs.sort(key=lambda t: t[0])
    wtot = sum(w for _, w, _, _ in recs)
    cuts = []
    acc = 0.0
    targets = [wtot * q / 5.0 for q in (1, 2, 3, 4)]
    ti = 0
    for m, w, _, _ in recs:
        acc += w
        while ti < 4 and acc >= targets[ti]:
            cuts.append(m)
            ti += 1
    p20 = cuts[0]
    print(f"households: {len(hh):,}  person-weighted total: {wtot:,.0f}")
    print(f"national MPCE quintile cuts (Rs): {[f'{c:,.0f}' for c in cuts]}")

    bounds = [-1.0] + cuts + [float("inf")]

    def qshares(filt):
        """[share in Q1..Q5 (%)] of person-weighted population matching filter,
        against the NATIONAL quintile cuts."""
        wq = [0.0] * 5
        for m, w, rl, sec in recs:
            if filt(rl, sec):
                for q in range(5):
                    if bounds[q] < m <= bounds[q + 1]:
                        wq[q] += w
                        break
        tot = sum(wq)
        return [100.0 * x / tot if tot else float("nan") for x in wq]

    print("--- gate: all-India shares must each be 20.0 ---")
    allq = qshares(lambda rl, sec: True)
    print("  all:", " ".join(f"{v:.2f}" for v in allq))
    if any(abs(v - 20.0) > 0.05 for v in allq):
        sys.exit("GATE FAILED")

    nhh = defaultdict(int)
    for k in hh:
        for rl2 in (rmap.get(relig[k], "other"), "all"):
            nhh[(rl2, "all")] += 1
            nhh[(rl2, {"1": "rural", "2": "urban"}[sector(k)])] += 1
    rows = []
    print("--- quintile shares by religion (Q1 poorest .. Q5 richest, % of community) ---")
    for rl in ("muslim", "hindu", "christian", "sikh", "all"):
        for res, sec in (("all", None), ("rural", "1"), ("urban", "2")):
            qs = qshares(lambda r, s, rl=rl, sec=sec:
                         (rl == "all" or r == rl) and (sec is None or s == sec))
            rows.append({"religion": rl, "residence": res,
                         **{f"q{i+1}_share": f"{qs[i]:.1f}" for i in range(5)},
                         "n_households": nhh[(rl, res)]})
            if res == "all":
                print(f"  {rl:9s}: " + " ".join(f"{v:5.1f}" for v in qs)
                      + f"  (n={nhh[(rl, 'all')]:,})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["religion", "residence",
                                          "q1_share", "q2_share", "q3_share",
                                          "q4_share", "q5_share", "n_households"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
