"""
L2 -> L3 for the `improved-sanitation` metric.

Reads:  extracted/nfhs-5/nfhs-5-table24-toilet-access-by-religion.csv
Writes: canonical/improved-sanitation.csv

Headline value = % of households with access to a toilet facility, total
residence. NFHS-5 Table 2.4. Reports muslim/hindu/all.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table24-toilet-access-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "improved-sanitation.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")


def canonicalize() -> None:
    by_religion: dict[str, float] = {}
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["residence"] != "total" or row["metric"] != "toilet_access_pct":
                continue
            by_religion[row["religion"]] = float(row["value"])

    extraction_run = (
        f"canonicalize-improved-sanitation-v{CANONICALIZER_VERSION}-"
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
        for religion in OUTPUT_RELIGIONS:
            val = by_religion.get(religion)
            if val is None:
                continue
            w.writerow([
                "improved-sanitation", "national", "IN", 2020, religion,
                val, "households", "", "", "",
                "nfhs-5",
                "sources/nfhs-5/reports/india-report-fr375.pdf",
                extraction_run,
                ("NFHS-5 Table 2.4 (page 74) — % of households with access to a "
                 "toilet facility (any type, not strictly 'improved' per JMP "
                 "definition). Total residence. Year=2020 = NFHS-5 fieldwork midpoint."),
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    canonicalize()
