"""
L2 -> L3 for the `pop-share` metric — share of each religious community in
India's population.

NATIONAL decadal series (1961 -> 2011), the six major communities:
  1961-1991  SECONDARY, manual-entry compilation of the published Census decadal
             religion proportions. No clean machine-readable RGI decadal table is
             downloadable (NADA digitised only 2001 + 2011 religion tables; Pew /
             PIB / Wayback bot-block automated retrieval). These are the standard
             Census figures (RGI; reproduced by Pew 2021 and Wikipedia), cross-
             validated against this repo's PRIMARY C-01 extracts — 2001 & 2011
             agree to <0.02pp. Flagged "secondary" on the card. (source_id
             census-decadal-religion)
  2001       PRIMARY — extracted/census-2001/c01-population-by-religion.csv
  2011       PRIMARY — extracted/census-2011/c01-population-by-religion*.csv

Plus the 2011 STATE + DISTRICT Muslim share (primary C-01) for the drill-down.

share = religion_persons / all_persons * 100   (residence=total, sex=persons)
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_2011_DIR = REPO_ROOT / "extracted" / "census-2011"
L2_2011_GLOB = "c01-population-by-religion*.csv"
L2_2001 = REPO_ROOT / "extracted" / "census-2001" / "c01-population-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "pop-share.csv"
CANONICALIZER_VERSION = "2.0.0"

NAMED = ("hindu", "muslim", "christian", "sikh", "buddhist", "jain")
DENOMINATOR = "all_persons_at_geography_total_residence"

# SECONDARY (manual entry). Census of India decadal religion proportions, % of
# total population, all-India. Standard published Census series (RGI; reproduced
# by Pew 2021 and en.wikipedia.org/wiki/Religion_in_India), cross-checked against
# this repo's primary C-01 at 2001/2011. 1951 omitted (post-Partition coverage +
# unreliable small-community figures).
DECADAL_SECONDARY = {
    1961: {"hindu": 83.45, "muslim": 10.69, "christian": 2.44, "sikh": 1.79, "buddhist": 0.74, "jain": 0.46},
    1971: {"hindu": 82.73, "muslim": 11.21, "christian": 2.60, "sikh": 1.89, "buddhist": 0.70, "jain": 0.48},
    1981: {"hindu": 82.30, "muslim": 11.75, "christian": 2.44, "sikh": 1.92, "buddhist": 0.70, "jain": 0.47},
    1991: {"hindu": 81.53, "muslim": 12.61, "christian": 2.32, "sikh": 1.94, "buddhist": 0.77, "jain": 0.40},
}
COVERAGE = {
    1981: " 1981 excludes Assam (not enumerated).",
    1991: " 1991 excludes Jammu & Kashmir (not enumerated).",
}
SEC_NOTE = ("SECONDARY (manual entry): Census of India decadal religion proportion, "
            "cross-checked against primary C-01 at 2001/2011.")
RELIGION_RANK = {r: i for i, r in enumerate(NAMED)}


def _geo_2011(state_code: str, distt_code: str) -> tuple[str, str]:
    if state_code == "00" and distt_code == "000":
        return "national", "IN"
    if distt_code == "000":
        return "state", f"IN-S{state_code}"
    return "district", f"IN-S{state_code}-D{distt_code}"


def _read_2011():
    """(level, code, religion) -> persons, plus (level, code) -> all_persons."""
    persons: dict[tuple[str, str, str], int] = {}
    all_persons: dict[tuple[str, str], int] = {}
    files = sorted(L2_2011_DIR.glob(L2_2011_GLOB))
    if not files:
        raise SystemExit(f"no L2 files match {L2_2011_DIR / L2_2011_GLOB}")
    for fp in files:
        with fp.open() as f:
            for row in csv.DictReader(f):
                if row["residence"] != "total" or row["sex"] != "persons":
                    continue
                level, code = _geo_2011(row["state_code"], row["distt_code"])
                persons[(level, code, row["religion"])] = int(row["value"])
                if row["religion"] == "all":
                    all_persons[(level, code)] = int(row["value"])
    return persons, all_persons


def _read_2001_national() -> dict[str, int]:
    """religion -> national persons (residence=total, sex=persons)."""
    out: dict[str, int] = {}
    with L2_2001.open() as f:
        for row in csv.DictReader(f):
            if row["state_code"] != "00" or row["residence"] != "total" or row["sex"] != "persons":
                continue
            out[row["religion"]] = int(row["value"])
    return out


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-pop-share-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    persons_2011, all_2011 = _read_2011()
    nat_2001 = _read_2001_national()

    rows: list[list] = []

    def emit(level, code, year, religion, share, src_id, src_doc, note):
        rows.append([
            "pop-share", level, code, year, religion,
            round(share, 4), DENOMINATOR, "", "", "",
            src_id, src_doc, extraction_run, note, "false",
        ])

    # --- National decadal series, all six communities ---
    # 1961-1991: secondary manual-entry
    for year, shares in DECADAL_SECONDARY.items():
        note = SEC_NOTE + COVERAGE.get(year, "")
        for rel in NAMED:
            emit("national", "IN", year, rel, shares[rel],
                 "census-decadal-religion", "(manual entry — see methodology_note)", note)
    # 2001: primary C-01 2001
    all01 = nat_2001.get("all")
    if all01:
        for rel in NAMED:
            if rel in nat_2001:
                emit("national", "IN", 2001, rel, nat_2001[rel] / all01 * 100,
                     "census-india-2001", "sources/census-2001/c-series/c01-population-by-religion.xls",
                     "Share of total population (all residences combined), primary C-01 2001.")
    # 2011: primary C-01 2011
    all11 = all_2011.get(("national", "IN"))
    if all11:
        for rel in NAMED:
            p = persons_2011.get(("national", "IN", rel))
            if p is not None:
                emit("national", "IN", 2011, rel, p / all11 * 100,
                     "census-india-2011", "sources/census-2011/c-series/c01-population-by-religion.xls",
                     "Share of total population (all residences combined), primary C-01 2011.")

    # --- 2011 state + district Muslim share (geographic drill-down) ---
    for (level, code, religion), p in persons_2011.items():
        if religion != "muslim" or level == "national":
            continue
        denom = all_2011.get((level, code))
        if not denom:
            continue
        src_doc = ("sources/census-2011/c-series/state-mdds/c01-<state>.xls" if level == "district"
                   else "sources/census-2011/c-series/c01-population-by-religion.xls")
        emit(level, code, 2011, "muslim", p / denom * 100,
             "census-india-2011", src_doc,
             "Muslim share of total population (all residences combined).")

    level_rank = {"national": 0, "state": 1, "district": 2}
    rows.sort(key=lambda r: (level_rank[r[1]], r[2], r[3], RELIGION_RANK.get(r[4], 9)))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        w.writerows(rows)

    nat_years = sorted({r[3] for r in rows if r[1] == "national"})
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows; "
          f"national years {nat_years})")


if __name__ == "__main__":
    canonicalize()
