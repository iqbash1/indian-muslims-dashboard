"""
L2 -> L3 for the `prison-share` metric (Muslim share of total prison population).

Reads:  extracted/ncrb-prison/psi-2022-religion-by-state.csv
Writes: canonical/prison-share.csv

Total prison population = convicts + undertrials + detenues + other prisoners.
NCRB PSI 2022 reports religion separately for each category (Tables 2.10C
through 2.13C) but the ALL-INDIA row format varies across pages (some span
two lines and don't match our single-line regex). We compute ALL-INDIA as
STATES subtotal + UTs subtotal for each category, which by construction
equals the published ALL-INDIA total.

Important caveat (recorded in methodology): Maharashtra did NOT report
religion breakdown for undertrials and detenues in PSI 2022. The published
religion totals therefore exclude ~32,883 Maharashtra undertrials and 189
Maharashtra detenues whose religion is unknown. Reported shares are
"Muslim share among prisoners whose religion was reported."
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "ncrb-prison" / "psi-2022-religion-by-state.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "prison-share.csv"
CANONICALIZER_VERSION = "1.0.0"

CATEGORIES = ["convicts", "undertrials", "detenues", "other"]


def load_subtotals() -> dict[tuple[str, str], int]:
    """Returns {(category, religion): count} summed across STATES + UTs subtotals.
    By construction this equals the ALL-INDIA published total.
    """
    out: dict[tuple[str, str], int] = {}
    with L2_PATH.open() as f:
        for row in csv.DictReader(f):
            if row["row_type"] != "subtotal_or_total":
                continue
            label = row["geography_name"]
            # Use STATES and UTs subtotals (their sum equals ALL-INDIA)
            if "STATES" not in label and "UTs" not in label:
                continue
            cat = row["category"]
            rel = row["religion"]
            val_str = row["value"]
            if not val_str:  # missing / non-reporting
                continue
            out[(cat, rel)] = out.get((cat, rel), 0) + int(val_str)
    return out


def canonicalize() -> None:
    sub = load_subtotals()

    # Sum across all categories for each religion
    by_religion: dict[str, int] = {}
    for (cat, rel), val in sub.items():
        by_religion[rel] = by_religion.get(rel, 0) + val

    total = sum(by_religion.values())
    if total == 0:
        raise RuntimeError("No prison data found in L2.")

    extraction_run = (
        f"canonicalize-prison-share-v{CANONICALIZER_VERSION}-"
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
                "prison-share", "national", "IN", 2022, religion,
                share,
                f"total_prison_population_religion_reported_{total}", "", "", "",
                "ncrb-prison",
                "sources/ncrb-prison/psi-2022.pdf",
                extraction_run,
                ("NCRB PSI 2022 Tables 2.10C-2.13C combined (convicts + undertrials + "
                 "detenues + other prisoners). Computed as STATES+UTs subtotals (equals "
                 f"ALL-INDIA total). Muslim count: {by_religion.get('muslim'):,}, "
                 f"total: {total:,}. Caveat: Maharashtra did not report religion "
                 "breakdown for undertrials and detenues in PSI 2022, so the religion-"
                 "reported denominator excludes ~33k Maharashtra prisoners. Shares are "
                 "'Muslim share among prisoners whose religion was reported.'"),
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    print(f"  totals: muslim={by_religion.get('muslim'):,}  hindu={by_religion.get('hindu'):,}  "
          f"all={total:,}")


if __name__ == "__main__":
    canonicalize()
