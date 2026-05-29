"""
L2 -> L3 for the `women-anemia` metric (any anaemia, women 15-49).

Reads:  extracted/nfhs-5/nfhs-5-table10231-women-anaemia-by-religion.csv
Writes: canonical/women-anemia.csv

NFHS-5 Table 10.23.1 reports total-residence women's anaemia by religion
directly — no weighting needed. The "any_anaemia" metric is haemoglobin
<12.0 g/dl (non-pregnant) or <11.0 g/dl (pregnant), altitude-adjusted.

Emits one row per religion at national level.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table10231-women-anaemia-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "women-anemia.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")


def canonicalize() -> None:
    by_religion: dict[str, dict] = {}
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["metric"] != "any_anaemia":
                continue
            by_religion[row["religion"]] = {
                "value": float(row["value"]),
                "n": int(row["n_women"]),
                "small": row["small_sample"] == "true",
            }

    extraction_run = (
        f"canonicalize-women-anemia-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        for religion in OUTPUT_RELIGIONS:
            d = by_religion.get(religion)
            if d is None:
                print(f"  skip {religion}: not in L2")
                continue
            w.writerow([
                "women-anemia", "national", "IN", 2020, religion,
                d["value"], "women_age_15_49_tested", d["n"], "", "",
                "nfhs-5",
                "sources/nfhs-5/reports/india-report-fr375.pdf",
                extraction_run,
                ("NFHS-5 Table 10.23.1 — any anaemia (haemoglobin <12.0 g/dl "
                 "non-pregnant, <11.0 g/dl pregnant), altitude-adjusted. "
                 "Total residence, national. Year=2020 represents the midpoint "
                 "of NFHS-5 fieldwork (2019-21)."),
                "false",
            ])
            n_rows += 1

        # ---- Earlier rounds for the time series (NFHS-4 2015, NFHS-3 2005) ----
        # break_flag=true: cross-round anaemia comparability is limited
        # (blood-draw method / cut-offs), so the trend line is not drawn across it.
        for year, sid, sdoc, ext in (
            (2015, "nfhs-4", "sources/nfhs-4/reports/india-report-fr339.pdf",
             "extracted/nfhs-4/nfhs-4-table10211-women-anaemia-by-religion.csv"),
            (2005, "nfhs-3", "sources/nfhs-3/reports/india-report-frind3.pdf",
             "extracted/nfhs-3/nfhs-3-table10241-women-anaemia-by-religion.csv"),
        ):
            p = REPO_ROOT / ext
            if not p.exists():
                continue
            with p.open() as ef:
                for r in csv.DictReader(ef):
                    if r["metric"] != "any_anaemia_pct":
                        continue
                    w.writerow([
                        "women-anemia", "national", "IN", year, r["religion"],
                        round(float(r["value"]), 2), "women_age_15_49_tested",
                        "", "", "", sid, sdoc, extraction_run,
                        (f"NFHS Table 10.21.1/10.24.1, any anaemia in women 15-49 by "
                         f"religion. Cross-round comparability limited (method/cut-offs) "
                         f"— treat as methodology break. Year={year}."),
                        "true",
                    ])
                    n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    canonicalize()
