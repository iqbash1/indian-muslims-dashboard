"""
L2 -> L3 for `pop-growth-decadal`: decadal population growth 2001 -> 2011 by
religious community, derived from the archived Census C-01 head-counts. Companion
to `pop-share`, surfaced as its "Population growth" tab.

The report on Muslim living conditions notes Muslim population grew faster than
Hindu over 2001-2011, but stresses the driver is (now-converging) fertility, not
migration or conversion. This metric makes that comparison explicit while the
methodology note carries the caveat.

Fully traceable: the 2001 and 2011 national counts are the same Census C-01
extracts `pop-share` already uses (this module reuses pop_share's readers, so it
can never drift from the share series). Growth = (count_2011 - count_2001) /
count_2001 x 100. Gated to the RGI 2011 religion-release published growth rates.

Writes: canonical/pop-growth-decadal.csv, one row per community + the all-India
total (the dashed reference).
"""

from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "pop-growth-decadal.csv"
CANONICALIZER_VERSION = "1.0.0"

# Reuse pop_share's census readers so the counts can never diverge from the
# share series (importing runs only module-level defs; canonicalize() is
# __main__-guarded there).
_PS_PATH = REPO_ROOT / "transform" / "canonicalize" / "pop_share.py"
_spec = importlib.util.spec_from_file_location("_pop_share_readers", _PS_PATH)
_ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ps)

SRC_2001 = "sources/census-2001/c-series/c01-population-by-religion.xls"
SRC_2011 = "sources/census-2011/c-series/c01-population-by-religion.xls"

# RGI Census 2011 religion-release published decadal growth rates (the gate).
PUBLISHED = {"hindu": 16.8, "muslim": 24.6, "christian": 15.5,
             "sikh": 8.4, "buddhist": 6.1, "jain": 5.4}
RELIGIONS = ["hindu", "muslim", "christian", "sikh", "buddhist", "jain"]


def canonicalize() -> None:
    persons, _ = _ps._read_2011()
    y2011 = {rel: persons[("national", "IN", rel)]
             for (lvl, _code, rel) in persons if lvl == "national"}
    y2001 = _ps._read_2001_national()

    extraction_run = (
        f"canonicalize-pop-growth-decadal-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows = []
    for rel in RELIGIONS + ["all"]:
        a, b = y2001.get(rel), y2011.get(rel)
        if not a or not b:
            raise SystemExit(f"missing census count for {rel}: 2001={a} 2011={b}")
        # Canonical keeps full precision (4dp, like pop-share); display rounds to
        # 1dp at render time. Rounding to 2dp here would double-round Muslim
        # 24.6453 -> 24.65 -> 24.7 and mismatch the published 24.6%.
        growth = round((b - a) / a * 100, 4)
        if rel in PUBLISHED and abs(round(growth, 1) - PUBLISHED[rel]) > 0.2:
            raise SystemExit(
                f"GATE FAIL {rel}: computed {growth}% vs published {PUBLISHED[rel]}%")
        rows.append((rel, a, b, growth))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        for rel, a, b, growth in rows:
            w.writerow([
                "pop-growth-decadal", "national", "IN", 2011, rel,
                growth,
                f"decadal_growth_pct_2001_2011 ({a}->{b} persons)",
                "", "", "",
                "census-india-2011", SRC_2011, extraction_run,
                (f"Decadal population growth 2001 to 2011 for {rel}: "
                 f"(2011 count {b:,} minus 2001 count {a:,}) divided by the 2001 "
                 f"count, times 100. Census C-01 head-counts (2001: {SRC_2001}; "
                 f"2011: {SRC_2011}); matches the RGI 2011 religion-release "
                 f"published rate. Faster Muslim growth is driven by higher, now "
                 f"converging fertility, not migration or conversion (RGI; Pew)."),
                "false",
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    for rel, a, b, growth in rows:
        print(f"  {rel:10} {a:>13,} -> {b:>13,}  = {growth:>5}%")


if __name__ == "__main__":
    canonicalize()
