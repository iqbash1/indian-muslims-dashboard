"""
L2 -> L3 for the `sex-ratio` metric (females per 1000 males).

Reads:  extracted/census-2011/c15-religion-by-age-sex.csv
Writes: canonical/sex-ratio.csv

Per (geography x religion):
  sex_ratio = females / males * 1000   at age='All ages', residence='total'

Emits one row per geography for each religion in (muslim, hindu, all).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "census-2011" / "c15-religion-by-age-sex.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "sex-ratio.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")


def geography(state_code: str, distt_code: str) -> tuple[str, str]:
    if state_code == "00" and distt_code == "000":
        return "national", "IN"
    if distt_code == "000":
        return "state", f"IN-S{state_code}"
    return "district", f"IN-S{state_code}-D{distt_code}"


def canonicalize() -> None:
    cells: dict[tuple[str, str, str, str], int] = {}

    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["residence"] != "total" or row["age_group"] != "All ages":
                continue
            if row["sex"] not in ("males", "females"):
                continue
            level, code = geography(row["state_code"], row["distt_code"])
            cells[(level, code, row["religion"], row["sex"])] = int(row["value"])

    geographies = {(lv, cd) for (lv, cd, _, _) in cells}

    extraction_run = (
        f"canonicalize-sex-ratio-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    n_missing = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])

        for (level, code) in sorted(geographies):
            for religion in OUTPUT_RELIGIONS:
                males = cells.get((level, code, religion, "males"))
                females = cells.get((level, code, religion, "females"))
                if not males or not females:
                    n_missing += 1
                    continue
                ratio = round(females / males * 1000, 1)
                w.writerow([
                    "sex-ratio", level, code, 2011, religion,
                    ratio, "females_per_1000_males_total_residence_all_ages", "", "", "",
                    "census-india-2011",
                    "sources/census-2011/c-series/c15-religion-by-age-sex.xlsx",
                    extraction_run,
                    "Females / Males * 1000 at All ages, Total residence.",
                    "false",
                ])
                n_rows += 1

    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({n_rows} rows; {n_missing} (geography x religion) cells incomplete)"
    )


if __name__ == "__main__":
    canonicalize()
