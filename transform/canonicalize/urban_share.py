"""
L2 -> L3 for the `urban-share` metric (% of each religion living in urban areas).
MULTI-YEAR (Census 2001 + Census 2011).

Reads:  extracted/census-2001/c01-population-by-religion.csv
        extracted/census-2011/c01-population-by-religion.csv
Writes: canonical/urban-share.csv  (one row per year x religion)

Both Census rounds carry religion × residence (rural/total/urban) × sex at the
full geographic hierarchy. We compute, for each religion at the national level,
urban_share = urban_persons / total_persons * 100, per year. 2021 Census
deferred — series ends at 2011.

Story: Muslims (~36% → 40%) and Christians (~38% → 40%) are markedly more
urban than Hindus (~26% → 29%) or the all-India average (~28% → 31%). Muslim
urbanisation rose ~3.7 pp 2001→2011 vs the all-India rise of ~3.2 pp —
slightly faster urban migration, but the relative gap is stable.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_2001 = REPO_ROOT / "extracted" / "census-2001" / "c01-population-by-religion.csv"
L2_2011 = REPO_ROOT / "extracted" / "census-2011" / "c01-population-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "urban-share.csv"
CANONICALIZER_VERSION = "2.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")
SOURCE_FOR_YEAR = {2001: ("census-india-2001", L2_2001), 2011: ("census-india-2011", L2_2011)}


def load_year(year: int) -> tuple[dict[str, dict[str, int]], str]:
    src_id, path = SOURCE_FOR_YEAR[year]
    by_rel: dict[str, dict[str, int]] = {}
    source_doc = ""
    for row in csv.DictReader(path.open()):
        if row["state_code"] != "00" or row["sex"] != "persons":
            continue
        # 2011 uses table_name C0100, 2001 uses C0101 (same C-01 family, different
        # NADA cataloguing) — accept both, plus any future cataloguing variant.
        if row["table_name"] not in ("C0100", "C0101"):
            continue
        by_rel.setdefault(row["religion"], {})[row["residence"]] = int(row["value"])
        source_doc = row["source_document"]
    return by_rel, source_doc


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-urban-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    summary: list[str] = []
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run", "methodology_note", "break_flag",
        ])
        for year in sorted(SOURCE_FOR_YEAR):
            by_rel, source_doc = load_year(year)
            if not by_rel:
                raise RuntimeError(f"no national C0100 rows found for {year}")
            src_id = SOURCE_FOR_YEAR[year][0]
            for religion in OUTPUT_RELIGIONS:
                d = by_rel.get(religion)
                if not d:
                    continue
                total = d.get("total")
                urban = d.get("urban")
                if not total or urban is None:
                    continue
                share = round(urban / total * 100, 2)
                note = (
                    f"Census {year} Table C-01 (Population by Religious Community). "
                    f"Urban share = urban_persons / total_persons. {religion.capitalize()} "
                    f"urban: {urban:,} of {total:,}. National all-India urban share: "
                    f"{by_rel['all']['urban'] / by_rel['all']['total'] * 100:.2f}%."
                )
                w.writerow([
                    "urban-share", "national", "IN", year, religion, share,
                    f"total_population_{total}", "", "", "",
                    src_id, source_doc, extraction_run, note, "false",
                ])
                n_rows += 1
                summary.append(f"  {year} {religion:10s} urban={urban:>13,} of total={total:>14,}  share={share:6.2f}%")
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    print("\n".join(summary))


if __name__ == "__main__":
    canonicalize()
