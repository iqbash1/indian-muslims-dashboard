"""
L2 -> L3 for the `lfpr-15plus` metric (Labour Force Participation Rate, 15+).

Reads:  extracted/plfs/plfs-2023-24-table48-employment-by-religion.csv
Writes: canonical/lfpr-15plus.csv

PLFS 2023-24 Table 48 (pages 396-400) reports LFPR by religion at all
combinations of residence (rural/urban/total) and sex (male/female/person).
The canonical metric publishes total-residence LFPR per religion AND per sex:
sex='all' is the both-sexes aggregate (PLFS "person"), plus 'male' and 'female'.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "plfs" / "plfs-2023-24-table48-employment-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "lfpr-15plus.csv"
CANONICALIZER_VERSION = "2.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")
# PLFS source sex labels -> canonical sex dimension.
SEX_MAP = {"person": "all", "male": "male", "female": "female"}
SEX_WORD = {"all": "both sexes", "male": "males", "female": "females"}
OUTPUT_SEXES = ("all", "male", "female")


def canonicalize() -> None:
    # by_rel_sex[religion][sex] = LFPR value
    by_rel_sex: dict[str, dict[str, float]] = {}
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if (row["indicator"] == "LFPR" and row["age_cohort"] == "15plus"
                    and row["residence"] == "total"):
                sx = SEX_MAP.get(row["sex"])
                if sx is None:
                    continue
                by_rel_sex.setdefault(row["religion"], {})[sx] = float(row["value"])

    extraction_run = (
        f"canonicalize-lfpr-15plus-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "sex", "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        for religion in OUTPUT_RELIGIONS:
            sexes = by_rel_sex.get(religion)
            if not sexes:
                print(f"  skip {religion}: not in L2")
                continue
            for sx in OUTPUT_SEXES:
                val = sexes.get(sx)
                if val is None:
                    continue
                w.writerow([
                    "lfpr-15plus", "national", "IN", 2023, religion, sx,
                    val, "population_age_15plus", "", "", "",
                    "plfs",
                    "sources/plfs/annual/plfs-annual-report-2023-24.pdf",
                    extraction_run,
                    (f"PLFS 2023-24 Table 48 (page 396-400). Usual status (ps+ss), "
                     f"total residence, {SEX_WORD[sx]}. Year=2023 represents the start "
                     f"of the Jul-2023 to Jun-2024 reference period."),
                    "false",
                ])
                n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    canonicalize()
