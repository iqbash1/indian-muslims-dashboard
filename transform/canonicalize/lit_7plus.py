"""
L2 -> L3 for the `lit-7plus` metric (Literacy rate, age 7+).

Reads:  extracted/census-2011/c09-education-by-religion.csv
Writes: canonical/lit-7plus.csv

Per (geography x religion):
  total_7plus    = total_population[age='Total']
                 - total_population[age='0-6']
                 - total_population[age='Age not stated']
  literate_7plus = literate[age='Total']
                 - literate[age='Age not stated']
  rate           = literate_7plus / total_7plus * 100

Subtracting "Age not stated" matches the published Census definition; without
it our national rate runs ~1pp low (72.98% vs the published 74.04%).
Under-7 individuals are all illiterate by Census convention, so the literate
numerator already represents 7+ literates before the Age-not-stated removal.

Emits one row per geography for each religion in (muslim, hindu, all).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "census-2011" / "c09-education-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "lit-7plus.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "all")


def geography(state_code: str, area_name: str) -> tuple[str, str]:
    if state_code == "00":
        return "national", "IN"
    return "state", f"IN-S{state_code}"


def canonicalize() -> None:
    # Aggregate to (level, code, religion) -> {measure_age: value}
    # Only care about residence=total, sex=persons.
    cells: dict[tuple[str, str, str, str, str], int] = {}

    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["residence"] != "total" or row["sex"] != "persons":
                continue
            if row["age_group"] not in ("Total", "0-6", "Age not stated"):
                continue
            if row["measure"] not in ("total_population", "literate"):
                continue
            level, code = geography(row["state_code"], row["area_name"])
            key = (level, code, row["religion"], row["measure"], row["age_group"])
            cells[key] = int(row["value"])

    geographies: set[tuple[str, str]] = {(lv, cd) for (lv, cd, _, _, _) in cells}

    extraction_run = (
        f"canonicalize-lit-7plus-v{CANONICALIZER_VERSION}-"
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
                total_all = cells.get((level, code, religion, "total_population", "Total"))
                total_06 = cells.get((level, code, religion, "total_population", "0-6"))
                total_nostate = cells.get(
                    (level, code, religion, "total_population", "Age not stated"), 0
                )
                literate_all = cells.get((level, code, religion, "literate", "Total"))
                literate_nostate = cells.get(
                    (level, code, religion, "literate", "Age not stated"), 0
                )
                if None in (total_all, total_06, literate_all):
                    n_missing += 1
                    continue
                total_7plus = total_all - total_06 - total_nostate
                literate_7plus = literate_all - literate_nostate
                if total_7plus <= 0:
                    n_missing += 1
                    continue
                rate = round(literate_7plus / total_7plus * 100, 4)
                w.writerow([
                    "lit-7plus", level, code, 2011, religion,
                    rate, "population_age_7_plus_excluding_age_not_stated", "", "", "",
                    "census-india-2011",
                    "sources/census-2011/c-series/c09-education-by-religion.xlsx",
                    extraction_run,
                    "(Literate - Literate_age_not_stated) / (Total - 0-6 - Age_not_stated) * 100. Matches published Census 2011 literacy definition.",
                    "false",
                ])
                n_rows += 1

    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({n_rows} rows; {n_missing} (geography x religion) cells incomplete)"
    )


if __name__ == "__main__":
    canonicalize()
