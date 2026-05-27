"""
L2 -> L3 for the `undertrial-share` metric (Muslim share of undertrial prisoners).

Reads:  extracted/ncrb-prison/psi-2022-religion-by-state.csv
Writes: canonical/undertrial-share.csv

Filters to category=undertrials (NCRB Table 2.11C) and uses the published
ALL-INDIA total for the share calculation.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "ncrb-prison" / "psi-2022-religion-by-state.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "undertrial-share.csv"
CANONICALIZER_VERSION = "1.0.0"


def canonicalize() -> None:
    # Sum STATES + UTs subtotals for undertrials only.
    by_religion: dict[str, int] = {}
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["category"] != "undertrials":
                continue
            if row["row_type"] != "subtotal_or_total":
                continue
            label = row["geography_name"]
            if "STATES" not in label and "UTs" not in label:
                continue
            val = row["value"]
            if not val:
                continue
            rel = row["religion"]
            by_religion[rel] = by_religion.get(rel, 0) + int(val)

    total = sum(by_religion.values())

    extraction_run = (
        f"canonicalize-undertrial-share-v{CANONICALIZER_VERSION}-"
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
        for religion in ("muslim", "hindu"):
            count = by_religion.get(religion)
            if count is None:
                continue
            share = round(count / total * 100, 2)
            w.writerow([
                "undertrial-share", "national", "IN", 2022, religion,
                share,
                f"undertrial_population_religion_reported_{total}", "", "", "",
                "ncrb-prison",
                "sources/ncrb-prison/psi-2022.pdf",
                extraction_run,
                (f"NCRB PSI 2022 Table 2.11C. Muslim undertrials: {by_religion.get('muslim'):,}, "
                 f"total religion-reported: {total:,}. "
                 "Caveat: Maharashtra did not report religion breakdown for ~33k "
                 "undertrials; share is computed over religion-reported subset only."),
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    print(f"  totals: muslim={by_religion.get('muslim'):,}  hindu={by_religion.get('hindu'):,}  "
          f"all={total:,}")


if __name__ == "__main__":
    canonicalize()
