#!/usr/bin/env python3
"""Canonicalize Monthly Per Capita Consumption Expenditure (MPCE) by religion (L3).

Metric: mpce -- average monthly spending per person, the standard Indian measure
of economic well-being (reliable income-by-religion data does not exist).

Only the Sachar Committee (NSS 61st round, 2004-05) publishes MPCE broken down
by religion / socio-religious category. Later rounds (HCES 2022-23) publish it
by social group (SC/ST/OBC/Others) only, so a current religion-wise figure needs
the unit-level microdata. When that is obtained, append a 2022-23 (or 2023-24)
row here and the card becomes a trend.

Values transcribed directly from the Sachar Committee Report (2006), Chapter 8,
"Poverty, Consumption and Standards of Living", section 2.1 (Mean per Capita
Expenditures), all-India, 2004-05:
  All-India average .... Rs. 712
  H-General ............ Rs. 1023   (context, not carded)
  H-OBC ................ Rs. 646    (context, not carded)
  Muslims .............. Rs. 635
  SC/ST ................ Rs. 520    (context, not carded)
Source doc: sources/sachar-committee-2006/sachar-comm-report-india-2006.pdf

Re-run: python3 transform/sachar/canonicalize_mpce.py
"""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "canonical" / "mpce.csv"
RUN = "manual-extract-mpce-sachar-v1.0-20260607"

SACHAR_DOC = "sources/sachar-committee-2006/sachar-comm-report-india-2006.pdf"
SACHAR_NOTE = (
    "Sachar Committee (2006), Chapter 8 section 2.1, from NSS 61st round (2004-05); "
    "all-India average MPCE by socio-religious category. Muslims Rs.635 vs the "
    "all-India average Rs.712, near SC/ST (Rs.520) and far below upper-caste "
    "'Hindu General' households (Rs.1023); Muslim deprivation is sharpest in urban "
    "areas. Most recent figure published by religion: later rounds (HCES 2022-23) "
    "give spending by social group only. Rupees are 2004-05 nominal."
)

# year -> {religion: value}. Add a 2022-23/2023-24 block here once the HCES
# microdata is processed (with its own source_id/source_document).
ROWS = [
    # (year, religion, value, source_id, source_document, note)
    (2004, "muslim", 635, "sachar-committee-2006", SACHAR_DOC, SACHAR_NOTE),
    (2004, "all",    712, "sachar-committee-2006", SACHAR_DOC,
     "Sachar Committee (2006), Ch.8 s.2.1, NSS 61st round (2004-05): all-India "
     "average MPCE (across all communities). Rupees are 2004-05 nominal."),
]

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion", "value",
        "denominator", "sample_size", "ci_lower", "ci_upper", "source_id", "source_document",
        "extraction_run", "methodology_note", "break_flag"]


def main():
    out = []
    for year, religion, value, sid, doc, note in ROWS:
        out.append({
            "metric_id": "mpce", "geography_level": "national", "geography_code": "IN",
            "year": year, "religion": religion, "value": value,
            "denominator": "per_person_per_month", "sample_size": "", "ci_lower": "",
            "ci_upper": "", "source_id": sid, "source_document": doc,
            "extraction_run": RUN, "methodology_note": note, "break_flag": "false",
        })
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT} ({len(out)} rows)")


if __name__ == "__main__":
    main()
