"""
L2 -> L3 for the `salaried-share` metric.

Reads:  extracted/plfs/plfs-2023-24-table49-employment-status-by-religion.csv
Writes: canonical/salaried-share.csv

Publishes Muslim, Hindu, all rural+urban-person regular wage/salary share
of all workers, from PLFS 2023-24 Table 49.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "plfs" / "plfs-2023-24-table49-employment-status-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "salaried-share.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")


def canonicalize() -> None:
    by_religion: dict[str, float] = {}
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if (row["metric"] == "regular_wage_salary"
                    and row["residence"] == "total"
                    and row["sex"] == "person"):
                by_religion[row["religion"]] = float(row["value"])

    extraction_run = (
        f"canonicalize-salaried-share-v{CANONICALIZER_VERSION}-"
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
                "salaried-share", "national", "IN", 2023, religion,
                val, "all_workers_usual_status_ps_ss", "", "", "",
                "plfs",
                "sources/plfs/annual/plfs-annual-report-2023-24.pdf",
                extraction_run,
                ("PLFS 2023-24 Table 49 (pages 401-402). Share of workers in "
                 "'regular wage/salary' employment, rural+urban person-level. "
                 "Other categories: self-employed (own account + helper), "
                 "casual labour. Reference period: Jul 2023 - Jun 2024."),
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    for religion in OUTPUT_RELIGIONS:
        v = by_religion.get(religion)
        if v:
            print(f"  {religion}: {v}%")


if __name__ == "__main__":
    canonicalize()
