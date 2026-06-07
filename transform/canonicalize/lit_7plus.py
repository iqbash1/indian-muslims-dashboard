"""
L2 -> L3 for the `lit-7plus` metric (Literacy rate, age 7+).

Decennial series, one canonical row per (year x geography x religion):
  total_7plus    = total_population[Total] - total_population[0-6]
                 - total_population[Age not stated]
  literate_7plus = literate[Total] - literate[Age not stated]
  rate           = literate_7plus / total_7plus * 100

Subtracting "Age not stated" matches the published Census literacy definition
(without it the national rate runs ~1pp low). Under-7s are illiterate by Census
convention, so the literate numerator is already 7+ before that removal. The
2001 and 2011 C-9 tables use the identical definition -> a clean decennial trend
(no methodology break).

Sources (same C-9 "education by religious community, age 7+" table family):
  2011  extracted/census-2011/c09-education-by-religion.csv   (national + state)
  2001  extracted/census-2001/c09-education-by-religion.csv   (national + state)

Publishes the six named communities + the residual "other" + the "all" total.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_2011 = REPO_ROOT / "extracted" / "census-2011" / "c09-education-by-religion.csv"
L2_2001 = REPO_ROOT / "extracted" / "census-2001" / "c09-education-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "lit-7plus.csv"
CANONICALIZER_VERSION = "3.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")
DENOMINATOR = "population_age_7_plus_excluding_age_not_stated"

SRC_2011 = (
    "census-india-2011",
    "sources/census-2011/c-series/c09-education-by-religion.xlsx",
    "(Literate - Literate_age_not_stated) / (Total - 0-6 - Age_not_stated) * 100. "
    "Matches published Census 2011 literacy definition.",
)
SRC_2001 = (
    "census-india-2001",
    "sources/census-2001/c-series/c09-education-by-religion.xls",
    "(Literate - Literate_age_not_stated) / (Total - 0-6 - Age_not_stated) * 100. "
    "Matches published Census 2001 literacy definition (same C-9 table family as 2011).",
)

LEVEL_RANK = {"national": 0, "state": 1}
RELIGION_RANK = {r: i for i, r in enumerate(OUTPUT_RELIGIONS)}
# Census C-09 sex labels -> canonical sex dimension. Gender is emitted at the
# national level only (states stay both-sexes; the by-sex card view is national).
SEX_MAP = {"persons": "all", "males": "male", "females": "female"}
SEX_RANK = {"all": 0, "male": 1, "female": 2}
OUTPUT_SEXES = ("all", "male", "female")


def _geo(state_code: str) -> tuple[str, str]:
    return ("national", "IN") if state_code == "00" else ("state", f"IN-S{state_code}")


def _cells(l2_path: pathlib.Path) -> dict[tuple[str, str, str, str, str, str], int]:
    """(level, code, religion, sex, measure, age_group) -> value, residence=total.
    sex is canonicalised: persons->all, males->male, females->female."""
    cells: dict[tuple[str, str, str, str, str, str], int] = {}
    with l2_path.open() as f:
        for row in csv.DictReader(f):
            if row["residence"] != "total":
                continue
            sx = SEX_MAP.get(row["sex"])
            if sx is None:
                continue
            if row["age_group"] not in ("Total", "0-6", "Age not stated"):
                continue
            if row["measure"] not in ("total_population", "literate"):
                continue
            level, code = _geo(row["state_code"])
            cells[(level, code, row["religion"], sx, row["measure"], row["age_group"])] = int(row["value"])
    return cells


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-lit-7plus-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rounds = [(2011, _cells(L2_2011), SRC_2011), (2001, _cells(L2_2001), SRC_2001)]

    out_rows: list[list] = []
    n_missing = 0
    for year, cells, (src_id, src_doc, note) in rounds:
        geographies = {(lv, cd) for (lv, cd, _, _, _, _) in cells}
        for (level, code) in geographies:
            for religion in OUTPUT_RELIGIONS:
                for sx in OUTPUT_SEXES:
                    # National-only gender; states stay both-sexes (sex=all).
                    if level != "national" and sx != "all":
                        continue
                    total_all = cells.get((level, code, religion, sx, "total_population", "Total"))
                    total_06 = cells.get((level, code, religion, sx, "total_population", "0-6"))
                    total_nostate = cells.get((level, code, religion, sx, "total_population", "Age not stated"), 0)
                    literate_all = cells.get((level, code, religion, sx, "literate", "Total"))
                    literate_nostate = cells.get((level, code, religion, sx, "literate", "Age not stated"), 0)
                    if None in (total_all, total_06, literate_all):
                        n_missing += 1
                        continue
                    total_7plus = total_all - total_06 - total_nostate
                    literate_7plus = literate_all - literate_nostate
                    if total_7plus <= 0:
                        n_missing += 1
                        continue
                    rate = round(literate_7plus / total_7plus * 100, 4)
                    out_rows.append([
                        "lit-7plus", level, code, year, religion, sx,
                        rate, DENOMINATOR, "", "", "",
                        src_id, src_doc, extraction_run, note, "false",
                    ])

    out_rows.sort(key=lambda r: (LEVEL_RANK[r[1]], r[2], r[3], RELIGION_RANK[r[4]], SEX_RANK[r[5]]))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "sex", "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        w.writerows(out_rows)

    years = sorted({r[3] for r in out_rows})
    n_gender = sum(1 for r in out_rows if r[5] != "all")
    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({len(out_rows)} rows; {n_gender} male/female; years {years}; {n_missing} incomplete cells)"
    )


if __name__ == "__main__":
    canonicalize()
