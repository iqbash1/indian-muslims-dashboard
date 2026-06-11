#!/usr/bin/env python3
"""Compute household wealth and debt by religion from AIDIS 2019 microdata (L2).

L1 source: MoSPI's own fixed-width TXT distribution of NSS 77th round Schedule
18.2 (All-India Debt & Investment Survey, fielded January-December 2019, asset
and debt stocks as on 30.06.2018), Visit 1: r77182v1L01.TXT .. L17.TXT served
from the unlinked directory mospi.gov.in/sites/default/files/NSS7718/ (the
NADA catalog id 156 ships the same survey only as a proprietary .Nesstar
binary). The ~380 MB stays LOCAL at ~/Desktop/nada-work/aidis-2018-19-alt/
(sha256s in sources/nss77-aidis/SHA256SUMS.txt). Override the archive dir with
argv[1]. Byte map + gotchas: nada/aidis-layout-map.md (2019 section); layout
authority NSS_77th_Layout_Sch_18.2_mult_post.xls, same directory.

Record format (README77182_v1m.pdf): 139 data bytes + CRLF; bytes 1-126 data,
127-129 NSC, 130-139 multiplier (two implied decimals). Final household
weight = MLT/100 (no sub-sample halving in this round's posted data; there is
no NSS field at all). Household key = FSU(4-8) + SSS(30) + hhno(31-32).

Method (Visit 1 only, all 116,461 households; the official Report-1 recipe,
Final Tabulation Plan NSS 77th R Sch 18.2 para 16):
  - Universe + religion + weight: level 03 (block 4), one row per household;
    religion byte 44 (1 Hinduism, 2 Islam, 3 Christianity, 4 Sikhism,
    5 Jainism, 6 Buddhism, 7 Zoroastrianism, 9 others); sector byte 15.
  - ASSETS per household as on 30.06.2018 = sum over 9 asset blocks of the
    block's TOTAL row value (tabulation plan's block/item/column references):
      level 05 = block 5.1 land rural-type   total srl 99, col 5 (bytes 49-60)
      level 06 = block 5.2 land urban-type   total srl 99, col 5 (bytes 49-60)
      level 07 = block 6  buildings          total srl 10, col 5 (bytes 51-62)
      level 08 = block 7  livestock          total srl 17, col 4 (bytes 51-62)
      level 09 = block 8  transport          total srl 8,  col 4 (bytes 51-62)
      level 10 = block 9  agri machinery     total srl 13, col 4 (bytes 51-62)
      level 11 = block 10 non-farm equipment total srl 20, col 3 (bytes 41-52)
      level 12 = block 11a financial assets incl. receivables
                                             total srl 19, col 6 (bytes 77-88)
      level 13 = block 11b shares & related  total srl 5,  col 6 (bytes 77-88)
    Blocks 11a/11b record stocks as on the survey date plus transactions since
    01.07.2018; col 6 = col 3 + col 5 - col 4 backs out the 30.06.2018 value.
    Block 11a srl 20 (bullion & ornaments) and srl 21 (paintings/artistic
    originals) are memo items OUTSIDE the total, same concept as 2013.
    Fallback for households with item rows but no total row: sum of item rows
    (serials below the total serial only).
  - DEBT per household = level 14 (block 12, cash loans) item rows (srl != 99)
    with byte 45 == 1 ("loan remained unpaid on 30.06.2018"), summing
    col 15 = amount outstanding incl. interest as on 30.06.2018 (bytes
    108-119). Kind loans (block 13) are as on the survey date and outside the
    published AOD, as in 2013.
  - IOI = weighted share of households with that debt > 0; institutional
    share of debt resolved at runtime among three candidate rules (the
    instructions' agency-code list, the DDI's divergent labelling, and the
    questionnaire's serial-number ranges) against the published 66/87 anchors;
    the winning rule is printed and used for the by-religion split.

Validation gates (script exits without writing the L2 if breached; published
figures from MoSPI press note 24.08.2021 on AIDIS NSS 77th round, fetched live
from mospi.gov.in/sites/default/files/press_release/press_note-AIDIS-240821.pdf):
  1. unweighted sample = 69,455 rural + 47,006 urban households (exact)
  2. all-India AVA  rural 15,92,379 / urban 27,17,081 Rs   +-3%
  3. all-India AOD  rural 59,748 / urban 1,20,336 Rs       +-3%
  4. all-India IOI  rural 35.0% / urban 22.4%              +-3% rel.
  5. institutional share of outstanding cash debt rural 66% / urban 87%
     (one of the three candidate rules must land within 1pp)
  Secondary diagnostics (printed): physical vs financial AVA split (published
  rural 15,19,771 / 72,608, urban 24,65,277 / 2,51,804), AODL (1,70,533 /
  5,36,861), bullion memo value.

Writes extracted/aidis/aidis-2018-wealth-by-religion.csv:
  religion,residence,avg_assets_rs,avg_debt_rs,avg_net_worth_rs,ioi_pct,
  institutional_debt_share_pct,n_households
(religions muslim/hindu/christian/sikh/all x residence all/rural/urban; assets,
debt, net worth = weighted means per household in Rs as on 30.06.2018.)

Run:  .venv/bin/python transform/aidis/extract_wealth_2018_by_religion.py [archive-dir]
"""
import csv
import os
import pathlib
import sys
from collections import defaultdict

ARCHIVE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                       else os.path.expanduser("~/Desktop/nada-work/aidis-2018-19-alt"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "extracted" / "aidis" / "aidis-2018-wealth-by-religion.csv"

# published all-India figures (MoSPI press note 24.08.2021, as on 30.06.2018)
PUB = {
    "n":    {"rural": 69455, "urban": 47006},
    "ava":  {"rural": 1592379, "urban": 2717081},
    "aod":  {"rural": 59748, "urban": 120336},
    "ioi":  {"rural": 35.0, "urban": 22.4},
    "inst": {"rural": 66.0, "urban": 87.0},
    "ava_phys": {"rural": 1519771, "urban": 2465277},
    "ava_fin":  {"rural": 72608, "urban": 251804},
    "aodl": {"rural": 170533, "urban": 536861},
}

# asset levels: (level, srl slice, value slice, total srl, memo srls, label)
# byte positions from NSS_77th_Layout_Sch_18.2_mult_post.xls (1-indexed, inclusive)
def sl(a, b):  # 1-indexed inclusive byte range -> python slice
    return slice(a - 1, b)

ASSET_LEVELS = [
    ("05", sl(39, 40), sl(49, 60), "99", set(),       "land (rural-type)"),
    ("06", sl(39, 40), sl(49, 60), "99", set(),       "land (urban-type)"),
    ("07", sl(39, 40), sl(51, 62), "10", set(),       "buildings"),
    ("08", sl(39, 40), sl(51, 62), "17", set(),       "livestock"),
    ("09", sl(40, 40), sl(51, 62), "8",  set(),       "transport equipment"),
    ("10", sl(39, 40), sl(51, 62), "13", set(),       "agri machinery"),
    ("11", sl(39, 40), sl(41, 52), "20", set(),       "non-farm equipment"),
    ("12", sl(39, 40), sl(77, 88), "19", {"20", "21"}, "financial assets (11a)"),
    ("13", sl(40, 40), sl(77, 88), "5",  set(),       "shares & related (11b)"),
]
FINANCIAL_LEVELS = {"12", "13"}  # for the physical/financial diagnostic

# institutional credit-agency candidate rules (block 12 col 5, bytes 58-59)
INST_INSTRUCTIONS = {"1", "2", "3", "4", "5", "6", "7", "8", "10", "11", "12", "13"}
INST_DDI = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "11", "12", "13"}

RMAP = {"1": "hindu", "2": "muslim", "3": "christian", "4": "sikh"}
RELIGIONS = ["muslim", "hindu", "christian", "sikh", "all"]
RESIDENCES = ["all", "rural", "urban"]


def fnum(s):
    s = s.strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def norm_srl(s):
    return s.strip().lstrip("0") or "0"


def lines(level):
    path = ARCHIVE / f"r77182v1L{level}.TXT"
    with path.open("r", encoding="ascii", errors="replace", newline="") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if len(line) >= 139:
                yield line


def hhkey(line):
    return line[3:8] + line[29] + line[30:32]   # FSU + SSS + hh no


def level_totals(level, srl_sl, val_sl, total_srl, memo):
    """Per-household block value: TOTAL row if present, else item-row sum
    (serials below the total serial; memo serials and junk skipped)."""
    tot, items = {}, defaultdict(float)
    max_item = int(total_srl) if total_srl != "99" else 98
    nrows = 0
    for line in lines(level):
        nrows += 1
        s = norm_srl(line[srl_sl])
        v = fnum(line[val_sl])
        h = hhkey(line)
        if s == total_srl:
            tot[h] = tot.get(h, 0.0) + v
        elif s not in memo:
            try:
                if int(s) < max_item or (total_srl == "99" and int(s) <= 98):
                    items[h] += v
            except ValueError:
                pass
    fallback = 0
    for h, v in items.items():
        if h not in tot:
            tot[h] = v
            fallback += 1
    # reconciliation: weighted-free ratio of item sums to total rows where both exist
    both = [h for h in items if h in tot and tot[h] > 0 and h not in ()]
    num = sum(items[h] for h in both if tot.get(h, 0) > 0)
    den = sum(tot[h] for h in both if tot.get(h, 0) > 0)
    ratio = num / den if den else float("nan")
    return tot, fallback, nrows, ratio


def main():
    # ---- universe: level 03 (block 4; one row per surveyed household)
    sector, religion, weight = {}, {}, {}
    samples = set()
    for line in lines("03"):
        h = hhkey(line)
        sector[h] = {"1": "rural", "2": "urban"}.get(line[14])
        religion[h] = RMAP.get(line[43])
        weight[h] = fnum(line[129:139]) / 100.0
        samples.add(line[13])
    n_r = sum(1 for h in sector if sector[h] == "rural")
    n_u = sum(1 for h in sector if sector[h] == "urban")
    print(f"households: {len(sector):,} (rural {n_r:,} / urban {n_u:,}); "
          f"sample codes seen: {sorted(samples)}")
    wpop_r = sum(weight[h] for h in sector if sector[h] == "rural")
    wpop_u = sum(weight[h] for h in sector if sector[h] == "urban")
    print(f"weighted households: rural {wpop_r/1e6:.1f}M / urban {wpop_u/1e6:.1f}M")

    # ---- assets
    assets = defaultdict(float)
    fin_assets = defaultdict(float)
    orphans = set()
    for level, srl_sl, val_sl, tsrl, memo, label in ASSET_LEVELS:
        tot, fb, nrows, ratio = level_totals(level, srl_sl, val_sl, tsrl, memo)
        bs = 0.0
        for h, v in tot.items():
            if h in sector:
                assets[h] += v
                if level in FINANCIAL_LEVELS:
                    fin_assets[h] += v
                bs += weight[h] * v
            else:
                orphans.add(h)
        print(f"  L{level} {label:24s}: rows={nrows:7,} hh={len(tot):7,} "
              f"fallback={fb:4d} item/total={ratio:6.3f} "
              f"weighted= Rs {bs/1e12:8.3f} lakh crore")
    if orphans:
        print(f"  WARN: {len(orphans)} asset-level households missing from level 03")

    # bullion & paintings memo (block 11a srl 20/21, outside the total)
    bullion = defaultdict(float)
    for line in lines("12"):
        s = norm_srl(line[38:40])
        if s in ("20", "21"):
            bullion[hhkey(line)] += fnum(line[76:88])

    # ---- debt: level 14 (block 12 cash loans)
    debt = defaultdict(float)
    inst_debt_a = defaultdict(float)   # instructions rule (09 non-inst, 10 inst)
    inst_debt_b = defaultdict(float)   # DDI-label rule (09 inst, no 10)
    inst_debt_s = defaultdict(float)   # serial-range rule (srl 1-50 inst)
    q15_on_paid = 0
    agency_seen = defaultdict(int)
    for line in lines("14"):
        s = norm_srl(line[38:40])
        if s == "99":
            continue
        unpaid = line[44] == "1"
        q15 = fnum(line[107:119])
        if not unpaid:
            if q15 > 0:
                q15_on_paid += 1
            continue
        h = hhkey(line)
        debt[h] += q15
        agency = norm_srl(line[57:59])
        agency_seen[agency] += 1
        if agency in INST_INSTRUCTIONS:
            inst_debt_a[h] += q15
        if agency in INST_DDI:
            inst_debt_b[h] += q15
        try:
            if int(s) <= 50:
                inst_debt_s[h] += q15
        except ValueError:
            pass
    print(f"  L14 cash loans: q15>0 on {q15_on_paid} loans flagged paid-off "
          f"(expect 0/handful); agency codes seen: "
          f"{dict(sorted(agency_seen.items(), key=lambda kv: int(kv[0])))}")

    # ---- choose the institutional rule against the published anchors
    def all_india_share(im):
        out = {}
        for res in ("rural", "urban"):
            hh = [h for h in sector if sector[h] == res]
            wd = sum(weight[h] * debt[h] for h in hh)
            wi = sum(weight[h] * im.get(h, 0.0) for h in hh)
            out[res] = 100.0 * wi / wd if wd else float("nan")
        return out

    candidates = [("instructions (09 non-inst, 10 inst)", inst_debt_a),
                  ("DDI labels (09 inst, no 10)", inst_debt_b),
                  ("serial range (srl 1-50)", inst_debt_s)]
    print("\n--- institutional-share rule resolution (published rural 66 / urban 87) ---")
    best = None
    for name, im in candidates:
        sh = all_india_share(im)
        err = abs(sh["rural"] - PUB["inst"]["rural"]) + abs(sh["urban"] - PUB["inst"]["urban"])
        print(f"  {name:38s}: rural {sh['rural']:5.1f} / urban {sh['urban']:5.1f}")
        if best is None or err < best[3]:
            best = (name, im, sh, err)
    inst_name, inst_debt, inst_sh, _ = best
    print(f"  -> using: {inst_name}")

    # ---- aggregate cells
    def cell(rel, res):
        hh = [h for h in sector
              if (rel == "all" or religion[h] == rel)
              and (res == "all" or sector[h] == res)]
        W = sum(weight[h] for h in hh)
        wa = sum(weight[h] * assets[h] for h in hh)
        wd = sum(weight[h] * debt[h] for h in hh)
        wi = sum(weight[h] * inst_debt.get(h, 0.0) for h in hh)
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
    print("\n--- validation vs MoSPI press note 24.08.2021 (as on 30.06.2018) ---")
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
        got_i = inst_sh[res]
        good_i = abs(got_i - PUB["inst"][res]) <= 1.0
        ok &= good_i
        print(f"  {'OK ' if good_i else 'FAIL'} {res} inst: computed "
              f"{got_i:>12,.1f} vs published {PUB['inst'][res]:>12,.1f}  (+-1pp)")
    if not ok:
        sys.exit("VALIDATION FAILED - L2 not written")

    # ---- diagnostics
    print("\n--- diagnostics vs press note ---")
    for res in ("rural", "urban"):
        hh = [h for h in sector if sector[h] == res]
        W = sum(weight[h] for h in hh)
        wfin = sum(weight[h] * fin_assets.get(h, 0.0) for h in hh)
        wtot = sum(weight[h] * assets[h] for h in hh)
        wbul = sum(weight[h] * bullion.get(h, 0.0) for h in hh)
        ioi = float(by[("all", res)]["ioi_pct"])
        aodl = by[("all", res)]["avg_debt_rs"] / (ioi / 100.0) if ioi else 0
        print(f"  {res}: physical {(wtot-wfin)/W:>12,.0f} (pub {PUB['ava_phys'][res]:,})  "
              f"financial {wfin/W:>9,.0f} (pub {PUB['ava_fin'][res]:,})")
        print(f"  {res}: AODL {aodl:>12,.0f} (pub {PUB['aodl'][res]:,})  "
              f"bullion memo avg Rs {wbul/W:,.0f}/hh (outside AVA)")

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
