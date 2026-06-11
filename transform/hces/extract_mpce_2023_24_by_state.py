#!/usr/bin/env python3
"""Extract MPCE by religion x state x residence from HCES 2023-24 microdata (L2).

Same validated machinery as extract_mpce_2023_24_by_religion.py (see its docstring
for the method + reference-period rules), extended to group by State: the State
code is already part of the household key (KEYCOLS index 2), so the state cut
needs no extra columns. Writes the L2 file

    extracted/hces/hces-2023-24-mpce-by-religion.csv
    (scope, state_code, religion, residence, mpce_rs, n_households)

covering national + per-state x {muslim, hindu, all} x {all, urban, rural}, with
unweighted household counts so the canonicaliser can apply the NSS small-sample
rule (suppress cells under 30 sampled households). State codes are the NSS/Census
2-digit codes (01 J&K ... 36 Telangana, 37 Ladakh); the run prints weighted
population shares per state as an empirical check of the code mapping.

Run:  .venv/bin/python transform/hces/extract_mpce_2023_24_by_state.py [path-to-zip]
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
OUT = ROOT / "extracted" / "hces" / "hces-2023-24-mpce-by-religion.csv"

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

    rmap = {"1": "hindu", "2": "muslim"}
    hh = [k for k in mult if k in relig and k in size]
    sector = lambda k: k.split("|")[1]          # 1=rural, 2=urban (KEYCOLS idx 1)
    state = lambda k: k.split("|")[2].zfill(2)  # NSS/Census 2-digit code (idx 2)

    def mpce(keys):
        num = sum(mult[k] * (e30[k] + e365[k] / 12.0) for k in keys)
        den = sum(mult[k] * size[k] for k in keys)
        return num / den if den else float("nan")

    print(f"households: {len(hh):,}\n--- national validation (must match prior run) ---")
    for s, lbl, pub in [("1", "Rural", 4122), ("2", "Urban", 6996)]:
        c = mpce([k for k in hh if sector(k) == s])
        print(f"  {lbl}: Rs {c:,.0f}  (published {pub:,}, ratio {c/pub:.3f})")

    print("--- state code check: weighted person-share per state (top 8) ---")
    wpop = defaultdict(float)
    for k in hh:
        wpop[state(k)] += mult[k] * size[k]
    tot = sum(wpop.values())
    for st, w in sorted(wpop.items(), key=lambda x: -x[1])[:8]:
        print(f"  state {st}: {100*w/tot:.1f}%")

    # L2 rows: national + per-state, x religion x residence, with unweighted counts.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    states = sorted({state(k) for k in hh})
    for scope, st in [("national", "")] + [("state", s) for s in states]:
        base = hh if scope == "national" else [k for k in hh if state(k) == st]
        for rel in ("muslim", "hindu", "all"):
            keys = base if rel == "all" else [k for k in base if rmap.get(relig[k]) == rel]
            for res, s in (("all", None), ("urban", "2"), ("rural", "1")):
                kk = keys if s is None else [k for k in keys if sector(k) == s]
                if not kk:
                    continue
                rows.append({"scope": scope, "state_code": st, "religion": rel,
                             "residence": res, "mpce_rs": f"{mpce(kk):.2f}",
                             "n_households": len(kk)})
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scope", "state_code", "religion",
                                          "residence", "mpce_rs", "n_households"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} rows, {len(states)} states)")


if __name__ == "__main__":
    main()
