"""
L2 -> L3 for the `ls-share` metric (Muslim share of Lok Sabha members).

This metric has no clean L1 source: religion of MPs is not in PRS
Legislative Research's published candidate profile PDFs (which cover
age/gender/party but not religion), and the ECI itself doesn't tabulate
by religion. The underlying data is candidate-affidavit religion fields
aggregated post-election by journalists and researchers.

Values are hard-coded from cross-verified journalistic sources:
  - Maktoob Media (2024 detailed breakdown by party/state)
  - The India Forum (analytical piece with historical series)
  - FACTLY fact-check (78 contestants -> 24 elected)
  - Statista (1952-2024 time series)
All sources concur on the headline counts; we record those.

L1 reference documents pulled to sources/prs-eci/ for provenance trail
(they don't have the religion data directly but they are the canonical
candidate-profile reference set on top of which religion is layered).

Writes: canonical/ls-share.csv with one row per (year, religion=muslim).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "ls-share.csv"
CANONICALIZER_VERSION = "1.0.0"

# (year, lok_sabha_number, muslim_mps, total_seats, primary_citation)
LOK_SABHA_DATA = [
    (2009, 15, 28, 543, "FACTLY / Statista / Maktoob aggregations"),
    (2014, 16, 22, 543, "FACTLY / Statista / Maktoob aggregations"),
    (2019, 17, 27, 543, "FACTLY / Statista / Maktoob aggregations"),
    (2024, 18, 24, 543, "Maktoob Media (4.42%); FACTLY (24 of 78 contesting); India Forum"),
]


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-ls-share-v{CANONICALIZER_VERSION}-"
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
        for year, ls_num, mps, total, cite in LOK_SABHA_DATA:
            share = round(mps / total * 100, 2)
            w.writerow([
                "ls-share", "national", "IN", year, "muslim",
                share,
                f"lok_sabha_seats ({mps}/{total} elected MPs, LS #{ls_num})",
                "", "", "",
                "prs-eci-affidavits",
                "MANUAL: cross-verified journalistic aggregation of ECI affidavit data",
                extraction_run,
                (f"Muslim MPs in the {ls_num}th Lok Sabha: {mps} of {total} seats. "
                 f"Source: {cite}. Religion is derived from ECI candidate affidavits; "
                 f"PRS Legislative Research vital-stats PDFs cover candidate profiles "
                 f"but do not tabulate religion. This is a documented manual-entry "
                 f"metric — figures cross-verified across multiple journalistic sources."),
                "false",
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(LOK_SABHA_DATA)} rows)")
    print("  Time series:")
    for year, ls_num, mps, total, _ in LOK_SABHA_DATA:
        print(f"    {year} (LS #{ls_num}): {mps}/{total} = {mps/total*100:.2f}%")


if __name__ == "__main__":
    canonicalize()
