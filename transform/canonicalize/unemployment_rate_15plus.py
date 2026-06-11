"""
L2 -> L3 for the `unemployment-rate-15plus` metric.

Reads:  extracted/plfs/plfs-microdata-2017-24-by-religion.csv  (all 7 rounds)
Writes: canonical/unemployment-rate-15plus.csv

Unemployment rate = unemployed (usual status ps: code 81) / labour force, age
15+. Unlike LFPR/WPR/salaried-share, the published PLFS annual-report tables
never break the unemployment rate down by religion, so ALL seven points
(2017-18 to 2023-24) come from the unit-level microdata (source
plfs-microdata; see _plfs_microdata.py and docs/runbooks/plfs-microdata.md).
The extraction's validation gate reproduces each round's published all-India
UR to 0.1, so the levels are anchored to the official series.
"""

from __future__ import annotations

import datetime as dt
import pathlib

from _plfs_microdata import eus_trend_rows, trend_rows

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "unemployment-rate-15plus.csv"
CANONICALIZER_VERSION = "1.0.0"

import csv

COLS = [
    "metric_id", "geography_level", "geography_code", "year", "religion",
    "sex", "residence", "value", "denominator", "sample_size", "ci_lower",
    "ci_upper", "source_id", "source_document", "extraction_run",
    "methodology_note", "break_flag",
]


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-unemployment-rate-15plus-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = trend_rows("unemployment-rate-15plus", "ur", "labour_force_15plus",
                      "unemployment rate (unemployed / labour force)",
                      extraction_run, years=range(2017, 2024))
    rows += eus_trend_rows("unemployment-rate-15plus", "ur", "labour_force_15plus",
                           "unemployment rate (unemployed / labour force)",
                           extraction_run)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(rows)
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    canonicalize()
