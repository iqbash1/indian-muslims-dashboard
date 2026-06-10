"""
L2 -> L3 for the `muslim-higher-ed-enrolment` metric.

Reads:  extracted/aishe/aishe-2021-22-table15-state-minority-enrolment.csv  (year 2021)
        extracted/aishe/aishe-2020-21-table15-state-minority-enrolment.csv  (year 2020)
Writes: canonical/muslim-higher-ed-enrolment.csv

Maps AISHE state names to canonical state codes via transform/geography_codes.py
and emits one row per (year x geography x sex) (religion=muslim, value=muslim_total).
Two AISHE rounds give an over-time series; year=2020 represents academic year
2020-21, year=2021 represents 2021-22. The 2020-21 L2 also carries West Bengal
(recovered via the character-level de-interleave; the 2021-22 text layer dropped
it), so the 2020 state breakdown is one state more complete than 2021.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from geography_codes import normalize_state_name

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "muslim-higher-ed-enrolment.csv"
CANONICALIZER_VERSION = "3.0.0"

# (year, academic-year label, L2 path). Newest first; the build sorts by year.
ROUNDS = [
    (2021, "2021-22", REPO_ROOT / "extracted" / "aishe" / "aishe-2021-22-table15-state-minority-enrolment.csv"),
    (2020, "2020-21", REPO_ROOT / "extracted" / "aishe" / "aishe-2020-21-table15-state-minority-enrolment.csv"),
]

# AISHE table-15 columns -> canonical sex dimension. Gender at national level
# only (states stay both-sexes / sex=all; the by-sex card view is national).
SEX_COLS = {"all": "muslim_total", "male": "muslim_male", "female": "muslim_female"}
SEX_WORD = {"all": "both sexes", "male": "males", "female": "females"}
OUTPUT_SEXES = ("all", "male", "female")


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-muslim-higher-ed-enrolment-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_rows: list[list] = []
    n_unmapped = 0
    for year, ay_label, l2_path in ROUNDS:
        for row in csv.DictReader(l2_path.open()):
            state_name = row["state_name"]
            geo_code = normalize_state_name(state_name)
            if geo_code is None:
                print(f"  WARN unmapped state ({ay_label}): {state_name!r}")
                n_unmapped += 1
                continue
            level = "national" if geo_code == "IN" else "state"
            for sx in OUTPUT_SEXES:
                if level != "national" and sx != "all":
                    continue
                raw = row.get(SEX_COLS[sx])
                if raw in (None, ""):
                    continue
                note = (f"AISHE {ay_label} Table 15 Muslim Minority"
                        f"{'' if sx == 'all' else ' ' + SEX_WORD[sx]} enrolment. "
                        f"Year={year} represents the academic year {ay_label}.")
                out_rows.append([
                    "muslim-higher-ed-enrolment", level, geo_code, year, "muslim", sx,
                    int(raw), "students", "", "", "",
                    "aishe", row["source_document"], extraction_run, note, "false",
                ])

    # national before state, newest year first, male/female after both-sexes.
    sex_rank = {"all": 0, "male": 1, "female": 2}
    level_rank = {"national": 0, "state": 1}
    out_rows.sort(key=lambda r: (level_rank[r[1]], -int(r[3]), r[2], sex_rank[r[5]]))

    with OUTPUT_PATH.open("w", newline="") as fout:
        w = csv.writer(fout)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "sex", "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        w.writerows(out_rows)

    print(
        f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} "
        f"({len(out_rows)} rows; {n_unmapped} unmapped; years {sorted({r[3] for r in out_rows})})"
    )


if __name__ == "__main__":
    canonicalize()
