"""
L2 -> L3 for the `pop-share-by-age` companion metric (feeds pop-share's
"By age" modal tab, Commit GG).

Reads:  extracted/census-2011/c15-national-age-by-religion.csv
Writes: canonical/pop-share-by-age.csv

One national row per 5-year age cohort (0-4 .. 80+): value = Muslim share of
that cohort's total population (Census 2011 C-15, all-residence). This is the
same "Muslim share of population" the card headlines, sliced by age instead of
by geography or residence - and it shows the youth skew (17.2% of under-5s are
Muslim, falling to ~10% among the elderly). "All ages" and "Age not stated"
cohorts are excluded from the series (the former is the 14.2% headline; the
latter is residual).

Gate: the all-ages Muslim share recomputed here must match the published
national figure (14.23%) within 0.01pp, or the run aborts.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "census-2011" / "c15-national-age-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "pop-share-by-age.csv"
SOURCE_ID = "census-india-2011"
SOURCE_DOC = "sources/census-2011/c-series/c15-religion-by-age-sex.xlsx"
CANONICALIZER_VERSION = "1.0.0"

# 5-year cohorts in census order; "All ages"/"Age not stated" are handled apart.
AGE_BANDS = [
    "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39",
    "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80+",
]
PUBLISHED_ALL_AGES_SHARE = 14.23  # Census 2011: 172,245,158 / 1,210,854,977


def canonicalize() -> None:
    # cohort -> {religion: persons}, all-residence ("total") rows only.
    cohort: dict[str, dict[str, int]] = {}
    for r in csv.DictReader(L2_PATH.open()):
        if r["residence"] != "total":
            continue
        cohort.setdefault(r["age_group"], {})[r["religion"]] = int(r["persons"])

    # Gate: recomputed all-ages share must match the published headline.
    allg = cohort.get("All ages", {})
    if not allg.get("all") or not allg.get("muslim"):
        raise SystemExit("C-15 national 'All ages' total/muslim cell missing")
    all_ages_share = allg["muslim"] / allg["all"] * 100
    if abs(all_ages_share - PUBLISHED_ALL_AGES_SHARE) > 0.01:
        raise SystemExit(
            f"all-ages Muslim share {all_ages_share:.4f}% != published "
            f"{PUBLISHED_ALL_AGES_SHARE}% (gate failed)")

    extraction_run = (
        f"canonicalize-pop-share-by-age-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows = []
    for band in AGE_BANDS:
        cells = cohort.get(band)
        if not cells or not cells.get("all") or not cells.get("muslim"):
            raise SystemExit(f"C-15 cohort {band!r} missing total/muslim cell")
        total, muslim = cells["all"], cells["muslim"]
        share = round(muslim / total * 100, 2)
        rows.append([
            "pop-share-by-age", "national", "IN", 2011, "muslim", band,
            share,
            f"muslim_{muslim} / total_{total}",
            total, "", "",
            SOURCE_ID, SOURCE_DOC, extraction_run,
            f"Muslim share of the {band} age cohort (Census 2011 C-15, "
            f"all-residence). {muslim:,} of {total:,}.",
            "false",
        ])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "age_band", "value", "denominator", "sample_size", "ci_lower",
            "ci_upper", "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        w.writerows(rows)

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} cohort rows)")
    print(f"  all-ages gate: {all_ages_share:.4f}% vs published {PUBLISHED_ALL_AGES_SHARE}% OK")
    print(f"  range: 0-4 = {rows[0][6]}%  ->  80+ = {rows[-1][6]}%")


if __name__ == "__main__":
    canonicalize()
