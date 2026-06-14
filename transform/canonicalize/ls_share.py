"""
L2 -> L3 for the `ls-share` metric (Muslim share of Lok Sabha members).

This metric has no machine-readable primary: religion of MPs is not in
PRS Legislative Research's published candidate profile PDFs (which cover
age/gender/party but not religion), and the ECI itself doesn't tabulate
by religion. See docs/runbooks/prs-eci.md for the source registration.

The per-election seat counts live in a committed, human-readable L1 table,
sources/prs-eci-affidavits/ls-muslim-mps-by-election.csv, each row
cross-verified across at least two journalistic compilations (Maktoob
Media, The India Forum, FACTLY, Statista, ORF, Clarion India) and citing
the compilations used (in the row's `citation` column). This canonicaliser
READS that archived table; the table - not this script - is the source of
truth, so every value traces to a SHA256-checksummed L1 file like every
other metric (the table's sha is in its .meta.json sidecar). Manual-entry
SECONDARY pattern shared with mla-share.

Writes: canonical/ls-share.csv with one row per (year, religion=muslim).
Full 18-Lok-Sabha series 1952->2024.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "ls-share.csv"
SOURCE_TABLE = REPO_ROOT / "sources" / "prs-eci-affidavits" / "ls-muslim-mps-by-election.csv"
SOURCE_DOCUMENT = SOURCE_TABLE.relative_to(REPO_ROOT).as_posix()
CANONICALIZER_VERSION = "2.0.0"


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', 18 -> '18th'."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _load_source() -> list[tuple[int, int, int, int, str]]:
    """Read the archived per-election affidavit table (the L1 source of truth).
    Returns (year, lok_sabha_number, muslim_mps, total_seats, citation) rows."""
    rows: list[tuple[int, int, int, int, str]] = []
    with SOURCE_TABLE.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((int(r["election_year"]), int(r["lok_sabha_number"]),
                         int(r["muslim_seats"]), int(r["total_seats"]),
                         r["citation"]))
    return rows


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-ls-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    data = _load_source()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        for year, ls_num, mps, total, cite in data:
            share = round(mps / total * 100, 2)
            w.writerow([
                "ls-share", "national", "IN", year, "muslim",
                share,
                f"lok_sabha_seats ({mps}/{total} elected MPs, LS #{ls_num})",
                "", "", "",
                "prs-eci-affidavits",
                SOURCE_DOCUMENT,
                extraction_run,
                (f"Muslim MPs in the {_ordinal(ls_num)} Lok Sabha: {mps} of {total} seats. "
                 f"Source: {cite}. Religion is derived from ECI candidate affidavits; "
                 f"PRS Legislative Research vital-stats PDFs cover candidate profiles "
                 f"but do not tabulate religion. This is a documented manual-entry "
                 f"metric: figures cross-verified across multiple journalistic sources."),
                "false",
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(data)} rows)")
    print(f"  source: {SOURCE_DOCUMENT}")
    print("  Time series:")
    for year, ls_num, mps, total, _ in data:
        print(f"    {year} (LS #{ls_num}): {mps}/{total} = {mps/total*100:.2f}%")


if __name__ == "__main__":
    canonicalize()
