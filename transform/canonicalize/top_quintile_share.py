"""
L2 -> L3 for the `top-quintile-share` metric.

Reads:  extracted/hces/hces-2023-24-quintile-by-religion.csv
Writes: canonical/top-quintile-share.csv

Of all persons in a community, the share living in households whose MPCE is in
the TOP 20% of the national person-weighted distribution (HCES 2023-24
microdata; cuts Rs 2,903 / 3,677 / 4,632 / 6,302). In a proportional world
every community sits at 20. The L2 (extract_quintile_2023_24_by_religion.py)
carries all five quintile shares; this metric cards Q5, with the Q1 near-parity
counterpoint stated in the methodology note. Residence rows are computed
against the SAME national cuts (so "urban" = share of the community's urban
population reaching the national top fifth).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "hces" / "hces-2023-24-quintile-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "top-quintile-share.csv"
CANONICALIZER_VERSION = "1.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}

NOTE = (
    "Computed from HCES 2023-24 unit-level microdata (NSO; 2.61 lakh households) "
    "pulled via the MoSPI NADA API: share of the community's population ({res}) "
    "living in households whose MPCE falls in the top fifth of the national "
    "person-weighted MPCE distribution (quintile cuts Rs 2,903 / 3,677 / 4,632 / "
    "6,302; every all-India quintile share = 20.0 by construction, the built-in "
    "validation). The counterpoint: Muslims sit at PAR in the bottom fifth (20.5 "
    "vs 20.0) - the distribution is compressed below the top, not crowded at the "
    "bottom. Same MPCE machinery as the mpce metric (reproduces the published "
    "national MPCE within ~2%). NSO unit-data rider: religion is self-reported "
    "and the survey is designed for MPCE estimation, so the religion split is "
    "indicative and no sub-state estimate is made. Year=2023 = HCES 2023-24."
)


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-top-quintile-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = []
    with L2_PATH.open() as f:
        for r in csv.DictReader(f):
            rows.append({
                "metric_id": "top-quintile-share", "geography_level": "national",
                "geography_code": "IN", "year": 2023, "religion": r["religion"],
                "residence": r["residence"], "value": r["q5_share"],
                "denominator": "community_population",
                "sample_size": r["n_households"], "ci_lower": "", "ci_upper": "",
                "source_id": "hces-2023-24",
                "source_document": "sources/hces-2023-24/HCES_Data_2023-24_Csv.zip",
                "extraction_run": extraction_run,
                "methodology_note": NOTE.format(res=RES_WORD[r["residence"]]),
                "break_flag": "false",
            })
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    for r in rows:
        if r["residence"] == "all":
            print(f"  {r['religion']:9s}: {r['value']}%")


if __name__ == "__main__":
    canonicalize()
