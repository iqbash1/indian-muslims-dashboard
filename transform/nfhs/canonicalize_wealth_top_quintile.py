#!/usr/bin/env python3
"""Canonicalize the NFHS wealth-index "top quintile by religion" series (L3).

Metric: wealth-top-quintile -- share of each community's de jure population in
the HIGHEST (richest) of India's five national wealth quintiles, NFHS-3/4/5.

The NFHS wealth index is an ASSET score (consumer durables, housing quality,
drinking water, sanitation, etc.), not income or spending. The national
population is split into five equal fifths, so by construction 20% of all
Indians fall in each quintile -- the all-communities reference line is 20.0.

Values transcribed directly from the published India report tables
("Religion ... of household head by wealth quintiles", the "Highest" column):
  NFHS-3 (2005-06): Table 2.18 (p.45) sources/nfhs-3/reports/india-report-frind3.pdf
  NFHS-4 (2015-16): Table 2.6  (p.31) sources/nfhs-4/reports/india-report-fr339.pdf
  NFHS-5 (2019-21): Table 2.9  (p.42) sources/nfhs-5/reports/india-report-fr375.pdf

Re-run: python3 transform/nfhs/canonicalize_wealth_top_quintile.py
"""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "canonical" / "wealth-top-quintile.csv"
RUN = "manual-extract-wealth-top-quintile-v1.0-20260607"

# year -> (source_id, archived source document, table reference)
ROUNDS = {
    2005: ("nfhs-3", "sources/nfhs-3/reports/india-report-frind3.pdf", "NFHS-3 (2005-06) Table 2.18"),
    2015: ("nfhs-4", "sources/nfhs-4/reports/india-report-fr339.pdf", "NFHS-4 (2015-16) Table 2.6"),
    2020: ("nfhs-5", "sources/nfhs-5/reports/india-report-fr375.pdf", "NFHS-5 (2019-21) Table 2.9"),
}

# religion -> {year: (highest-quintile %, de jure population as printed in the
# table, or None for the by-construction national reference)}
DATA = {
    "hindu":     {2005: (19.2, 418056),  2015: (19.1, 2203861), 2020: (19.1, 2251319)},
    "muslim":    {2005: (17.2, 74718),   2015: (18.8, 388606),  2020: (19.3, 380983)},
    "christian": {2005: (31.1, 11885),   2015: (28.1, 64722),   2020: (25.6, 67300)},
    "sikh":      {2005: (52.7, 8988),    2015: (60.2, 46401),   2020: (59.1, 45088)},
    "buddhist":  {2005: (22.3, 4342),    2015: (20.6, 24734),   2020: (17.8, 18356)},
    "jain":      {2005: (86.8, 1784),    2015: (74.9, 5448),    2020: (80.1, 7048)},
    "all":       {2005: (20.0, None),    2015: (20.0, None),    2020: (20.0, None)},
}

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion", "value",
        "denominator", "sample_size", "ci_lower", "ci_upper", "source_id", "source_document",
        "extraction_run", "methodology_note", "break_flag"]


def main():
    rows = []
    for religion, by_year in DATA.items():
        for year, (value, n) in by_year.items():
            sid, doc, tref = ROUNDS[year]
            if religion == "all":
                note = ("By construction 20% of India's de jure population falls in each wealth "
                        f"quintile ({tref} Total row). National reference line.")
            else:
                note = (f"{tref} 'Religion and caste/tribe of household head by wealth quintiles', "
                        "India; HIGHEST (richest) of 5 national wealth quintiles. NFHS asset-based "
                        "wealth index (durables, housing, drinking water, sanitation).")
            rows.append({
                "metric_id": "wealth-top-quintile", "geography_level": "national",
                "geography_code": "IN", "year": year, "religion": religion, "value": value,
                "denominator": "de_jure_population", "sample_size": ("" if n is None else n),
                "ci_lower": "", "ci_upper": "", "source_id": sid, "source_document": doc,
                "extraction_run": RUN, "methodology_note": note, "break_flag": "false",
            })
    rows.sort(key=lambda r: (r["year"], r["religion"]))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
