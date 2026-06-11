"""Shared helper: PLFS microdata trend rows for the employment metrics.

The annual-report PDFs publish the 15+ by-religion detail only for their own
year, so the over-time rows (2017-2022) of lfpr-15plus / wpr-15plus /
salaried-share come from the unit-level microdata instead (7 rounds via the
MoSPI NADA API; see nada/plfs-layout-map.md and sources/nada/plfs-<round>/).
The 2023 point stays sourced from the published Table 48/49 (source `plfs`),
which the microdata reproduces within 0.2pp, so the series is seamless.

Reads extracted/plfs/plfs-microdata-2017-24-by-religion.csv (written by
transform/plfs/extract_microdata_trends.py, whose validation gates assert the
all-India figures match every round's published report to 0.1).
"""
from __future__ import annotations

import csv
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MICRO_L2 = REPO_ROOT / "extracted" / "plfs" / "plfs-microdata-2017-24-by-religion.csv"

# religions the published 2023-24 tables also carry, so every trend line has
# a current-year anchor point
RELIGIONS = ("muslim", "hindu", "christian", "sikh", "all")
TREND_YEARS = range(2017, 2023)   # 2023 comes from the published table instead

ZIP = {
    "2017-18": "CSV_PLFS_July2017_June2018.zip",
    "2018-19": "PLFS_2018_19_CSV.zip",
    "2019-20": "CSV_PLFS_19_20.zip",
    "2020-21": "CSV_Unit_level_data_PLFS_July2020_June2021.zip",
    "2021-22": "PLFS_Data_2021-22_CSV.zip",
    "2022-23": "Data_in_CSV.zip",
}

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}
SEX_WORD = {"all": "both sexes", "male": "males", "female": "females"}


def trend_rows(metric_id: str, field: str, denominator: str, what: str,
               extraction_run: str, *, sexes=("all", "male", "female"),
               residences=("all", "urban", "rural")) -> list[list]:
    """Canonical rows (17-col schema with sex) for years 2017-2022 from the
    microdata L2. `field` = lfpr | wpr | ur | salaried_share; `what` is the
    indicator phrase used in the methodology note."""
    rows = []
    with MICRO_L2.open() as f:
        for r in csv.DictReader(f):
            year = int(r["year"])
            if year not in TREND_YEARS:
                continue
            if (r["religion"] not in RELIGIONS or r["sex"] not in sexes
                    or r["residence"] not in residences):
                continue
            val = r[field]
            if not val:
                continue
            rnd = r["round"]
            note = (
                f"Computed from PLFS {rnd} unit-level microdata (first-visit person "
                f"file, usual status ps+ss, age 15+, {RES_WORD[r['residence']]}, "
                f"{SEX_WORD[r['sex']]}): {what}. Weight = MULT/100 (or /200 when "
                f"NSS!=NSC) / NO_QTR; household religion joined from the household "
                f"file. The run reproduces the round's published all-India "
                f"LFPR/WPR/UR to 0.1. Pulled via the MoSPI NADA API; zip sha256 in "
                f"sources/nada/plfs-{rnd}/. NSO unit-data rider: religion is "
                f"self-reported and the survey is designed for labour-force "
                f"estimation, so religion figures are indicative (no sub-state "
                f"estimates). Year={year} is the start of the Jul-{year} to "
                f"Jun-{year+1} reference period."
            )
            rows.append([
                metric_id, "national", "IN", year, r["religion"], r["sex"],
                r["residence"], round(float(val), 1), denominator,
                r["n_15plus"], "", "",
                "plfs-microdata", f"sources/nada/plfs-{rnd}/{ZIP[rnd]}",
                extraction_run, note, "false",
            ])
    return rows
