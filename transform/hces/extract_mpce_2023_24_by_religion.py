#!/usr/bin/env python3
"""Compute MPCE by religion from HCES 2023-24 unit-level microdata.

L1 source: HCES_Data_2023-24_Csv.zip from MoSPI's NADA API
(dataset idno DDI-IND-MOSPI-NSS-HCES23-24; see sources/hces-2023-24/). The 244 MB
zip is kept LOCAL (archive SHA256 + provenance only, not committed); re-fetch with
the API recipe in sources/hces-2023-24/PROVENANCE.md. Default path:
~/Desktop/hces-work/HCES_Data_2023-24_Csv.zip (override with argv[1]).

Method (NSS Survey Methodology & Estimation Procedure, section 3.5):
  MPCE_household = E_food/P + E_csq/P + E_durable/P, aggregated as the ratio
  estimator  MPCE = sum(w * TE) / sum(w * size)  by sector / religion, where
  TE = monthly consumption = (30-day items) + (365-day items)/12.

  - Consumption value = `Total_Consumption_Value` in the DETAIL levels L05/L06
    (food), L08, L09, L10 (consumables & services), L12, L13 (durables). NOT
    level 14 (= section subtotals / expenditure-only, undercounts ~half).
  - Reference periods (MMRP): 30-day as-is = food + L08 + L10 + L09 Section 9;
    365-day /12 = L09 Sections 10/11 (clothing/footwear/education/medical) + L12 +
    L13 (durables). L09 is the only mixed file; its section is set by item-code
    block (Section 9 = codes 440-479; Sections 10/11 = 400-439 and 480-899).
  - Weight = Multiplier (from L01); religion + household size from L03.

Validation: reproduces the published national MPCE (rural Rs 4,122 / urban
Rs 6,996, without free-item imputation) within ~2%, then extracts the religion
split. NSO's unit-data rider: religion is self-reported/unverified and the survey
is designed for MPCE with State/UT as the basic stratum, so the religion figures
are indicative and no sub-state estimate is made.

Run:  python transform/hces/extract_mpce_2023_24_by_religion.py [path-to-zip]
Prints the validation table + the MPCE-by-religion rows appended to
canonical/mpce.csv (year=2023, source_id=hces-2023-24).
"""
import csv
import io
import os
import sys
import zipfile
from collections import defaultdict

ZIP = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/hces-work/HCES_Data_2023-24_Csv.zip")

# Detail level -> (column name carrying the consumption value, reference period).
# L09 is handled specially (item-code block decides the period).
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
    g = level_glob.lower()   # L13's file is "Level - 13" (lowercase); match loosely
    name = next(n for n in zf.namelist()
                if g in n.lower() and n.endswith(".csv"))
    return io.TextIOWrapper(zf.open(name), encoding="utf-8", errors="replace")


def l09_is_30day(item_code):
    """Section 9 (misc goods/services/rent, 30-day) = item codes 440-479;
    everything else in L09 (400-439, 480-899) is Section 10/11 (365-day)."""
    try:
        it = int(item_code)
    except (TypeError, ValueError):
        return True
    return it < 400 or (440 <= it <= 479)


def main():
    e30 = defaultdict(float)
    e365 = defaultdict(float)
    with zipfile.ZipFile(ZIP) as zf:
        # consumption detail levels
        for glob, (col, period) in VALUE_COL.items():
            f = _open(zf, f"LEVEL - {glob} ")
            r = csv.DictReader(f)
            bucket = e30 if period == "30" else e365
            for row in r:
                key = "|".join(row[c] for c in KEYCOLS)
                try:
                    bucket[key] += float(row[col] or 0)
                except ValueError:
                    pass
        # L09 (mixed reference period, split by item-code block)
        f = _open(zf, "LEVEL - 09 ")
        r = csv.DictReader(f)
        for row in r:
            key = "|".join(row[c] for c in KEYCOLS)
            try:
                v = float(row["Value_Rs_9_1_to_11_4"] or 0)
            except ValueError:
                continue
            (e30 if l09_is_30day(row["Item_Code_9_1_to_11_4"]) else e365)[key] += v

        # household attributes: L01 (sector, weight), L03 (religion, size)
        sector, mult = {}, {}
        f = _open(zf, "LEVEL - 01")
        for row in csv.DictReader(f):
            key = "|".join(row[c] for c in KEYCOLS)
            sector[key] = row["Sector"]
            mult[key] = float(row["Multiplier"]) / 100.0   # Final weight = MLT/100
        relig, size = {}, {}
        f = _open(zf, "LEVEL - 03.csv")
        for row in csv.DictReader(f):
            key = "|".join(row[c] for c in KEYCOLS)
            relig[key] = row["Religion_of_HH_Head"]
            size[key] = float(row["HH_Size_FDQ"])

    rmap = {"1": "hindu", "2": "muslim"}
    households = [k for k in sector if k in relig and k in size]

    def mpce(keys):
        num = sum(mult[k] * (e30[k] + e365[k] / 12.0) for k in keys)
        den = sum(mult[k] * size[k] for k in keys)
        return num / den if den else float("nan")

    by_sector = lambda keys, s: [k for k in keys if sector[k] == s]
    print(f"households: {len(households):,}\n--- national validation ---")
    for s, lbl, pub in [("1", "Rural", 4122), ("2", "Urban", 6996)]:
        c = mpce(by_sector(households, s))
        print(f"  {lbl}: Rs {c:,.0f}  (published {pub:,}, ratio {c/pub:.3f})")

    print("--- MPCE by religion (Rs/month) ---")
    rows = []
    for rel in ("muslim", "hindu", "all"):
        keys = households if rel == "all" else [k for k in households
                                                if rmap.get(relig[k]) == rel]
        for res, s in (("all", None), ("urban", "2"), ("rural", "1")):
            kk = keys if s is None else by_sector(keys, s)
            v = mpce(kk)
            rows.append((rel, res, round(v, 1)))
            print(f"  {rel:7s} {res:5s}: Rs {v:,.1f}")
    return rows


if __name__ == "__main__":
    main()
