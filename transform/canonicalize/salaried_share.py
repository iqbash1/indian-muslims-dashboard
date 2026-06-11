"""
L2 -> L3 for the `salaried-share` metric.

Reads:  extracted/plfs/plfs-2023-24-table49-employment-status-by-religion.csv  (2023)
        extracted/plfs/plfs-microdata-2017-24-by-religion.csv                  (2017-2022)
Writes: canonical/salaried-share.csv

Publishes the regular wage/salary share of all workers by religion, from PLFS
2023-24 Table 49 (the 2023 point) plus the 2017-2022 trend computed from the
unit-level microdata (see _plfs_microdata.py).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

from _plfs_microdata import eus_trend_rows, trend_rows

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "plfs" / "plfs-2023-24-table49-employment-status-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "salaried-share.csv"
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
            if row["metric"] != "regular_wage_salary":
                continue
            sx = SEX_MAP.get(row["sex"])
            res = RES_MAP.get(row["residence"])
            if sx is None or res is None:
                continue
            cube[(row["religion"], sx, res)] = float(row["value"])

    extraction_run = (
        f"canonicalize-salaried-share-v{CANONICALIZER_VERSION}-"
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
                        "salaried-share", "national", "IN", 2023, religion, sx, res,
                        val, "all_workers_usual_status_ps_ss", "", "", "",
                        "plfs",
                        "sources/plfs/annual/plfs-annual-report-2023-24.pdf",
                        extraction_run,
                        (f"PLFS 2023-24 Table 49 (pages 401-402). Share of workers in "
                         f"'regular wage/salary' employment, {RES_WORD[res]}, {SEX_WORD[sx]}. "
                         f"Other categories: self-employed, casual labour. Reference "
                         f"period: Jul 2023 - Jun 2024."),
                        "false",
                    ])
                    n_rows += 1

        # over-time 2017-2022 from the unit-level microdata (source plfs-microdata)
        for mrow in trend_rows("salaried-share", "salaried_share",
                               "all_workers_usual_status_ps_ss",
                               "share of workers in regular wage/salaried employment",
                               extraction_run):
            w.writerow(mrow)
            n_rows += 1
        for mrow in eus_trend_rows("salaried-share", "salaried_share",
                                   "all_workers_usual_status_ps_ss",
                                   "share of workers in regular wage/salaried employment",
                                   extraction_run):
            w.writerow(mrow)
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    for res in ("all", "urban", "rural"):
        m = cube.get(("muslim", "all", res))
        a = cube.get(("all", "all", res))
        print(f"  {res}: Muslim {m}% vs all {a}%")


if __name__ == "__main__":
    canonicalize()
