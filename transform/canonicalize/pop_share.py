"""
L2 -> L3 for the `pop-share` metric — share of each religious community in
India's population.

NATIONAL decadal series (1961 -> 2011), the six major communities. All
six rounds are now PRIMARY (Commit AJ — census-decadal-religion secondary
retired):

  1961  extracted/census-1961/c07-religion.csv — RGI Social and Cultural
        Tables Vol-XIII INDIA Table C-VII (NADA cat 32022). Includes J&K.
  1971  extracted/census-1971/religion-summary.csv — RGI Paper 2 of 1972
        (NADA cat 31626). Six named religions only — denominator is
        sum-of-six-named, so shares run ~0.04pp higher than the universally
        cited published shares (which divide by India total including
        "Others" residual).
  1981  extracted/census-1981/hh15-religion.csv — RGI Paper 3 of 1984 HH-15
        (NADA cat 30879). EXCLUDES Assam (Census not held there in 1981).
  1991  extracted/census-1991/c09-religion.csv — RGI C-9 XLSX (NADA cat
        35737). EXCLUDES J&K (Census not held there in 1991). Differs from
        the universally cited 12.61% Muslim 1991 share (which RGI
        interpolated J&K back into) by ~0.5pp — our value is 12.12%.
  2001  extracted/census-2001/c01-population-by-religion.csv
  2011  extracted/census-2011/c01-population-by-religion*.csv

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
L2_1991 = REPO_ROOT / "extracted" / "census-1991" / "c09-religion.csv"
L2_1981 = REPO_ROOT / "extracted" / "census-1981" / "hh15-religion.csv"
L2_1971 = REPO_ROOT / "extracted" / "census-1971" / "religion-summary.csv"
L2_1961 = REPO_ROOT / "extracted" / "census-1961" / "c07-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "pop-share.csv"
CANONICALIZER_VERSION = "4.0.0"

NAMED = ("hindu", "muslim", "christian", "sikh", "buddhist", "jain")
DENOMINATOR = "all_persons_at_geography_total_residence"
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


def _read_1991_national() -> dict[str, int]:
    """religion -> national persons (excl J&K). Reads area_level=national, residence=total, sex=persons."""
    out: dict[str, int] = {}
    with L2_1991.open() as f:
        for row in csv.DictReader(f):
            if row.get("area_level") != "national" or row["residence"] != "total" or row["sex"] != "persons":
                continue
            out[row["religion"]] = int(row["value"])
    return out


def _read_1971_national() -> dict[str, int]:
    """religion -> national persons. 1971 Summary has 6 named religions only — no 'all' column."""
    out: dict[str, int] = {}
    with L2_1971.open() as f:
        for row in csv.DictReader(f):
            if row.get("area_level") != "national" or row["sex"] != "persons":
                continue
            out[row["religion"]] = int(row["value"])
    return out


def _read_1981_national() -> dict[str, int]:
    """religion -> national persons (Total residence, excl Assam)."""
    out: dict[str, int] = {}
    with L2_1981.open() as f:
        for row in csv.DictReader(f):
            if row.get("area_level") != "national" or row["residence"] != "total" or row["sex"] != "persons":
                continue
            out[row["religion"]] = int(row["value"])
    return out


def _read_1961_national() -> dict[str, int]:
    """religion -> national persons (Total residence, India)."""
    out: dict[str, int] = {}
    with L2_1961.open() as f:
        for row in csv.DictReader(f):
            if row.get("area_level") != "national" or row["residence"] != "total" or row["sex"] != "persons":
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
    nat_1991 = _read_1991_national()
    nat_1981 = _read_1981_national()
    nat_1971 = _read_1971_national()
    nat_1961 = _read_1961_national()

    rows: list[list] = []

    def emit(level, code, year, religion, share, src_id, src_doc, note):
        rows.append([
            "pop-share", level, code, year, religion,
            round(share, 4), DENOMINATOR, "", "", "",
            src_id, src_doc, extraction_run, note, "false",
        ])

    # --- National decadal series, all six communities ---
    # 1961: primary C-VII, India total (includes J&K + most areas)
    all61 = nat_1961.get("all")
    if all61:
        note_61 = (
            "PRIMARY: RGI Social and Cultural Tables Vol-XIII INDIA Table C-VII "
            "Religion (A. Mitra RGI, Census 1961; NADA cat 32022). INDIA T row at "
            "PDF pp 501-502. Includes J&K. Some small territories (NEFA ~38k persons) "
            "not religion-canvassed are in the Total denominator but not in the "
            "religion numerators — net effect on share <0.07%."
        )
        for rel in NAMED:
            p = nat_1961.get(rel)
            if p is not None:
                emit("national", "IN", 1961, rel, p / all61 * 100,
                     "census-india-1961", "sources/census-1961/social-cultural-tables-c07-religion.pdf",
                     note_61)
    # 1971: primary, sum-of-6-named denominator
    if nat_1971:
        all71 = sum(nat_1971[rel] for rel in NAMED if rel in nat_1971)
        note_71 = (
            "PRIMARY: RGI 1972 Religion Paper (Series-1, India, by A. Chandra Sekhar), "
            "Summary table at p.xiii / NADA PDF p17. Denominator is the sum of the six "
            "named religions (Hindu/Muslim/Christian/Sikh/Buddhist/Jain) — 'Other religions "
            "and persuasions' is not in the Summary, so this share runs ~0.04pp higher than "
            "the universally-cited published share (which divides by India total including "
            "Others)."
        )
        for rel in NAMED:
            if rel in nat_1971:
                emit("national", "IN", 1971, rel, nat_1971[rel] / all71 * 100,
                     "census-india-1971", "sources/census-1971/religion-paper-2-of-1972.pdf",
                     note_71)
    # 1981: primary HH-15, India total EXCLUDES Assam (Census not held there)
    all81 = nat_1981.get("all")
    if all81:
        note_81 = (
            "PRIMARY: RGI Paper 3 of 1984 (V.S. Verma RGI) Table HH-15, Household "
            "Population by Religion of Head of Household (NADA cat 30879). India figure "
            "EXCLUDES Assam (Census not held there in 1981). Share is religion_persons / "
            "India-excl-Assam total."
        )
        for rel in NAMED:
            p = nat_1981.get(rel)
            if p is not None:
                emit("national", "IN", 1981, rel, p / all81 * 100,
                     "census-india-1981", "sources/census-1981/paper-3-of-1984-hh15-religion.pdf",
                     note_81)
    # 1991: primary C-9 XLSX, EXCLUDES J&K (Census not held there)
    all91 = nat_1991.get("all")
    if all91:
        note_91 = (
            "PRIMARY: RGI 1991 C-9 Religion XLSX (NADA catalog 35737). India figure "
            "EXCLUDES Jammu & Kashmir (Census was not held there in 1991). Share is "
            "religion_persons / India-excl-J&K total. This differs from the universally-"
            "cited published 1991 share (which uses RGI's J&K-interpolated all-India total) "
            "— the difference is ~0.5pp for Muslim (12.12% here vs 12.61% published) because "
            "J&K's ~68% Muslim composition shifts the all-India share notably when J&K is "
            "interpolated back in."
        )
        for rel in NAMED:
            p = nat_1991.get(rel)
            if p is not None:
                emit("national", "IN", 1991, rel, p / all91 * 100,
                     "census-india-1991", "sources/census-1991/c09-religion.xlsx", note_91)
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
