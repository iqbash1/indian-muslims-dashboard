#!/usr/bin/env python3
"""Canonicalize Monthly Per Capita Consumption Expenditure (MPCE) by religion (L3).

Metric: mpce -- average monthly spending per person, the standard Indian measure
of economic well-being (reliable income-by-religion data does not exist).

TWO sources merge into canonical/mpce.csv:

1. Sachar Committee (NSS 61st round, 2004-05) -- the historical benchmark.
   National combined values (residence=all) are transcribed directly from the
   Sachar Report (2006) Chapter 8 section 2.1, all-India 2004-05: All-India
   Rs.712, Muslims Rs.635 (H-General Rs.1023, SC/ST Rs.520 for context). The
   urban/rural split (national + per state) comes from the L2 extraction of
   Appendix Tables 8.2/8.3 via transform/sachar/extract_mpce_by_state.py.

2. HCES 2023-24 unit-level microdata (NSO, via the MoSPI NADA API) -- the
   current point, computed (NOT published; factsheets stop at social group).
   L2 = extracted/hces/hces-2023-24-mpce-by-religion.csv, written by
   transform/hces/extract_mpce_2023_24_by_state.py (national + per-state x
   religion x residence, with unweighted household counts). Drives the card
   hero (year=2023), the "Urban vs rural" tab, and the "By state" tab (the
   builder shows the LATEST year, so 2023-24 supersedes Sachar there while the
   2004 state rows stay in the file as history). Per-state cells with fewer
   than 30 sampled Muslim households are suppressed (NSS small-sample rule).

Re-run: python3 transform/sachar/extract_mpce_by_state.py          (L1->L2, Sachar)
        .venv/bin/python transform/hces/extract_mpce_2023_24_by_state.py  (L1->L2, HCES; needs the local 244MB zip)
        python3 transform/sachar/canonicalize_mpce.py               (L2->L3, merges both)
"""
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from geography_codes import normalize_state_name

ROOT = pathlib.Path(__file__).resolve().parents[2]
L2 = ROOT / "extracted" / "sachar" / "sachar-mpce-by-state.csv"
L2_HCES = ROOT / "extracted" / "hces" / "hces-2023-24-mpce-by-religion.csv"
OUT = ROOT / "canonical" / "mpce.csv"
RUN = "manual-extract-mpce-sachar-v2.0-20260609"
RUN_HCES = "canonicalize-mpce-hces-v1.1-20260610"
MIN_CELL = 30  # NSS convention: suppress estimates from <30 sample households

SACHAR_DOC = "sources/sachar-committee-2006/sachar-comm-report-india-2006.pdf"
NOTE_NAT_MUSLIM = (
    "Sachar Committee (2006), Chapter 8 section 2.1, from NSS 61st round (2004-05); "
    "all-India average MPCE by socio-religious category. Muslims Rs.635 vs the "
    "all-India average Rs.712, near SC/ST (Rs.520) and far below upper-caste "
    "'Hindu General' households (Rs.1023); Muslim deprivation is sharpest in urban "
    "areas. Most recent figure published by religion: later rounds (HCES 2022-23) "
    "give spending by social group only. Rupees are 2004-05 nominal."
)
NOTE_NAT_ALL = (
    "Sachar Committee (2006), Ch.8 s.2.1, NSS 61st round (2004-05): all-India "
    "average MPCE (across all communities). Rupees are 2004-05 nominal."
)
NOTE_URBAN_RURAL = (
    "Sachar Committee (2006) Appendix Table 8.{tbl} ({res} MPCE by socio-religious "
    "category, NSS 61st round 2004-05, current prices). The combined all-India "
    "Rs.635 (Muslim) sits between these strata. Rupees are 2004-05 nominal."
)
NOTE_STATE = (
    "Sachar Committee (2006) Appendix Table 8.{tbl}: state-level {res} Muslim MPCE "
    "(NSS 61st round 2004-05, current prices). No combined per-state figure is "
    "published, so urban and rural are shown as reported. Rupees are 2004-05 nominal."
)

HCES_DOC = "sources/hces-2023-24/HCES_Data_2023-24_Csv.zip"
NOTE_HCES_NAT = (
    "Computed from HCES 2023-24 unit-level microdata (NSO; 2.61 lakh households) "
    "pulled via the MoSPI NADA API: weighted monthly per capita consumption "
    "expenditure (food + consumables & services + durables, 365-day items "
    "annualised), cross-classified by religion of the household head. Reproduces "
    "the published national MPCE (rural Rs.4,122 / urban Rs.6,996) within ~2%. "
    "NSO unit-data rider: religion is self-reported and unverified and the survey "
    "is designed for MPCE estimation, so this religion split is indicative and no "
    "sub-state estimate is made. MMRP method; 2023-24 nominal rupees (not "
    "comparable in level to the 2004-05 URP figure)."
)
NOTE_HCES_STATE = (
    "Computed from HCES 2023-24 unit-level microdata (NSO) pulled via the MoSPI "
    "NADA API: weighted per-state Muslim MPCE, urban and rural separately. "
    "State/UT is the survey's basic stratum, so a state-level religion cross-tab "
    "is the finest permitted cut (no sub-state estimates); cells with fewer than "
    "30 sampled Muslim households are suppressed, per NSS small-sample practice. "
    "MMRP method; 2023-24 nominal rupees, not level-comparable to the 2004-05 "
    "Sachar state figures (URP) retained in this file."
)

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion", "residence",
        "value", "denominator", "sample_size", "ci_lower", "ci_upper", "source_id",
        "source_document", "extraction_run", "methodology_note", "break_flag"]
TBL = {"urban": "2", "rural": "3"}


def row(level, code, religion, residence, value, note):
    return {
        "metric_id": "mpce", "geography_level": level, "geography_code": code,
        "year": 2004, "religion": religion, "residence": residence, "value": value,
        "denominator": "per_person_per_month", "sample_size": "", "ci_lower": "",
        "ci_upper": "", "source_id": "sachar-committee-2006", "source_document": SACHAR_DOC,
        "extraction_run": RUN, "methodology_note": note, "break_flag": "false",
    }


def hces_row(level, code, religion, residence, value, n_households, note):
    return {
        "metric_id": "mpce", "geography_level": level, "geography_code": code,
        "year": 2023, "religion": religion, "residence": residence, "value": value,
        "denominator": "per_person_per_month", "sample_size": n_households,
        "ci_lower": "", "ci_upper": "", "source_id": "hces-2023-24",
        "source_document": HCES_DOC, "extraction_run": RUN_HCES,
        "methodology_note": note, "break_flag": "true",
    }


def hces_rows():
    """HCES 2023-24 rows from the microdata L2: national (muslim/hindu/all x
    all/urban/rural -> card face + Urban-vs-rural tab) + per-state muslim
    urban/rural (-> the By state tab, which renders the latest year). Cells
    under MIN_CELL sampled households are suppressed."""
    if not L2_HCES.exists():
        print(f"  WARN {L2_HCES.relative_to(ROOT)} missing - HCES 2023-24 rows skipped")
        return []
    out = []
    n_state = 0
    for r in csv.DictReader(L2_HCES.open()):
        val = round(float(r["mpce_rs"]))
        n = int(r["n_households"])
        if r["scope"] == "national":
            out.append(hces_row("national", "IN", r["religion"], r["residence"],
                                val, n, NOTE_HCES_NAT))
        elif r["religion"] == "muslim" and r["residence"] in ("urban", "rural"):
            if n < MIN_CELL:
                continue
            code = f"IN-S{int(r['state_code']):02d}"
            out.append(hces_row("state", code, "muslim", r["residence"],
                                val, n, NOTE_HCES_STATE))
            n_state += 1
    print(f"  HCES 2023-24: {len(out)} rows ({n_state} per-state muslim cells >= {MIN_CELL} households)")
    return out


def main():
    out = [
        # National combined (published Ch.8 s.2.1), residence=all -> card face.
        row("national", "IN", "muslim", "all", 635, NOTE_NAT_MUSLIM),
        row("national", "IN", "all", "all", 712, NOTE_NAT_ALL),
    ]

    l2 = list(csv.DictReader(L2.open()))
    n_state = 0
    unmapped = set()
    for res in ("urban", "rural"):
        rows_res = [r for r in l2 if r["residence"] == res]
        ai = next(r for r in rows_res if r["state_name"] == "All India")
        # National urban/rural: Muslim + All (matches the card's Muslim-vs-average framing).
        out.append(row("national", "IN", "muslim", res, int(ai["muslim"]),
                       NOTE_URBAN_RURAL.format(tbl=TBL[res], res=res.capitalize())))
        out.append(row("national", "IN", "all", res, int(ai["all"]),
                       NOTE_URBAN_RURAL.format(tbl=TBL[res], res=res.capitalize())))
        # Per-state Muslim urban/rural -> the "By state" (urban + rural) tab.
        for r in rows_res:
            if r["state_name"] in ("All India", "All other States"):
                continue
            code = normalize_state_name(r["state_name"])
            if code is None:
                unmapped.add(r["state_name"])
                continue
            out.append(row("state", code, "muslim", res, int(r["muslim"]),
                           NOTE_STATE.format(tbl=TBL[res], res=res)))
            n_state += 1

    if unmapped:
        print(f"  WARN unmapped states: {sorted(unmapped)}")

    out.extend(hces_rows())

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out)} rows; {n_state} per-state muslim rows)")


if __name__ == "__main__":
    main()
