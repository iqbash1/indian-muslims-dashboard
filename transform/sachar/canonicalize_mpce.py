#!/usr/bin/env python3
"""Canonicalize Monthly Per Capita Consumption Expenditure (MPCE) by religion (L3).

Metric: mpce -- average monthly spending per person, the standard Indian measure
of economic well-being (reliable income-by-religion data does not exist).

Only the Sachar Committee (NSS 61st round, 2004-05) publishes MPCE broken down
by religion / socio-religious category. Later rounds (HCES 2022-23) publish it
by social group (SC/ST/OBC/Others) only, so a current religion-wise figure needs
the unit-level microdata. When that is obtained, append a 2022-23 (or 2023-24)
row here and the card becomes a trend.

National combined values (residence=all) are transcribed directly from the Sachar
Report (2006) Chapter 8 section 2.1, all-India 2004-05: All-India Rs.712,
Muslims Rs.635 (H-General Rs.1023, SC/ST Rs.520 for context, not carded).

The urban/rural split (national + per state) comes from the L2 extraction of
Sachar Appendix Tables 8.2 (urban) and 8.3 (rural), via
transform/sachar/extract_mpce_by_state.py. These drive two drill-down tabs:
  - "Urban vs rural": national Muslim 804 urban / 553 rural vs All 1105 / 579 ->
    the Muslim-vs-average gap is wide in towns, near parity in villages.
  - "By state": per-state Muslim MPCE, urban and rural side by side.
The combined Rs.635 sits between the two strata (Muslims are ~35% urban), as
expected; it is published, the strata are published, but no combined per-state
figure exists, so the by-state tab shows urban and rural as published.

Re-run: python3 transform/sachar/extract_mpce_by_state.py   (L1->L2, first)
        python3 transform/sachar/canonicalize_mpce.py        (L2->L3)
"""
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from geography_codes import normalize_state_name

ROOT = pathlib.Path(__file__).resolve().parents[2]
L2 = ROOT / "extracted" / "sachar" / "sachar-mpce-by-state.csv"
OUT = ROOT / "canonical" / "mpce.csv"
RUN = "manual-extract-mpce-sachar-v2.0-20260609"

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

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out)} rows; {n_state} per-state muslim rows)")


if __name__ == "__main__":
    main()
