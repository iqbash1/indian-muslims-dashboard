"""
L2 -> L3 for the `ls-share` metric (Muslim share of Lok Sabha members).

This metric has no machine-readable primary: religion of MPs is not in
PRS Legislative Research's published candidate profile PDFs (which cover
age/gender/party but not religion), and the ECI itself doesn't tabulate
by religion. See docs/runbooks/prs-eci.md for the source registration.

Values are hard-coded from cross-verified journalistic sources (Maktoob
Media, The India Forum, FACTLY, Statista, ORF, Clarion India). At least
two compilations agree on every entry; methodology_note per row cites
the compilations used. Manual-entry SECONDARY pattern shared with
mla-share (the other per-election journalistic series; pop-share and
sex-ratio were once fallback-sourced too, but are now primary RGI census).

Writes: canonical/ls-share.csv with one row per (year, religion=muslim).
Full 18-Lok-Sabha series 1952→2024.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "ls-share.csv"
CANONICALIZER_VERSION = "1.0.0"

# (year, lok_sabha_number, muslim_mps, total_seats, primary_citation)
# Headline counts from cross-verified secondary compilations: India Forum
# (Hilal Ahmed's historical series), Statista, ORF, Maktoob Media, FACTLY.
# All published series concur on these figures within +/- 1 MP rounding.
# The 1980-89 Congress era was the historical peak (~9% Muslim
# representation, close to but never reaching the ~14.2% population share);
# the post-2014 BJP-majority Lok Sabhas have run ~4-5%.
LOK_SABHA_DATA = [
    (1952,  1, 21, 489, "India Forum / Statista historical series"),
    (1957,  2, 23, 494, "India Forum / Statista historical series"),
    (1962,  3, 23, 494, "India Forum / Statista historical series"),
    (1967,  4, 25, 520, "India Forum / Statista historical series"),
    (1971,  5, 30, 518, "India Forum / Statista historical series"),
    (1977,  6, 34, 542, "India Forum / Statista (Janata wave)"),
    (1980,  7, 49, 542, "India Forum / Statista (historical PEAK)"),
    (1984,  8, 45, 542, "India Forum / Statista (Rajiv Gandhi sweep)"),
    (1989,  9, 33, 525, "India Forum / Statista"),
    (1991, 10, 28, 521, "India Forum / Statista"),
    (1996, 11, 28, 543, "India Forum / Statista"),
    (1998, 12, 29, 543, "India Forum / Statista"),
    (1999, 13, 32, 543, "India Forum / Statista"),
    (2004, 14, 36, 543, "India Forum / Statista (UPA-1)"),
    (2009, 15, 28, 543, "FACTLY / Statista / Maktoob aggregations"),
    (2014, 16, 22, 543, "FACTLY / Statista / Maktoob aggregations"),
    (2019, 17, 27, 543, "FACTLY / Statista / Maktoob aggregations"),
    (2024, 18, 24, 543, "Maktoob Media (4.42%); FACTLY (24 of 78 contesting); India Forum"),
]


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', 18 -> '18th'."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


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
                (f"Muslim MPs in the {_ordinal(ls_num)} Lok Sabha: {mps} of {total} seats. "
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
