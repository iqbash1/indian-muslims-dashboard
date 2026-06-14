"""
L2 -> L3 for the `pop-share-by-age` companion metric (feeds pop-share's
"By age" modal tab, Commit GG; community reference lines added Commit GH).

Reads:  extracted/census-2011/c15-national-age-by-religion.csv
Writes: canonical/pop-share-by-age.csv

One national row per community per 10-year age cohort (0-9 .. 80+, aggregated
from the C-15 5-year groups): value = the share of that community's OWN total
population that falls in the cohort - i.e. each community's age distribution
(Census 2011 C-15, all-residence). Normalising to each community's own
population (not the cohort total) puts every community on a comparable scale,
so the SHAPES compare directly: a younger community sits higher in the young
bands and lower in the old. Muslims have the youngest profile (23.8% under 10,
falling to 0.7% over 80); Jains, Sikhs and Christians the oldest. The "By age"
tab plots all six named communities (Muslim the maroon hero, the rest grey).
"All ages" and "Age not stated" cohorts are excluded from the series.

Gates: (1) read-correctness - the underlying counts must reproduce the
published 14.23% Muslim-of-total share; (2) partition - each community's 17
band shares sum to ~100% (the small remainder is the "Age not stated" cohort).
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
CANONICALIZER_VERSION = "3.1.0"

# Muslim leads (the hero series); the rest follow for reference. Matches the
# C-15 religion vocabulary; "other" is the residual catch-all.
OUTPUT_RELIGIONS = ["muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other"]
REL_LABEL = {"muslim": "Muslim", "hindu": "Hindu", "christian": "Christian",
             "sikh": "Sikh", "buddhist": "Buddhist", "jain": "Jain", "other": "Other"}

# 10-year cohorts, each aggregating the C-15 5-year groups (the source only
# tabulates 5-year bands; "All ages"/"Age not stated" are handled apart).
AGE_BANDS = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
BAND_PARTS = {
    "0-9": ["0-4", "5-9"], "10-19": ["10-14", "15-19"],
    "20-29": ["20-24", "25-29"], "30-39": ["30-34", "35-39"],
    "40-49": ["40-44", "45-49"], "50-59": ["50-54", "55-59"],
    "60-69": ["60-64", "65-69"], "70-79": ["70-74", "75-79"], "80+": ["80+"],
}
PUBLISHED_ALL_AGES_SHARE = 14.23  # Census 2011: 172,245,158 / 1,210,854,977


def canonicalize() -> None:
    # cohort -> {religion: persons}, all-residence ("total") rows only.
    cohort: dict[str, dict[str, int]] = {}
    for r in csv.DictReader(L2_PATH.open()):
        if r["residence"] != "total":
            continue
        cohort.setdefault(r["age_group"], {})[r["religion"]] = int(r["persons"])

    # Gate 1 (read-correctness): the underlying counts must reproduce the
    # published 14.23% Muslim-of-total share, even though that share is no
    # longer the plotted value. allg[rel] is each community's total population.
    allg = cohort.get("All ages", {})
    if not allg.get("all") or not allg.get("muslim"):
        raise SystemExit("C-15 national 'All ages' total/muslim cell missing")
    all_ages_share = allg["muslim"] / allg["all"] * 100
    if abs(all_ages_share - PUBLISHED_ALL_AGES_SHARE) > 0.01:
        raise SystemExit(
            f"Muslim-of-total share {all_ages_share:.4f}% != published "
            f"{PUBLISHED_ALL_AGES_SHARE}% (read-correctness gate failed)")

    extraction_run = (
        f"canonicalize-pop-share-by-age-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    rows = []
    band_sum = {rel: 0.0 for rel in OUTPUT_RELIGIONS}
    for band in AGE_BANDS:
        parts = BAND_PARTS[band]
        for rel in OUTPUT_RELIGIONS:
            ctot = allg.get(rel)  # this community's total population
            if not ctot:
                raise SystemExit(f"C-15 missing {rel} total")
            try:
                n = sum(cohort[p][rel] for p in parts)  # aggregate 5-year -> 10-year
            except KeyError as exc:
                raise SystemExit(f"C-15 band {band!r} missing {rel} cell {exc}")
            share = round(n / ctot * 100, 2)  # the community's age distribution
            band_sum[rel] += share
            rows.append([
                "pop-share-by-age", "national", "IN", 2011, rel, band,
                share,
                f"{rel}_in_band_{n} / {rel}_total_{ctot}",
                ctot, "", "",
                SOURCE_ID, SOURCE_DOC, extraction_run,
                f"Share of the {REL_LABEL[rel]} population in the {band} age cohort "
                f"(Census 2011 C-15, all-residence). {n:,} of {ctot:,}.",
                "false",
            ])

    # Gate 2 (partition): each community's 17 bands sum to ~100% (the small
    # remainder is the excluded "Age not stated" cohort).
    for rel in OUTPUT_RELIGIONS:
        if not (99.0 <= band_sum[rel] <= 100.5):
            raise SystemExit(f"{rel} age bands sum to {band_sum[rel]:.2f}% (expected ~100)")

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

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows; "
          f"{len(OUTPUT_RELIGIONS)} communities x {len(AGE_BANDS)} cohorts)")
    print(f"  read-correctness: Muslim/total = {all_ages_share:.4f}% (vs {PUBLISHED_ALL_AGES_SHARE}%) OK")
    mus = {r[5]: r[6] for r in rows if r[4] == "muslim"}
    print(f"  Muslim age profile: {AGE_BANDS[0]} = {mus[AGE_BANDS[0]]}%  ->  "
          f"{AGE_BANDS[-1]} = {mus[AGE_BANDS[-1]]}%  (bands sum {band_sum['muslim']:.1f}%)")


if __name__ == "__main__":
    canonicalize()
