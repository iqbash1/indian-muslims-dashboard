"""
L2 -> L3 for the `urban-share` metric (% of each religion living in urban areas).

Reads:  extracted/census-2011/c01-population-by-religion.csv
Writes: canonical/urban-share.csv

Census 2011 Table C-01 already carries the religion x residence (rural/total/
urban) x sex breakdown. We compute, for each religion at the national level,
urban_share = urban_persons / total_persons * 100. Story: Muslims (~40%) and
Christians (~40%) are markedly more urban than Hindus (~29%) or the all-India
average (~31%) — a Sachar-era fact that shapes outcomes downstream (urban poor
labour markets, segregation, housing access).
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "census-2011" / "c01-population-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "urban-share.csv"
CANONICALIZER_VERSION = "1.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")


def canonicalize() -> None:
    # Aggregate national persons by religion x residence (table_name C0100, state=00, sex=persons).
    by_rel: dict[str, dict[str, int]] = {}
    source_doc = ""
    for row in csv.DictReader(L2_PATH.open()):
        if row["state_code"] != "00" or row["sex"] != "persons" or row["table_name"] != "C0100":
            continue
        rel = row["religion"]
        res = row["residence"]
        by_rel.setdefault(rel, {})[res] = int(row["value"])
        source_doc = row["source_document"]
    if not by_rel:
        raise RuntimeError(f"no national C0100 rows found in {L2_PATH}")

    extraction_run = (
        f"canonicalize-urban-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary: list[str] = []
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run", "methodology_note", "break_flag",
        ])
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
                f"Census 2011 Table C-01 (Population by Religious Community). "
                f"Urban share = urban_persons / total_persons. {religion.capitalize()} "
                f"urban: {urban:,} of {total:,}. National all-India urban share: "
                f"{by_rel['all']['urban'] / by_rel['all']['total'] * 100:.2f}% — Muslims "
                f"(and Christians, Buddhists, Jains) are notably more urbanised than the "
                f"all-India average; Sikhs and Hindus are below it."
            )
            w.writerow([
                "urban-share", "national", "IN", 2011, religion, share,
                f"total_population_{total}", "", "", "",
                "census-india-2011", source_doc, extraction_run, note, "false",
            ])
            n_rows += 1
            summary.append(f"  {religion:10s} urban={urban:>13,} of total={total:>14,}  share={share:6.2f}%")
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    print("\n".join(summary))


if __name__ == "__main__":
    canonicalize()
