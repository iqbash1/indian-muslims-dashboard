"""
L2 -> L3 for the `sex-ratio` metric (females per 1000 males).

Decennial series, one canonical row per (year x geography x religion):
  sex_ratio = females / males * 1000   at all ages, total residence

Sources (identical all-ages / total-residence definition — verified
table-invariant: 2011 sex ratios computed from C-01 match C-15 exactly):
  2011  extracted/census-2011/c15-religion-by-age-sex.csv  (age='All ages')
        -> national + state + district
  2001  extracted/census-2001/c01-population-by-religion.csv
        -> national + state  (all-India 2001 C-1 file carries no districts)

Emits each religion in OUTPUT_RELIGIONS. The two rounds form the 2001->2011
trend the dashboard renders as a time series.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_C15_2011 = REPO_ROOT / "extracted" / "census-2011" / "c15-religion-by-age-sex.csv"
L2_C01_2001 = REPO_ROOT / "extracted" / "census-2001" / "c01-population-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "sex-ratio.csv"
CANONICALIZER_VERSION = "2.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")
DENOMINATOR = "females_per_1000_males_total_residence_all_ages"

SRC_2011 = (
    "census-india-2011",
    "sources/census-2011/c-series/c15-religion-by-age-sex.xlsx",
    "Females / Males * 1000 at All ages, Total residence.",
)
SRC_2001 = (
    "census-india-2001",
    "sources/census-2001/c-series/c01-population-by-religion.xls",
    "Females / Males * 1000 at total residence (all ages, from C-1 "
    "population-by-religion). Same all-ages total-residence definition as the "
    "2011 C-15 figure (verified table-invariant: 2011 C-01 reproduces C-15).",
)

LEVEL_RANK = {"national": 0, "state": 1, "district": 2}
RELIGION_RANK = {r: i for i, r in enumerate(OUTPUT_RELIGIONS)}


def _geo_c15(state_code: str, distt_code: str) -> tuple[str, str]:
    if state_code == "00" and distt_code == "000":
        return "national", "IN"
    if distt_code == "000":
        return "state", f"IN-S{state_code}"
    return "district", f"IN-S{state_code}-D{distt_code}"


def _cells_2011() -> dict[tuple[str, str, str, str], int]:
    cells: dict[tuple[str, str, str, str], int] = {}
    with L2_C15_2011.open() as f:
        for row in csv.DictReader(f):
            if row["residence"] != "total" or row["age_group"] != "All ages":
                continue
            if row["sex"] not in ("males", "females"):
                continue
            level, code = _geo_c15(row["state_code"], row["distt_code"])
            cells[(level, code, row["religion"], row["sex"])] = int(row["value"])
    return cells


def _cells_2001() -> dict[tuple[str, str, str, str], int]:
    # C-01 2001 all-India file: national (state_code 00) + states; no districts.
    cells: dict[tuple[str, str, str, str], int] = {}
    with L2_C01_2001.open() as f:
        for row in csv.DictReader(f):
            if row["residence"] != "total" or row["sex"] not in ("males", "females"):
                continue
            if row["distt_code"] != "00":
                continue  # defensive: all-India C-1 has no district rows
            state = row["state_code"]
            level, code = ("national", "IN") if state == "00" else ("state", f"IN-S{state}")
            cells[(level, code, row["religion"], row["sex"])] = int(row["value"])
    return cells


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-sex-ratio-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rounds = [(2011, _cells_2011(), SRC_2011), (2001, _cells_2001(), SRC_2001)]

    out_rows: list[list] = []
    n_missing = 0
    for year, cells, (src_id, src_doc, note) in rounds:
        geographies = {(lv, cd) for (lv, cd, _, _) in cells}
        for (level, code) in geographies:
            for religion in OUTPUT_RELIGIONS:
                males = cells.get((level, code, religion, "males"))
                females = cells.get((level, code, religion, "females"))
                if not males or not females:
                    n_missing += 1
                    continue
                ratio = round(females / males * 1000, 1)
                out_rows.append([
                    "sex-ratio", level, code, year, religion,
                    ratio, DENOMINATOR, "", "", "",
                    src_id, src_doc, extraction_run, note, "false",
                ])

    out_rows.sort(key=lambda r: (LEVEL_RANK[r[1]], r[2], r[3], RELIGION_RANK[r[4]]))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        w.writerows(out_rows)

    years = sorted({r[3] for r in out_rows})
    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({len(out_rows)} rows; years {years}; {n_missing} incomplete cells)"
    )


if __name__ == "__main__":
    canonicalize()
