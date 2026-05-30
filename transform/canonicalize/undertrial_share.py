"""
L2 -> L3 for the `undertrial-share` metric (Muslim share of undertrial prisoners).
MULTI-YEAR.

Reads:  extracted/ncrb-prison/psi-*-religion-by-state.csv  (globbed, one per year)
Writes: canonical/undertrial-share.csv  (one row per year x religion)

Filters to category=undertrials (NCRB Table 2.11C). For each year we sum
religion VALUES across STATES + UTs subtotals (= ALL-INDIA by construction;
auto-excludes non-reporting states whose religion cells are blank). Reported
shares are "Muslim share among undertrials whose religion was reported."
Undertrials are the large majority of the prison population, so this tracks
the overall prison-share closely but a touch higher.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_DIR = REPO_ROOT / "extracted" / "ncrb-prison"
OUTPUT_PATH = REPO_ROOT / "canonical" / "undertrial-share.csv"
CANONICALIZER_VERSION = "2.0.0"

YEAR_RE = re.compile(r"psi-(\d{4})-religion-by-state\.csv$")
MUSLIM_POP_SHARE = 14.23  # Census 2011 Muslim share of national population
CATEGORIES = {"undertrials"}


def load_year_subtotals(path: pathlib.Path, categories: set[str] | None = None):
    """Sum religion VALUES across STATES+UTs subtotals for the given year file,
    restricted to `categories`. Returns (by_religion, source_document)."""
    by_religion: dict[str, int] = {}
    source_doc = ""
    with path.open() as f:
        for row in csv.DictReader(f):
            if row["row_type"] != "subtotal_or_total":
                continue
            if categories is not None and row["category"] not in categories:
                continue
            label = row["geography_name"]
            if "STATES" not in label and "UTs" not in label:
                continue
            val = row["value"]
            if not val:  # blank = non-reporting cell
                continue
            by_religion[row["religion"]] = by_religion.get(row["religion"], 0) + int(val)
            source_doc = row["source_document"]
    return by_religion, source_doc


def canonicalize() -> None:
    files = sorted(L2_DIR.glob("psi-*-religion-by-state.csv"))
    if not files:
        raise RuntimeError(f"no L2 files matching psi-*-religion-by-state.csv in {L2_DIR}")

    extraction_run = (
        f"canonicalize-undertrial-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows_out: list[tuple] = []
    summary: list[str] = []
    for path in files:
        m = YEAR_RE.search(path.name)
        if not m:
            continue
        year = int(m.group(1))
        by_religion, source_doc = load_year_subtotals(path, CATEGORIES)
        total = sum(by_religion.values())
        if total == 0:
            raise RuntimeError(f"no undertrial data found in {path.name}")
        muslim = by_religion.get("muslim", 0)
        for religion in ("muslim", "hindu"):
            count = by_religion.get(religion)
            if count is None:
                continue
            share = round(count / total * 100, 2)
            note = (
                f"NCRB PSI {year} Table 2.11C (undertrial prisoners). Muslim share among "
                f"undertrials whose religion was reported: sum of religion columns across "
                f"STATES+UTs subtotals (auto-excludes states that did not report religion, "
                f"e.g. Maharashtra in several years). {religion.capitalize()} count: "
                f"{count:,}, religion-reported total: {total:,}. Compare vs Muslim share of "
                f"population ~{MUSLIM_POP_SHARE}% (Census 2011)."
            )
            rows_out.append((
                "undertrial-share", "national", "IN", year, religion, share,
                f"undertrial_population_religion_reported_{total}", "", "", "",
                "ncrb-prison", source_doc, extraction_run, note, "false",
            ))
        summary.append(f"  {year}: muslim={muslim:,} total={total:,} share={muslim/total*100:.2f}%")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run", "methodology_note", "break_flag",
        ])
        for r in rows_out:
            w.writerow(r)

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows_out)} rows, {len(summary)} years)")
    print("\n".join(summary))


if __name__ == "__main__":
    canonicalize()
