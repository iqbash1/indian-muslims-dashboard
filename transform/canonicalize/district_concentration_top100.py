"""
L2 -> L3 for the `district-concentration-top100` metric.

Reads:  extracted/census-2011/c01-population-by-religion*.csv
Writes: canonical/district-concentration-top100.csv

Emits 1 national row + the top-100 district rows (since v2.0.0):
  - National row (geography_level=national): value = % of national Muslim
    population concentrated in the top 100 districts (the headline aggregate).
  - 100 district rows (geography_level=district): one per top-100 district.
    value = absolute Muslim population in that district. sample_size = total
    district population. methodology_note carries rank + district name + state.
    This lets the dashboard render a scrollable top-100 table directly from
    canonical.

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
CANONICALIZER_VERSION = "2.0.0"

TOP_N = 100


def canonicalize() -> None:
    # district_rows: list of (state_code, distt_code, area_name, muslim_persons, total_persons)
    district_rows: list[tuple[str, str, str, int, int]] = []
    national_muslim = None

    for l2_path in sorted(L2_DIR.glob(L2_GLOB)):
        with l2_path.open() as f:
            # Aggregate by (state, distt, residence=total, sex=persons)
            cell: dict[tuple[str, str, str], int] = {}
            names: dict[tuple[str, str], str] = {}
            for row in csv.DictReader(f):
                if row["residence"] != "total" or row["sex"] != "persons":
                    continue
                # Filter to district-aggregate level (no tehsil/town breakdowns)
                if row["tehsil_code"] != "00000" or row["town_code"] != "000000":
                    continue
                key = (row["state_code"], row["distt_code"], row["religion"])
                cell[key] = int(row["value"])
                # Capture the district name once
                names[(row["state_code"], row["distt_code"])] = row["area_name"]
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
                name = names.get((state_code, distt_code), "").replace("District - ", "").strip()
                district_rows.append((state_code, distt_code, name, val, total))

    if national_muslim is None:
        raise SystemExit("national Muslim population not found in any L2 file")

    # Sort districts by Muslim population descending, take top 100
    district_rows.sort(key=lambda x: -x[3])
    top = district_rows[:TOP_N]
    top_sum = sum(r[3] for r in top)
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
        # National aggregate row
        w.writerow([
            "district-concentration-top100", "national", "IN", 2011, "muslim",
            top_share,
            (f"top_100_districts_muslim_pop_{top_sum} / "
             f"national_muslim_pop_{national_muslim}"),
            national_muslim, "", "",
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
        # Per-district rows (rank-ordered)
        for rank, (state_code, distt_code, name, muslim, total) in enumerate(top, 1):
            pct = round(muslim / total * 100, 2)
            geo_code = f"IN-S{state_code}-D{distt_code}"
            w.writerow([
                "district-concentration-top100", "district", geo_code, 2011, "muslim",
                muslim,
                f"district_total_pop_{total}",
                total, "", "",
                "census-india-2011",
                f"sources/census-2011/c-series/state-mdds/c01-{state_code}-<state>.xls",
                extraction_run,
                f"rank={rank}; name={name}; muslim_pct_of_district={pct}",
                "false",
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} (1 national + {len(top)} district rows)")
    print(f"  {len(district_rows)} districts considered")
    print(f"  top {TOP_N} hold {top_sum:,} Muslims of {national_muslim:,} total = {top_share}%")
    print(f"  top 5 districts by Muslim count:")
    for state, distt, name, m, total in top[:5]:
        print(f"    #{1}: {name} (S{state})  muslims={m:,}  share_within_distt={m/total*100:.1f}%")


if __name__ == "__main__":
    canonicalize()
