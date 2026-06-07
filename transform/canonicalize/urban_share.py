"""
L2 -> L3 for the `urban-share` metric (% of each religion living in urban areas).
MULTI-YEAR (Census 2001 + Census 2011).

Reads:  extracted/census-2001/c01-population-by-religion.csv
        extracted/census-2011/c01-population-by-religion.csv
Writes: canonical/urban-share.csv  (one row per year x geography x religion;
        national + all 35 states/UTs)

Both Census rounds carry religion × residence (rural/total/urban) × sex at the
full geographic hierarchy. We compute, for each religion at the national AND
state level, urban_share = urban_persons / total_persons * 100, per year. The
all-India C-01 file carries national (state_code 00) plus every state/UT
(state_code 01..; no districts). 2021 Census deferred — series ends at 2011.

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
CANONICALIZER_VERSION = "3.0.0"

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")
SOURCE_FOR_YEAR = {2001: ("census-india-2001", L2_2001), 2011: ("census-india-2011", L2_2011)}


LEVEL_RANK = {"national": 0, "state": 1}
RELIGION_RANK = {r: i for i, r in enumerate(OUTPUT_RELIGIONS)}


def _geo(state_code: str) -> tuple[str, str]:
    return ("national", "IN") if state_code == "00" else ("state", f"IN-S{state_code}")


def load_year(year: int) -> tuple[dict[tuple[str, str], dict[str, dict[str, int]]], str]:
    """Return {(level, code): {religion: {residence: persons}}} for national + states.

    The all-India C-01 file carries national (state_code 00) plus all 35 states
    (state_code 01..; single distt_code, so no districts), each with
    religion x residence x sex. We keep sex=persons and the urban/total cells.
    """
    src_id, path = SOURCE_FOR_YEAR[year]
    by_geo: dict[tuple[str, str], dict[str, dict[str, int]]] = {}
    source_doc = ""
    for row in csv.DictReader(path.open()):
        if row["sex"] != "persons":
            continue
        # 2011 uses table_name C0100, 2001 uses C0101 (same C-01 family, different
        # NADA cataloguing) — accept both, plus any future cataloguing variant.
        if row["table_name"] not in ("C0100", "C0101"):
            continue
        geo = _geo(row["state_code"])
        by_geo.setdefault(geo, {}).setdefault(row["religion"], {})[row["residence"]] = int(row["value"])
        source_doc = row["source_document"]
    return by_geo, source_doc


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-urban-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    out_rows: list[list] = []
    summary: list[str] = []
    for year in sorted(SOURCE_FOR_YEAR):
        by_geo, source_doc = load_year(year)
        if not by_geo:
            raise RuntimeError(f"no C-01 rows found for {year}")
        src_id = SOURCE_FOR_YEAR[year][0]
        nat_all = by_geo.get(("national", "IN"), {}).get("all", {})
        nat_share = (nat_all["urban"] / nat_all["total"] * 100) if nat_all.get("total") and nat_all.get("urban") is not None else None
        for (level, code), geo_rel in by_geo.items():
            all_d = geo_rel.get("all", {})
            geo_all_share = (all_d["urban"] / all_d["total"] * 100) if all_d.get("total") and all_d.get("urban") is not None else None
            for religion in OUTPUT_RELIGIONS:
                d = geo_rel.get(religion)
                if not d:
                    continue
                total = d.get("total")
                urban = d.get("urban")
                if not total or urban is None:
                    continue
                share = round(urban / total * 100, 2)
                if level == "national":
                    note = (
                        f"Census {year} Table C-01 (Population by Religious Community). "
                        f"Urban share = urban_persons / total_persons. {religion.capitalize()} "
                        f"urban: {urban:,} of {total:,}. National all-India urban share: "
                        f"{nat_share:.2f}%."
                    )
                else:
                    note = (
                        f"Census {year} Table C-01 (Population by Religious Community). "
                        f"Urban share = urban_persons / total_persons for {religion} in this "
                        f"state/UT. {religion.capitalize()} urban: {urban:,} of {total:,}."
                        + (f" Urban share across all communities here: {geo_all_share:.2f}%."
                           if geo_all_share is not None else "")
                    )
                out_rows.append([
                    "urban-share", level, code, year, religion, share,
                    f"total_population_{total}", "", "", "",
                    src_id, source_doc, extraction_run, note, "false",
                ])
                if level == "national":
                    summary.append(f"  {year} {religion:10s} urban={urban:>13,} of total={total:>14,}  share={share:6.2f}%")

    out_rows.sort(key=lambda r: (LEVEL_RANK[r[1]], r[2], r[3], RELIGION_RANK[r[4]]))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run", "methodology_note", "break_flag",
        ])
        w.writerows(out_rows)

    n_state = sum(1 for r in out_rows if r[1] == "state")
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(out_rows)} rows; {n_state} state rows)")
    print("\n".join(summary))


if __name__ == "__main__":
    canonicalize()
