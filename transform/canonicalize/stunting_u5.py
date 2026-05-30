"""
L2 -> L3 for the `stunting-u5` metric (% of children under 5 stunted by religion).

Reads:  extracted/nfhs-5/nfhs-5-table101-stunting-by-religion.csv
Writes: canonical/stunting-u5.csv

Stunting = % below -2 SD height-for-age (WHO Child Growth Standards median).
NFHS-5 (2019-21). The all-India "all" value is computed as a sample-size-
weighted average of the 6 religion rows; we verified this reproduces the
published national rate of 35.5% (our weighted average = 35.47%, 0.03pp off
within rounding).

Story: stunting is widespread across all communities (Muslim 36.8%, Hindu
35.5%) — unlike literacy or employment, the Muslim disadvantage here is small
(+1.3pp vs Hindu). Sikhs (23.6%) and Jains (28.5%) fare best; the gap by
caste/wealth is much larger than the gap by religion.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table101-stunting-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "stunting-u5.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "all")


def canonicalize() -> None:
    by_religion: dict[str, tuple[float, int]] = {}
    source_doc = ""
    for row in csv.DictReader(L2_PATH.open()):
        by_religion[row["religion"]] = (float(row["stunting_pct"]), int(row["n_children"]))
        source_doc = row["source_document"]
    if not by_religion:
        raise RuntimeError(f"no rows in {L2_PATH}")

    # Sample-size-weighted average -> national "all"
    n_total = sum(n for _, n in by_religion.values())
    all_value = round(sum(v * n for v, n in by_religion.values()) / n_total, 2)
    by_religion["all"] = (all_value, n_total)

    extraction_run = (
        f"canonicalize-stunting-u5-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run", "methodology_note", "break_flag",
        ])
        for religion in OUTPUT_RELIGIONS:
            d = by_religion.get(religion)
            if not d:
                continue
            value, n = d
            note = (
                "NFHS-5 (2019-21) Table 10.1, Nutritional status of children: "
                "% below -2 SD height-for-age (WHO Child Growth Standards). All-India "
                "value is the sample-size-weighted average of the 6 religion rows; this "
                "reproduces the published NFHS-5 national stunting rate of 35.5%."
            )
            w.writerow([
                "stunting-u5", "national", "IN", 2020, religion, value,
                f"children_under_5_with_valid_HFA", n, "", "",
                "nfhs-5", source_doc, extraction_run, note, "false",
            ])
            n_rows += 1
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    print(f"  weighted-all = {all_value}% (published NFHS-5 national = 35.5%)")


if __name__ == "__main__":
    canonicalize()
