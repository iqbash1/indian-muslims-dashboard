"""
L2 -> L3 for the `sex-ratio` metric (females per 1000 males).

Decennial series, one canonical row per (year x geography x religion):
  sex_ratio = females / males * 1000   at all ages, total residence

All six rounds 1961 → 2011 are now PRIMARY (Commit AJ — Sachar fallback
retired). Identical all-ages / total-residence definition across rounds;
verified table-invariant at 2011 (C-01 reproduces C-15) and confirmed by
the Sachar AT 3.8 compilation matching the primary values exactly at
every overlap.

  2011  extracted/census-2011/c15-religion-by-age-sex.csv (national + state + district)
  2001  extracted/census-2001/c01-population-by-religion.csv (national + state)
  1991  extracted/census-1991/c09-religion.csv  — RGI C-9 XLSX (NADA cat 35737).
        India figure EXCLUDES J&K (Census not held there in 1991).
  1981  extracted/census-1981/hh15-religion.csv — RGI Paper 3 of 1984
        Household Population by Religion of Head of Household (NADA cat 30879).
        India figure EXCLUDES Assam (Census not held there in 1981).
  1971  extracted/census-1971/religion-summary.csv — RGI Paper 2 of 1972
        Religion Summary table (NADA cat 31626). Six named religions; the
        "all-India" row is derived by summing the six (matches Sachar AT 3.8
        published "All 930" exactly).
  1961  extracted/census-1961/c07-religion.csv — RGI Social and Cultural
        Tables Vol-XIII INDIA Table C-VII (NADA cat 32022).

Emits each religion in OUTPUT_RELIGIONS. Full 6-round trend for all 6
named religions + 'all' for the first time.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_C15_2011 = REPO_ROOT / "extracted" / "census-2011" / "c15-religion-by-age-sex.csv"
L2_C01_2001 = REPO_ROOT / "extracted" / "census-2001" / "c01-population-by-religion.csv"
L2_C09_1991 = REPO_ROOT / "extracted" / "census-1991" / "c09-religion.csv"
L2_HH15_1981 = REPO_ROOT / "extracted" / "census-1981" / "hh15-religion.csv"
L2_REL_1971 = REPO_ROOT / "extracted" / "census-1971" / "religion-summary.csv"
L2_C07_1961 = REPO_ROOT / "extracted" / "census-1961" / "c07-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "sex-ratio.csv"
CANONICALIZER_VERSION = "5.0.1"

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
SRC_1991 = (
    "census-india-1991",
    "sources/census-1991/c09-religion.xlsx",
    "Females / Males * 1000 at total residence from RGI 1991 C-9 Religion table "
    "(XLSX, NADA catalog 35737). India figure excludes J&K (Census not held in 1991).",
)
SRC_1971 = (
    "census-india-1971",
    "sources/census-1971/religion-paper-2-of-1972.pdf",
    "Females / Males * 1000 from the RGI 1972 Religion Paper Summary table "
    "(printed p.xiii / NADA PDF p17; Chandra Sekhar, RGI). Six named religions; "
    "the 'all-India' value here is the sum across the six named (matches RGI's "
    "published all-India 1971 sex ratio of 930).",
)
SRC_1981 = (
    "census-india-1981",
    "sources/census-1981/paper-3-of-1984-hh15-religion.pdf",
    "Females / Males * 1000 from RGI Paper 3 of 1984 (V.S. Verma RGI), Table "
    "HH-15 Household Population by Religion of Head of Household, INDIA T row "
    "spanning PDF pp 23-26. Excludes Assam (Census not held there in 1981).",
)
SRC_1961 = (
    "census-india-1961",
    "sources/census-1961/social-cultural-tables-c07-religion.pdf",
    "Females / Males * 1000 from RGI Social and Cultural Tables Vol-XIII "
    "INDIA Table C-VII Religion (A. Mitra RGI, Census 1961), INDIA T row at "
    "PDF pp 501-502.",
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


def _cells_2011_residence() -> dict[tuple[str, str, str], int]:
    """National urban/rural cells from C-15 2011, All ages, for the residence
    drill-down. Returns {(residence, religion, sex): persons}, residence in
    {urban, rural}, sex in {males, females}."""
    cells: dict[tuple[str, str, str], int] = {}
    with L2_C15_2011.open() as f:
        for row in csv.DictReader(f):
            if row["residence"] not in ("urban", "rural") or row["age_group"] != "All ages":
                continue
            if row["state_code"] != "00" or row["distt_code"] != "000":
                continue
            if row["sex"] not in ("males", "females"):
                continue
            cells[(row["residence"], row["religion"], row["sex"])] = int(row["value"])
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


def _cells_1991() -> dict[tuple[str, str, str, str], int]:
    """National-only: aggregate India row (state_code='01', distt='00', area_level='national')."""
    cells: dict[tuple[str, str, str, str], int] = {}
    with L2_C09_1991.open() as f:
        for row in csv.DictReader(f):
            if row["area_level"] != "national" or row["residence"] != "total":
                continue
            if row["sex"] not in ("males", "females"):
                continue
            cells[("national", "IN", row["religion"], row["sex"])] = int(row["value"])
    return cells


def _cells_1971() -> dict[tuple[str, str, str, str], int]:
    """National-only: six named religions from the Summary table + a derived 'all' (sum)."""
    cells: dict[tuple[str, str, str, str], int] = {}
    sum_males = sum_females = 0
    with L2_REL_1971.open() as f:
        for row in csv.DictReader(f):
            if row["area_level"] != "national" or row["sex"] not in ("males", "females"):
                continue
            value = int(row["value"])
            cells[("national", "IN", row["religion"], row["sex"])] = value
            if row["sex"] == "males":
                sum_males += value
            else:
                sum_females += value
    cells[("national", "IN", "all", "males")] = sum_males
    cells[("national", "IN", "all", "females")] = sum_females
    return cells


def _cells_1981() -> dict[tuple[str, str, str, str], int]:
    """National-only Total-residence: 6 named religions + 'all' explicit."""
    cells: dict[tuple[str, str, str, str], int] = {}
    with L2_HH15_1981.open() as f:
        for row in csv.DictReader(f):
            if row["area_level"] != "national" or row["residence"] != "total":
                continue
            if row["sex"] not in ("males", "females"):
                continue
            cells[("national", "IN", row["religion"], row["sex"])] = int(row["value"])
    return cells


def _cells_1961() -> dict[tuple[str, str, str, str], int]:
    """National-only Total-residence: 6 named religions + 'all' explicit."""
    cells: dict[tuple[str, str, str, str], int] = {}
    with L2_C07_1961.open() as f:
        for row in csv.DictReader(f):
            if row["area_level"] != "national" or row["residence"] != "total":
                continue
            if row["sex"] not in ("males", "females"):
                continue
            cells[("national", "IN", row["religion"], row["sex"])] = int(row["value"])
    return cells


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-sex-ratio-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rounds = [
        (2011, _cells_2011(), SRC_2011),
        (2001, _cells_2001(), SRC_2001),
        (1991, _cells_1991(), SRC_1991),
        (1981, _cells_1981(), SRC_1981),
        (1971, _cells_1971(), SRC_1971),
        (1961, _cells_1961(), SRC_1961),
    ]

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
                    "sex-ratio", level, code, year, religion, "all",
                    ratio, DENOMINATOR, "", "", "",
                    src_id, src_doc, extraction_run, note, "false",
                ])

    # --- 2011 national urban vs rural sex ratio (residence drill-down) ---
    # Feeds the "Urban vs rural" tab; year 2011 (latest census, C-15 All ages).
    res_cells = _cells_2011_residence()
    for res in ("urban", "rural"):
        for religion in OUTPUT_RELIGIONS:
            males = res_cells.get((res, religion, "males"))
            females = res_cells.get((res, religion, "females"))
            if not males or not females:
                continue
            ratio = round(females / males * 1000, 1)
            out_rows.append([
                "sex-ratio", "national", "IN", 2011, religion, res,
                ratio, DENOMINATOR, "", "", "",
                SRC_2011[0], SRC_2011[1], extraction_run,
                f"Females / Males * 1000 at All ages, {res.capitalize()} residence "
                f"(RGI Census 2011 C-15).", "false",
            ])

    out_rows.sort(key=lambda r: (LEVEL_RANK[r[1]], r[2], r[3], RELIGION_RANK[r[4]], r[5]))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "residence", "value", "denominator", "sample_size", "ci_lower", "ci_upper",
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
