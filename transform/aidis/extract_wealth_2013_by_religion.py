#!/usr/bin/env python3
"""Compute household wealth and debt by religion from AIDIS 2013 microdata (L2).

L1 source: CSV_NSS_70th_Debt_&_Investment_Visit1_Jan_Dec_2013.zip from MoSPI's NADA
API (dataset idno DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec20131 = NSS 70th round,
Schedule 18.2 All-India Debt & Investment Survey, Visit 1, Jan-Jul 2013 fieldwork,
central sample). The 39 MB zip stays LOCAL at ~/Desktop/nada-work/aidis-2013-v1/
(sha256 in that dir's MANIFEST.json; re-fetch with nada/bank.py). Override the
archive dir with argv[1]. File/block/column map + gotchas: nada/aidis-layout-map.md.

Reference date: all asset and debt stocks are "as on 30.06.2012" (the 70th round
reference date), reported directly by the informant (KI(70/18.2) para 2.3.1).

Method (one record set per household, Visit 1 only, all 110,800 households):
  - Universe + religion + weight: Block 3 file (level 02), one row per household;
    religion = b3q6 (1 Hinduism, 2 Islam, 3 Christianity, 4 Sikhism, 5 Jainism,
    6 Buddhism, 7 Zoroastrianism, 9 others); sector 1 rural / 2 urban.
  - Weight = MLT/100 if NSS == NSC else MLT/200 (the CSVs ship both as Weight_SS /
    Weight_SC; the halving pools the two independent sub-samples, per Appendix C of
    KI(70/18.2)). Gives 156.1M rural + 83.7M urban households, plausible for 2013.
  - ASSETS per household = sum over the 10 asset blocks of the block's TOTAL row
    (falling back to the sum of item rows, minus subtotal serials, for the <20
    households per block whose total row is missing):
      block 5.1 land (srl 99) + 5.2 land (99) + 6 buildings (11) + 7 livestock (22,
      subtotal 17 skipped in fallback) + 8 transport (8) + 9 agri machinery (8) +
      10 non-farm business equipment (15, subtotal 12 skipped; NOTE the value
      column is EMPTY file-wide in the CSV conversion, see gotcha below) +
      11 shares & debentures at the derived 30.06.2012 value b11_q6 (srl 5) +
      12 financial assets total srl 11 = items 1-7 & 10 ONLY (srl 8 is a policy
      COUNT, 9 is sum assured, 12 is bullion & ornaments; all three excluded from
      the published assets concept) + 13 amount receivable (srl 7).
    This reproduces the published Average Value of Assets (AVA) definition, which
    EXCLUDES bullion/ornaments and household durables (KI Statement 3.3 footnote).
  - DEBT per household = Block 14 (cash loans) item rows with b14_q4 (period) == 1
    ("loan remaining unpaid on 30.6.12"), summing b14_q17 = amount outstanding
    incl. interest as on 30.06.2012 (only filled for period-1 loans; verified 0 on
    every period-2 row). Kind loans (block 15) are outstanding as on the DATE OF
    SURVEY only, hence not part of the published 30.06.2012 AOD and excluded.
  - IOI = share of households with debt > 0; institutional share = q17 share of
    credit-agency codes {01-08, 10, 11} (Govt, co-op, banks, insurance, PF,
    financial corps/companies, SHGs, other institutional); non-institutional =
    {09, 12-17} (landlord, moneylenders, input suppliers, relatives, etc.).

Validation gates (script exits without writing the L2 if breached; published
figures verified directly from NSS KI(70/18.2), 19 Dec 2014, mospi.gov.in):
  1. unweighted sample = 62,135 rural + 48,665 urban households (KI para 2.2.3.2)
  2. all-India AVA  rural 1,006,985 / urban 2,285,135 Rs  (Statement 3.2) +-3%
  3. all-India AOD  rural 32,522 / urban 84,625 Rs        (Statement 3.4) +-3%
  4. all-India IOI  rural 31.44% / urban 22.37%           (Statement 3.4) +-3% rel.
  Secondary (printed, +-2pp tolerance): institutional share of outstanding debt
  rural 56.0% / urban 84.5% (Table 8: 560 / 845 per Rs 1000).

Known data gotcha (documented, not fixable from the CSV): the block 10 value
column (b10_q3, non-farm business equipment) is empty for all 85,330 rows of the
CSV conversion, so computed AVA runs ~0.25% (rural) / ~0.76% (urban) below the
published level (those are the published block-10 shares of AVA, Statement 3.3).

Writes extracted/aidis/aidis-2013-wealth-by-religion.csv:
  religion,residence,avg_assets_rs,avg_debt_rs,avg_net_worth_rs,ioi_pct,
  institutional_debt_share_pct,n_households
(religions muslim/hindu/christian/sikh/all x residence all/rural/urban; assets,
debt, net worth = weighted means per household in Rs as on 30.06.2012.)

Run:  .venv/bin/python transform/aidis/extract_wealth_2013_by_religion.py [archive-dir]
"""
import csv
import io
import os
import pathlib
import sys
import zipfile
from collections import defaultdict

ARCHIVE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                       else os.path.expanduser("~/Desktop/nada-work/aidis-2013-v1"))
ZIPNAME = "CSV_NSS_70th_Debt_&_Investment_Visit1_Jan_Dec_2013.zip"
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "extracted" / "aidis" / "aidis-2013-wealth-by-religion.csv"

# published all-India figures, NSS KI(70/18.2) (verified from the PDF itself)
PUB = {
    "n":   {"rural": 62135, "urban": 48665},          # para 2.2.3.2 (Visit 1)
    "ava": {"rural": 1006985, "urban": 2285135},      # Statement 3.2
    "aod": {"rural": 32522, "urban": 84625},          # Statement 3.4
    "ioi": {"rural": 31.44, "urban": 22.37},          # Statement 3.4
    "inst": {"rural": 56.0, "urban": 84.5},           # Table 8 (per-1000 -> %)
}

# asset blocks: (zip-member prefix, srl col, value col, total srl, subtotal srls)
ASSET_BLOCKS = [
    ("Visit 1_Block 5pt1", "b5_1_1", "b5_1_6", "99", set(), "land (rural-type)"),
    ("Visit 1_Block 5pt2", "b5_2_1", "b5_2_6", "99", set(), "land (urban-type)"),
    ("Visit 1_Block 6_",   "b6_q3",  "b6_q6",  "11", set(), "buildings"),
    ("Visit 1_Block 7_",   "b7_q2",  "b7_q5",  "22", {"17"}, "livestock"),
    ("Visit 1_Block 8_",   "b8_q2",  "b8_q5",  "8",  set(), "transport equipment"),
    ("Visit 1_Block 9_",   "b9_q2",  "b9_q4",  "8",  set(), "agri machinery"),
    ("Visit 1_Block 10_",  "b10_q2", "b10_q3", "15", {"12"}, "non-farm equipment"),
    ("Visit 1_Block 11_",  "b11_q1", "b11_q6", "5",  set(), "shares & debentures"),
    ("Visit 1_Block 13.csv", "b13_q2", "b13_q4", "7", set(), "amount receivable"),
]
# block 12 handled separately (count/sum-assured/bullion serials to exclude)
B12_VALUE_ITEMS = {"1", "2", "3", "4", "5", "6", "7", "10"}

INSTITUTIONAL = {"1", "2", "3", "4", "5", "6", "7", "8", "10", "11"}
RMAP = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh"}
RELIGIONS = ["muslim", "hindu", "christian", "sikh", "all"]
RESIDENCES = ["all", "rural", "urban"]


def fnum(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def norm_srl(s):
    return (s or "").strip().lstrip("0") or "0"


def open_member(zf, prefix):
    name = next(n for n in zf.namelist()
                if n.split("/")[-1].startswith(prefix) and n.endswith(".csv"))
    return csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8",
                                           errors="replace"))


def block_totals(zf, prefix, srl_col, val_col, total_srl, subtotals):
    """Per-household block value: TOTAL row if present, else item-row sum
    (excluding subtotal serials and serials above the total serial = junk)."""
    tot, items = {}, defaultdict(float)
    max_item = int(total_srl) if total_srl != "99" else 98
    for row in open_member(zf, prefix):
        s = norm_srl(row[srl_col])
        v = fnum(row[val_col])
        h = row["HHID"]
        if s == total_srl:
            tot[h] = tot.get(h, 0.0) + v
        elif s not in subtotals:
            try:
                if int(s) <= max_item:
                    items[h] += v
            except ValueError:
                pass
    fallback = 0
    for h, v in items.items():
        if h not in tot:
            tot[h] = v
            fallback += 1
    return tot, fallback


def main():
    zf = zipfile.ZipFile(ARCHIVE / ZIPNAME)

    # ---- universe: block 3 (one row per canvassed household)
    sector, religion, weight = {}, {}, {}
    for row in open_member(zf, "Visit 1_Block 3"):
        h = row["HHID"]
        sector[h] = {"1": "rural", "2": "urban"}.get(row["Sector"].strip())
        religion[h] = RMAP.get((row["b3q6"] or "").strip())
        mlt = fnum(row["MLT"])
        weight[h] = mlt / (100.0 if row["NSS"].strip() == row["NSC"].strip()
                           else 200.0)
    print(f"households: {len(sector):,}")

    # ---- assets
    assets = defaultdict(float)
    orphans = set()
    for prefix, sc, vc, tsrl, subs, label in ASSET_BLOCKS:
        tot, fb = block_totals(zf, prefix, sc, vc, tsrl, subs)
        bs = 0.0
        for h, v in tot.items():
            if h in sector:
                assets[h] += v
                bs += weight[h] * v
            else:
                orphans.add(h)
        print(f"  {label:22s}: hh={len(tot):6,}  fallback={fb:3d}  "
              f"weighted total= Rs {bs/1e12:8.3f} lakh crore")

    # block 12: financial assets total srl 11 (= items 1-7 & 10); srl 8 is a
    # count, 9 sum assured, 12 bullion & ornaments - all outside the published
    # assets concept. Bullion tracked separately as a diagnostic.
    b12tot, b12items, bullion = {}, defaultdict(float), defaultdict(float)
    for row in open_member(zf, "Visit 1_Block 12.csv"):
        s = norm_srl(row["b12_q1"])
        v = fnum(row["b12_q3"])
        h = row["HHID"]
        if s == "11":
            b12tot[h] = b12tot.get(h, 0.0) + v
        elif s in B12_VALUE_ITEMS:
            b12items[h] += v
        elif s == "12":
            bullion[h] += v
    fb = 0
    for h, v in b12items.items():
        if h not in b12tot:
            b12tot[h] = v
            fb += 1
    bs = 0.0
    for h, v in b12tot.items():
        if h in sector:
            assets[h] += v
            bs += weight[h] * v
        else:
            orphans.add(h)
    print(f"  {'financial assets':22s}: hh={len(b12tot):6,}  fallback={fb:3d}  "
          f"weighted total= Rs {bs/1e12:8.3f} lakh crore")
    if orphans:
        print(f"  WARN: {len(orphans)} asset-block households missing from block 3")

    # ---- debt: block 14 cash loans, period 1 = outstanding on 30.06.2012
    debt = defaultdict(float)
    inst_debt = defaultdict(float)
    for row in open_member(zf, "Visit 1_Block 14.csv"):
        s = norm_srl(row["b14_q1"])
        if s == "99" or (row["b14_q4"] or "").strip() != "1":
            continue
        h = row["HHID"]
        q17 = fnum(row["b14_q17"])
        debt[h] += q17
        if norm_srl(row["b14_q6"]) in INSTITUTIONAL:
            inst_debt[h] += q17

    # ---- aggregate cells
    def cell(rel, res):
        hh = [h for h in sector
              if (rel == "all" or religion[h] == rel)
              and (res == "all" or sector[h] == res)]
        W = sum(weight[h] for h in hh)
        wa = sum(weight[h] * assets[h] for h in hh)
        wd = sum(weight[h] * debt[h] for h in hh)
        wi = sum(weight[h] * inst_debt[h] for h in hh)
        wioi = sum(weight[h] for h in hh if debt[h] > 0)
        return {
            "religion": rel, "residence": res,
            "avg_assets_rs": round(wa / W),
            "avg_debt_rs": round(wd / W),
            "avg_net_worth_rs": round((wa - wd) / W),
            "ioi_pct": f"{100.0 * wioi / W:.2f}",
            "institutional_debt_share_pct": f"{100.0 * wi / wd:.2f}" if wd else "",
            "n_households": len(hh),
        }

    rows = [cell(rel, res) for rel in RELIGIONS for res in RESIDENCES]
    by = {(r["religion"], r["residence"]): r for r in rows}

    # ---- validation gates
    print("\n--- validation vs published KI(70/18.2) ---")
    ok = True
    for res in ("rural", "urban"):
        r = by[("all", res)]
        checks = [
            ("n",   r["n_households"], PUB["n"][res], 0.0),
            ("AVA", r["avg_assets_rs"], PUB["ava"][res], 0.03),
            ("AOD", r["avg_debt_rs"], PUB["aod"][res], 0.03),
            ("IOI", float(r["ioi_pct"]), PUB["ioi"][res], 0.03),
        ]
        for name, got, want, tol in checks:
            rel_err = abs(got - want) / want
            good = rel_err <= tol if tol else got == want
            ok &= good
            print(f"  {'OK ' if good else 'FAIL'} {res} {name:4s}: computed "
                  f"{got:>12,} vs published {want:>12,}  ({100*rel_err:+.2f}%)"
                  .replace("+", ""))
        got_i = float(r["institutional_debt_share_pct"])
        want_i = PUB["inst"][res]
        flag = "OK " if abs(got_i - want_i) <= 2.0 else "WARN"
        print(f"  {flag} {res} inst: computed {got_i:>12,.1f} vs published "
              f"{want_i:>12,.1f}  (secondary, +-2pp)")
    if not ok:
        sys.exit("VALIDATION FAILED - L2 not written")

    # ---- diagnostics: bullion & ornaments (collected but outside published AVA)
    print("\n--- diagnostic: bullion & ornaments (block 12 srl 12, NOT in AVA) ---")
    for res in ("rural", "urban"):
        hh = [h for h in sector if sector[h] == res]
        W = sum(weight[h] for h in hh)
        wb = sum(weight[h] * bullion.get(h, 0.0) for h in hh)
        print(f"  {res}: avg Rs {wb/W:,.0f} per household "
              f"({100*wb/W/PUB['ava'][res]:.1f}% of published AVA)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["religion", "residence", "avg_assets_rs",
                                          "avg_debt_rs", "avg_net_worth_rs",
                                          "ioi_pct", "institutional_debt_share_pct",
                                          "n_households"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT.relative_to(ROOT)} ({len(rows)} rows)")

    print("\n--- headline: net worth / IOI / institutional share ---")
    for rel in RELIGIONS:
        for res in RESIDENCES:
            r = by[(rel, res)]
            print(f"  {rel:9s} {res:5s}: assets {r['avg_assets_rs']:>9,}  "
                  f"debt {r['avg_debt_rs']:>7,}  net {r['avg_net_worth_rs']:>9,}  "
                  f"IOI {r['ioi_pct']}%  inst {r['institutional_debt_share_pct']:>6}%  "
                  f"(n={r['n_households']:,})")


if __name__ == "__main__":
    main()
