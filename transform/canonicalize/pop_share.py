"""
L2 -> L3 for the `pop-share` metric (Muslim share of total population).

Reads:  extracted/census-2011/c01-population-by-religion*.csv
        - c01-population-by-religion.csv          (all-India MDDS: states only)
        - c01-population-by-religion-<state>.csv  (state MDDS: state + districts)
Writes: canonical/pop-share.csv

Filters L2 to (residence=total, sex=persons), computes muslim/all * 100
per geography, emits one row per geography for religion=muslim. Dedupes
rows by (level, code) when the same geography appears in multiple files
(e.g. UP state row in both all-India and UP state-MDDS files).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_DIR = REPO_ROOT / "extracted" / "census-2011"
L2_GLOB = "c01-population-by-religion*.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "pop-share.csv"
CANONICALIZER_VERSION = "1.1.0"


def geography(state_code: str, distt_code: str) -> tuple[str, str]:
    if state_code == "00" and distt_code == "000":
        return "national", "IN"
    if distt_code == "000":
        return "state", f"IN-S{state_code}"
    return "district", f"IN-S{state_code}-D{distt_code}"


def canonicalize() -> None:
    geo_religion_persons: dict[tuple[str, str, str], int] = {}
    geo_all_persons: dict[tuple[str, str], int] = {}

    l2_files = sorted(L2_DIR.glob(L2_GLOB))
    if not l2_files:
        raise SystemExit(f"no L2 files match {L2_DIR / L2_GLOB}")

    for l2_path in l2_files:
        with l2_path.open() as f:
            for row in csv.DictReader(f):
                if row["residence"] != "total" or row["sex"] != "persons":
                    continue
                level, code = geography(row["state_code"], row["distt_code"])
                value = int(row["value"])
                key = (level, code, row["religion"])
                # Dedupe: same (level, code, religion) from multiple files
                # should agree; later files overwrite (but values should match).
                geo_religion_persons[key] = value
                if row["religion"] == "all":
                    geo_all_persons[(level, code)] = value

    extraction_run = (
        f"canonicalize-pop-share-v{CANONICALIZER_VERSION}-"
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

        for (level, code, religion), persons in sorted(geo_religion_persons.items()):
            if religion != "muslim":
                continue
            all_persons = geo_all_persons.get((level, code))
            if not all_persons:
                continue
            share = round(persons / all_persons * 100, 4)
            # Source document depends on geography level
            if level == "district":
                source_doc = "sources/census-2011/c-series/state-mdds/c01-<state>.xls"
            else:
                source_doc = "sources/census-2011/c-series/c01-population-by-religion.xls"
            w.writerow([
                "pop-share", level, code, 2011, "muslim",
                share, "all_persons_at_geography_total_residence", "", "", "",
                "census-india-2011",
                source_doc,
                extraction_run,
                "Muslim share of total population (all residences combined).",
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    canonicalize()
