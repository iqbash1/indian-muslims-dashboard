"""
L2 -> L3 for the `district-concentration-top100` metric.

Reads:  extracted/census-2011/c01-population-by-religion*.csv
Writes: canonical/district-concentration-top100.csv

Computes: share of national Muslim population that lives in the top 100
districts (ranked by absolute Muslim population). A direct measure of
geographic concentration — high values mean Muslims are clustered in a few
districts; low values mean they are dispersed.

Reads district-level rows from all state MDDS L2 files. Total Muslim
population comes from the all-India MDDS L2 national row (state_code=00).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_DIR = REPO_ROOT / "extracted" / "census-2011"
L2_GLOB = "c01-population-by-religion*.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "district-concentration-top100.csv"
CANONICALIZER_VERSION = "1.0.0"

TOP_N = 100


def canonicalize() -> None:
    # district_muslim_pop: list of (state_code, distt_code, muslim_persons, total_persons)
    district_rows: list[tuple[str, str, int, int]] = []
    national_muslim = None

    for l2_path in sorted(L2_DIR.glob(L2_GLOB)):
        with l2_path.open() as f:
            # Aggregate by (state, distt, residence=total, sex=persons)
            cell: dict[tuple[str, str, str], int] = {}
            for row in csv.DictReader(f):
                if row["residence"] != "total" or row["sex"] != "persons":
                    continue
                key = (row["state_code"], row["distt_code"], row["religion"])
                cell[key] = int(row["value"])
            # Pull national row from any file that has it (all-India MDDS)
            if national_muslim is None:
                national_muslim = cell.get(("00", "000", "muslim"))
            # Extract districts (distt_code != "000")
            for (state_code, distt_code, religion), val in cell.items():
                if religion != "muslim":
                    continue
                if distt_code == "000":
                    continue  # state or national level
                total = cell.get((state_code, distt_code, "all"))
                if total is None:
                    continue
                district_rows.append((state_code, distt_code, val, total))

    if national_muslim is None:
        raise SystemExit("national Muslim population not found in any L2 file")

    # Sort districts by Muslim population descending, take top 100
    district_rows.sort(key=lambda x: -x[2])
    top = district_rows[:TOP_N]
    top_sum = sum(r[2] for r in top)
    top_share = round(top_sum / national_muslim * 100, 2)

    extraction_run = (
        f"canonicalize-district-concentration-top100-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        w.writerow([
            "district-concentration-top100", "national", "IN", 2011, "muslim",
            top_share,
            (f"top_100_districts_muslim_pop_{top_sum} / "
             f"national_muslim_pop_{national_muslim}"),
            "", "", "",
            "census-india-2011",
            "sources/census-2011/c-series/state-mdds/c01-<state>.xls",
            extraction_run,
            (f"Share of national Muslim population concentrated in the top "
             f"{TOP_N} districts (ranked by absolute Muslim population). "
             f"Computed from all state MDDS files: {len(district_rows)} districts "
             f"considered. The top 100 hold {top_sum:,} Muslim residents of "
             f"India's {national_muslim:,} total Muslim population."),
            "false",
        ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} (1 row)")
    print(f"  {len(district_rows)} districts considered")
    print(f"  top {TOP_N} hold {top_sum:,} Muslims of {national_muslim:,} total = {top_share}%")
    print(f"  top 5 districts by Muslim count:")
    for state, distt, m, total in top[:5]:
        print(f"    state={state} distt={distt}  muslims={m:,}  share_within_distt={m/total*100:.1f}%")


if __name__ == "__main__":
    canonicalize()
