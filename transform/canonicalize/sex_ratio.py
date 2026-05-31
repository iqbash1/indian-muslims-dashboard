"""
L2 -> L3 for the `sex-ratio` metric (females per 1000 males).

Decennial series, one canonical row per (year x geography x religion):
  sex_ratio = females / males * 1000   at all ages, total residence

Sources (all PRIMARY where possible; identical all-ages / total-residence
definition across rounds — verified table-invariant at 2011 where C-01
and C-15 reproduce the same numbers):

  2011  PRIMARY  extracted/census-2011/c15-religion-by-age-sex.csv
        national + state + district
  2001  PRIMARY  extracted/census-2001/c01-population-by-religion.csv
        national + state (all-India 2001 C-1 file carries no districts)
  1991  PRIMARY  extracted/census-1991/c09-religion.csv
        national row, all six religions + "all" — derived from the RGI
        1991 C-9 Religion table (XLSX, NADA catalog 35737). Excludes J&K
        (Census not held there in 1991). Cross-validated against Sachar
        Committee 2006 AT 3.8 (Muslim 930, All 927) — matches exactly.
  1971  PRIMARY  extracted/census-1971/religion-summary.csv
        national row, six named religions (Hindu / Muslim / Christian /
        Sikh / Buddhist / Jain) — parsed from the RGI 1972 Religion Paper
        Summary table (Paper 2 of 1972, Series-1, India, by Chandra Sekhar
        RGI; NADA catalog 31626). The "all-India" row is derived by summing
        the six named (Sachar AT 3.8's published "All 930" matches the
        sum). "Other religions and persuasions" not in the Summary.
  1961, 1981  SECONDARY (manual entry) — Sachar Committee 2006 AT 3.8 (p301),
        compiled from RGI 1961 + 1984 publications. The original 1961 + 1981
        RGI religion volumes carrying full sex-by-religion breakdowns are
        not on NADA, so Sachar's compilation is the closest addressable
        source. Sachar AT 3.8 provides Muslim + All-India only (no Hindu /
        Christian / Sikh / Buddhist / Jain decadal for these years). Cross-
        validated at 2001 where Sachar's "All 933, Muslim 936" matches the
        primary C-01 derivation to <0.1pp.

Emits each religion in OUTPUT_RELIGIONS. The 1961-2011 trend now spans:
  - 6 rounds for Muslim + All-India (1961, 1971, 1981, 1991, 2001, 2011)
  - 4 rounds for Hindu / Christian / Sikh / Buddhist / Jain (1971, 1991,
    2001, 2011 — gaps at 1961 and 1981 because RGI's per-decade religion
    volumes for those years aren't accessible to this pipeline)
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_C15_2011 = REPO_ROOT / "extracted" / "census-2011" / "c15-religion-by-age-sex.csv"
L2_C01_2001 = REPO_ROOT / "extracted" / "census-2001" / "c01-population-by-religion.csv"
L2_C09_1991 = REPO_ROOT / "extracted" / "census-1991" / "c09-religion.csv"
L2_REL_1971 = REPO_ROOT / "extracted" / "census-1971" / "religion-summary.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "sex-ratio.csv"
CANONICALIZER_VERSION = "4.0.0"

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

# SECONDARY (manual entry). Sachar Committee Report 2006, Appendix Table 3.8
# (p301), national row only — Muslim + All. Compiled from RGI 1961 & 1984
# decadal religion publications. Used as fallback ONLY for 1961 and 1981 where
# the original RGI religion volumes are not on NADA.
DECADAL_SECONDARY = {
    1961: {"muslim": 935, "all": 941},
    1981: {"muslim": 937, "all": 934},  # 1981 excludes Assam (RGI did not enumerate)
}
COVERAGE = {
    1981: " 1981 excludes Assam (RGI did not enumerate).",
}
SEC_NOTE = (
    "SECONDARY (manual entry): Sachar Committee Report 2006, Appendix Table 3.8 "
    "(p301), compiled from RGI 1961 & 1984 decadal religion publications. Used "
    "only for 1961 + 1981 where the underlying RGI religion volumes are not on "
    "NADA. Cross-validated at 2001 against this repo's primary C-01 to <0.1pp."
)
SRC_DECADAL_SECONDARY = (
    "sachar-committee-2006",
    "sources/sachar-committee-2006/sachar-comm-report-india-2006.pdf",
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


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-sex-ratio-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rounds = [
        (2011, _cells_2011(), SRC_2011),
        (2001, _cells_2001(), SRC_2001),
        (1991, _cells_1991(), SRC_1991),
        (1971, _cells_1971(), SRC_1971),
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
                    "sex-ratio", level, code, year, religion,
                    ratio, DENOMINATOR, "", "", "",
                    src_id, src_doc, extraction_run, note, "false",
                ])

    # SECONDARY: Sachar AT 3.8 national-level Muslim + All for 1961 + 1981
    # (years where the primary RGI religion volume isn't on NADA).
    sec_src_id, sec_src_doc = SRC_DECADAL_SECONDARY
    for year, shares in DECADAL_SECONDARY.items():
        note = SEC_NOTE + COVERAGE.get(year, "")
        for religion, ratio in shares.items():
            out_rows.append([
                "sex-ratio", "national", "IN", year, religion,
                float(ratio), DENOMINATOR, "", "", "",
                sec_src_id, sec_src_doc, extraction_run, note, "false",
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
