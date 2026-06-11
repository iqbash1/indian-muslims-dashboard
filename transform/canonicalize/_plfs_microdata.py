"""Shared helper: PLFS + EUS microdata trend rows for the employment metrics.

The annual-report PDFs publish the 15+ by-religion detail only for their own
year, so the over-time rows (2017-2022) of lfpr-15plus / wpr-15plus /
salaried-share come from the unit-level microdata instead (7 rounds via the
MoSPI NADA API; see nada/plfs-layout-map.md and sources/nada/plfs-<round>/).
The 2023 point stays sourced from the published Table 48/49 (source `plfs`),
which the microdata reproduces within 0.2pp, so the series is seamless.

The PRE-PLFS history (2004, 2009, 2011) comes from the three quinquennial
EUS rounds' unit data via eus_trend_rows (see nada/eus-layout-map.md and
transform/eus/extract_microdata_trends.py, whose gates reproduce the
published by-religion statements of NSS Reports 568/552). EUS and PLFS are
NOT strictly comparable (sampling design, CAPI, rotation panel), so the
first PLFS round's rows carry break_flag=true - the same convention as
mpce's Sachar->HCES break, rendered as the dashed Muslim line.

Reads extracted/plfs/plfs-microdata-2017-24-by-religion.csv (written by
transform/plfs/extract_microdata_trends.py, whose validation gates assert the
all-India figures match every round's published report to 0.1) and
extracted/eus/eus-microdata-2004-12-by-religion.csv.
"""
from __future__ import annotations

import csv
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MICRO_L2 = REPO_ROOT / "extracted" / "plfs" / "plfs-microdata-2017-24-by-religion.csv"
EUS_L2 = REPO_ROOT / "extracted" / "eus" / "eus-microdata-2004-12-by-religion.csv"

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
    "2023-24": "CSV_data_PLFS_2023_2024.zip",
}

EUS_ZIP = {
    "2004-05": ("eus-2004-05", "Emp_Unemp_2004_2005_CSV.zip", "61st"),
    "2009-10": ("eus-2009-10", "Emp_Unemp_2009_2010_CSV.zip", "66th"),
    "2011-12": ("eus-2011-12", "U_M_2011_2012_CSV.zip", "68th"),
}

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}
SEX_WORD = {"all": "both sexes", "male": "males", "female": "females"}


def trend_rows(metric_id: str, field: str, denominator: str, what: str,
               extraction_run: str, *, sexes=("all", "male", "female"),
               residences=("all", "urban", "rural"),
               years=TREND_YEARS) -> list[list]:
    """Canonical rows (17-col schema with sex) for the given years from the
    microdata L2. `field` = lfpr | wpr | ur | salaried_share; `what` is the
    indicator phrase used in the methodology note. Default years stop at 2022
    (2023 comes from the published table); unemployment-rate passes all seven
    because the published tables don't break UR down by religion at all."""
    rows = []
    with MICRO_L2.open() as f:
        for r in csv.DictReader(f):
            year = int(r["year"])
            if year not in years:
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
                extraction_run, note,
                # 2017-18 is the first PLFS round after the EUS era: the
                # design break (new sampling, CAPI, rotation panel) is
                # flagged here, mpce's Sachar->HCES convention
                "true" if year == 2017 else "false",
            ])
    return rows


def eus_trend_rows(metric_id: str, field: str, denominator: str, what: str,
                   extraction_run: str, *, sexes=("all", "male", "female"),
                   residences=("all", "urban", "rural")) -> list[list]:
    """Canonical rows for the pre-PLFS EUS history (2004, 2009, 2011) from
    the EUS microdata L2; same 17-col schema as trend_rows. The 64th round
    (2007-08) is absent by design: NSSO published no by-religion employment
    tables for that thin annual round, so it cannot be gate-validated."""
    rows = []
    with EUS_L2.open() as f:
        for r in csv.DictReader(f):
            if (r["religion"] not in RELIGIONS or r["sex"] not in sexes
                    or r["residence"] not in residences):
                continue
            val = r[field]
            if not val:
                continue
            rnd = r["round"]
            year = int(r["year"])
            dirname, zipname, nss_round = EUS_ZIP[rnd]
            note = (
                f"Computed from NSS {nss_round}-round Employment & Unemployment "
                f"Survey {rnd} unit-level microdata (usual status ps+ss, age "
                f"15+, {RES_WORD[r['residence']]}, {SEX_WORD[r['sex']]}): "
                f"{what}. Weighted by the survey's combined multiplier; "
                f"household religion joined from the household-characteristics "
                f"block. The run reproduces the published all-ages by-religion "
                f"LFPR/WPR/UR of NSS Reports 568/552 cell-for-cell at printed "
                f"precision. Pulled via the MoSPI NADA API; zip sha256 in "
                f"sources/nada/{dirname}/. EUS and PLFS designs are not "
                f"strictly comparable (the break is flagged on the first PLFS "
                f"round). NSO unit-data rider: religion is self-reported and "
                f"the survey is designed for labour-force estimation, so "
                f"religion figures are indicative (no sub-state estimates). "
                f"Year={year} is the start of the Jul-{year} to Jun-{year+1} "
                f"reference period."
            )
            rows.append([
                metric_id, "national", "IN", year, r["religion"], r["sex"],
                r["residence"], round(float(val), 1), denominator,
                r["n_15plus"], "", "",
                "eus-microdata", f"sources/nada/{dirname}/{zipname}",
                extraction_run, note, "false",
            ])
    return rows
