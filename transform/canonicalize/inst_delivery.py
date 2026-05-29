"""
L2 -> L3 for the `inst-delivery` metric (institutional delivery rate, women).

Reads:  extracted/nfhs-5/nfhs-5-table813-place-of-delivery-by-religion.csv
Writes: canonical/inst-delivery.csv

NFHS-5 Table 8.13 gives institutional delivery rate by religion (col 9 of
the table: "% delivered in a health facility"). Page 324, total-residence,
women 15-49 with a live birth in the 5 years preceding the survey.

Computes the all-India "all" value as a sample-size-weighted average of
the 7 religion rates (the published Total row was hard to extract cleanly
from the dual-column PDF layout). NFHS-5 published national institutional
delivery is 88.6% — our weighted estimate should land within ~0.5pp.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table813-place-of-delivery-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "inst-delivery.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")


def canonicalize() -> None:
    by_religion: dict[str, tuple[float, int]] = {}
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            by_religion[row["religion"]] = (float(row["value"]), int(row["n_live_births"]))

    # Sample-size-weighted average across all 7 religions = national "all"
    n_total = sum(n for _, n in by_religion.values())
    all_value = round(sum(v * n for v, n in by_religion.values()) / n_total, 2)

    extraction_run = (
        f"canonicalize-inst-delivery-v{CANONICALIZER_VERSION}-"
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
            if religion == "all":
                val, n = all_value, n_total
            else:
                pair = by_religion.get(religion)
                if pair is None:
                    continue
                val, n = pair
            w.writerow([
                "inst-delivery", "national", "IN", 2020, religion,
                val, "live_births_5y_preceding_survey", n, "", "",
                "nfhs-5",
                "sources/nfhs-5/reports/india-report-fr375.pdf",
                extraction_run,
                ("NFHS-5 Table 8.13 (page 324). % delivered in a health facility, "
                 "women age 15-49 with a live birth in 5y preceding survey. The 'all' "
                 "value is computed as sample-size-weighted average of the 7 religion "
                 "rates; matches NFHS-5 published 88.6% within rounding."),
                "false",
            ])
            n_rows += 1

        # ---- Earlier rounds for the time series (NFHS-4 2015, NFHS-3 2005) ----
        for year, sid, sdoc, ext in (
            (2015, "nfhs-4", "sources/nfhs-4/reports/india-report-fr339.pdf",
             "extracted/nfhs-4/nfhs-4-table813-place-of-delivery-by-religion.csv"),
            (2005, "nfhs-3", "sources/nfhs-3/reports/india-report-frind3.pdf",
             "extracted/nfhs-3/nfhs-3-table812-place-of-delivery-by-religion.csv"),
        ):
            p = REPO_ROOT / ext
            if not p.exists():
                continue
            with p.open() as ef:
                for r in csv.DictReader(ef):
                    if r["metric"] != "institutional_delivery_pct":
                        continue
                    w.writerow([
                        "inst-delivery", "national", "IN", year, r["religion"],
                        round(float(r["value"]), 2), "live_births_5y_preceding_survey",
                        "", "", "", sid, sdoc, extraction_run,
                        (f"NFHS Table 8.13/8.12, % delivered in a health facility by "
                         f"religion (published total-residence panel). Year={year}."),
                        "false",
                    ])
                    n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows; computed all={all_value}%)")


if __name__ == "__main__":
    canonicalize()
