"""
L2 -> L3 for the `mla-share` metric (Muslim share of state legislative
assembly members).

Like ls-share, this is a manual-entry metric: religion is not tabulated
in any single official publication. The underlying data is candidate
affidavits classified post-election by journalists and researchers.

The per-assembly seat counts live in a committed, human-readable L1 table,
sources/prs-eci-affidavits/mla-muslim-mlas-by-assembly.csv, each row
cross-verified across journalistic compilations (Maktoob, Clarion India,
The India Forum, The Wire, Deccan Herald, FACTLY, Outlook, Radiance Weekly,
ummid.com and others) and citing the compilations used (in the row's
`citation` column). This canonicaliser READS that archived table; the
table - not this script - is the source of truth, so every value traces to
a SHA256-checksummed L1 file (sha in the table's .meta.json sidecar).

Coverage: 30 of 31 state/UT assemblies (all 28 states + Delhi/Puducherry/
J&K UTs), most recent election per assembly, plus an all-states national
aggregate row (no count; the ~6% headline). J&K rejoined the assembly
system in 2024 after the 2019 Article 370 reorganisation. The five
small-Muslim-pop states (HP, Sikkim, Arunachal, Mizoram, Nagaland) have
never elected a Muslim MLA in their history - encoded as 0. Tripura's
first-ever Muslim MLA (Boxanagar bypoll, Sep 2023) is NOT in the main-
election row. All of this is recorded per row in the archived table.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "mla-share.csv"
SOURCE_TABLE = REPO_ROOT / "sources" / "prs-eci-affidavits" / "mla-muslim-mlas-by-assembly.csv"
SOURCE_DOCUMENT = SOURCE_TABLE.relative_to(REPO_ROOT).as_posix()
CANONICALIZER_VERSION = "2.0.0"


def _load_source():
    """Read the archived per-assembly affidavit table (the L1 source of truth).
    Returns (year, geo_code, geo_level, geo_label, muslim_mlas|None,
    total_seats|None, share_pct|None, citation) rows; the national-aggregate
    row carries no seat count and an authoritative share_pct."""
    rows = []
    with SOURCE_TABLE.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m = (r["muslim_seats"] or "").strip()
            t = (r["total_seats"] or "").strip()
            s = (r["share_pct"] or "").strip()
            rows.append((
                int(r["election_year"]), r["geography_code"],
                r["geography_level"], r["geography_label"],
                int(m) if m != "" else None,
                int(t) if t != "" else None,
                float(s) if s != "" else None,
                r["citation"],
            ))
    return rows


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-mla-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    data = _load_source()

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
        for year, code, level, label, m_mlas, total, share_pct, cite in data:
            if m_mlas is None:
                # National aggregate - archived share, no count
                share = share_pct
                denom = "all_state_assembly_seats (aggregate ~6% across 28 assemblies)"
            else:
                share = round(m_mlas / total * 100, 2)
                denom = f"assembly_seats ({m_mlas}/{total} Muslim MLAs / total seats)"
            w.writerow([
                "mla-share", level, code, year, "muslim",
                share, denom, "", "", "",
                "prs-eci-affidavits",
                SOURCE_DOCUMENT,
                extraction_run,
                (f"{label}, {year}. {cite}. Religion is derived from ECI candidate "
                 f"affidavits; manual entry with cross-source verification."),
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    print(f"  source: {SOURCE_DOCUMENT}")
    for year, code, level, label, m_mlas, total, share_pct, _ in data:
        share = (m_mlas / total * 100) if m_mlas is not None else share_pct
        suffix = f" ({m_mlas}/{total})" if m_mlas is not None else " (aggregate)"
        print(f"  {year} {label}: {share:.2f}%{suffix}")


if __name__ == "__main__":
    canonicalize()
