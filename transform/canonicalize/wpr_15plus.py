"""
L2 -> L3 for the `wpr-15plus` metric (Worker Population Ratio, 15+).

Reads:  extracted/plfs/plfs-2023-24-table48-employment-by-religion.csv  (2023)
        extracted/plfs/plfs-microdata-2017-24-by-religion.csv          (2017-2022)
Writes: canonical/wpr-15plus.csv

Same structure as lfpr-15plus canonicalizer but filters to indicator=WPR;
the 2017-2022 trend rows come from the unit-level microdata (see
_plfs_microdata.py).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

from _plfs_microdata import eus_trend_rows, trend_rows

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "plfs" / "plfs-2023-24-table48-employment-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "wpr-15plus.csv"
CANONICALIZER_VERSION = "2.1.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")
SEX_MAP = {"person": "all", "male": "male", "female": "female"}
SEX_WORD = {"all": "both sexes", "male": "males", "female": "females"}
OUTPUT_SEXES = ("all", "male", "female")


def canonicalize() -> None:
    RES_MAP = {"total": "all", "rural": "rural", "urban": "urban"}
    cube: dict[tuple[str, str, str], float] = {}  # (religion, sex, residence) -> value
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["indicator"] != "WPR" or row["age_cohort"] != "15plus":
                continue
            sx = SEX_MAP.get(row["sex"])
            res = RES_MAP.get(row["residence"])
            if sx is None or res is None:
                continue
            cube[(row["religion"], sx, res)] = float(row["value"])

    extraction_run = (
        f"canonicalize-wpr-15plus-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "sex", "residence", "value", "denominator", "sample_size", "ci_lower",
            "ci_upper", "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}
        for religion in OUTPUT_RELIGIONS:
            for sx in OUTPUT_SEXES:
                for res in ("all", "urban", "rural"):
                    val = cube.get((religion, sx, res))
                    if val is None:
                        continue
                    w.writerow([
                        "wpr-15plus", "national", "IN", 2023, religion, sx, res,
                        val, "population_age_15plus", "", "", "",
                        "plfs",
                        "sources/plfs/annual/plfs-annual-report-2023-24.pdf",
                        extraction_run,
                        (f"PLFS 2023-24 Table 48 (page 396-400). Usual status (ps+ss), "
                         f"{RES_WORD[res]}, {SEX_WORD[sx]}."),
                        "false",
                    ])
                    n_rows += 1

        # over-time 2017-2022 from the unit-level microdata (source plfs-microdata)
        for mrow in trend_rows("wpr-15plus", "wpr", "population_age_15plus",
                               "worker population ratio", extraction_run):
            w.writerow(mrow)
            n_rows += 1
        for mrow in eus_trend_rows("wpr-15plus", "wpr", "population_age_15plus",
                                   "worker population ratio", extraction_run):
            w.writerow(mrow)
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    canonicalize()
