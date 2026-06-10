"""
L2 -> L3 for the `ger-higher-ed` metric (Gross Enrolment Ratio, higher education).

Reads:
  extracted/aishe/aishe-2021-22-table15-state-minority-enrolment.csv  (year 2021)
  extracted/aishe/aishe-2020-21-table15-state-minority-enrolment.csv  (year 2020)
  extracted/census-2011/c15-national-age-by-religion.csv              (denominator)
  extracted/census-2011/c15-religion-by-age-sex.csv                   (by-sex/state denom)
  canonical/muslim-higher-ed-enrolment.csv                            (by-sex/state numerator)
Writes:
  canonical/ger-higher-ed.csv

GER (the official AISHE definition) = student enrolment in higher education /
population in the 18-23 age group * 100. We use Census 2011 C-15 5-year bands
(15-19 + 20-24 = 10 years) scaled by 0.6 as an 18-23 effective population
proxy. Census 2021 was deferred, so the 2011 cohort is the cleanest primary
denominator available, and it is held FIXED across both AISHE years; the
over-time movement is therefore the enrolment numerator alone (the cross-
religion gap, the dashboard story, is robust to the denominator choice).

Two AISHE rounds give a short over-time series (academic years 2020-21 and
2021-22, labelled years 2020 and 2021). Per-round national numerators:
  - Muslim + Other Minority All-India enrolment come from each report's Table 15
    All-India row (extracted/aishe/aishe-<yr>-...csv, serial 0). The 2020-21 row
    was recovered by character-level de-interleaving and equals the exact sum of
    its 36 state rows; the 2021-22 row is the published aggregate (its non-Muslim
    All-India cells were dropped by the text layer, so Other-Minority and the
    minority-by-sex split for that year come from the report's prose instead).
  - Total enrolment is the report prose headline: 4,32,68,181 (2021-22 p29) and
    4,13,80,713 (2020-21 p30).

Validated: published AISHE National GER = 28.4% (2021-22, MoSPI projections);
our 2011-denominator computation sits ~2-3pp above because the 2011 cohort is
smaller than the projected 2021 cohort. The Muslim-vs-national gap of roughly
half is the story.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
AISHE_DIR = REPO_ROOT / "extracted" / "aishe"
C15_L2 = REPO_ROOT / "extracted" / "census-2011" / "c15-national-age-by-religion.csv"
C15_SEX_L2 = REPO_ROOT / "extracted" / "census-2011" / "c15-religion-by-age-sex.csv"
MUSLIM_ENROL_L3 = REPO_ROOT / "canonical" / "muslim-higher-ed-enrolment.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "ger-higher-ed.csv"
CANONICALIZER_VERSION = "2.0.0"

# Single-year-age proxy factor: 18-23 (6 years) / 15-24 (10 years) under the
# assumption that single-year cohorts are roughly uniform within each 5-year band.
AGE_PROXY_FACTOR = 0.6

# AISHE's "Other Minority Community" = Christian, Sikh, Buddhist, Jain, Parsi
# (always grouped; AISHE never breaks them out individually). The matching
# Census denominator sums the four sizeable ones present in Census C-15.
OTHER_MINORITY_DENOM = ("christian", "sikh", "buddhist", "jain")

# Per-round published national figures the Table-15 L2 cannot supply directly.
#   total_enrol            : report-prose headline total enrolment (for national GER)
#   othmin_total_fallback  : All-India Other-Minority enrolment from prose, used only
#                            when the L2 All-India row lacks the non-Muslim cells
#   minority_male/female   : All-India total Minority enrolment by sex from prose;
#                            other-minority-by-sex = this minus Muslim-by-sex
# 2020-21's L2 carries all of these in the recovered All-India row, so its fallbacks
# are None (everything is read from the table).
ROUNDS = [
    {
        "year": 2021, "ay": "2021-22",
        "l2": AISHE_DIR / "aishe-2021-22-table15-state-minority-enrolment.csv",
        "report_doc": "sources/aishe/aishe-report-2021-22.pdf",
        "total_enrol": 43_268_181, "total_enrol_page": 29,
        "othmin_total_fallback": 905_159,
        "minority_male": 1_496_191, "minority_female": 1_517_001,
    },
    {
        "year": 2020, "ay": "2020-21",
        "l2": AISHE_DIR / "aishe-2020-21-table15-state-minority-enrolment.csv",
        "report_doc": "sources/aishe/aishe-report-2020-21.pdf",
        "total_enrol": 41_380_713, "total_enrol_page": 30,
        "othmin_total_fallback": None,
        "minority_male": None, "minority_female": None,
    },
]


def aishe_allindia(l2_path: pathlib.Path) -> tuple[dict, str]:
    """All-India (serial 0) Muslim + Other-Minority cells from a Table-15 L2.
    Values are the published aggregate, NOT a sum of state rows. Cells absent from
    the text layer come back as None."""
    for row in csv.DictReader(l2_path.open()):
        if (row.get("serial") or "").strip() == "0" and (row.get("state_name") or "").strip().lower() == "all india":
            def g(k: str):
                v = row.get(k)
                return int(v) if v not in (None, "") else None
            cells = {k: g(k) for k in (
                "muslim_male", "muslim_female", "muslim_total",
                "other_minority_male", "other_minority_female", "other_minority_total")}
            return cells, row["source_document"]
    raise RuntimeError(f"All India row not found in {l2_path}")


def population_18_23(religion: str) -> int:
    """0.6 * (15-19 + 20-24) for a given religion, national total residence."""
    p = 0
    for row in csv.DictReader(C15_L2.open()):
        if row["religion"] != religion:
            continue
        if row["age_group"] in ("15-19", "20-24"):
            p += int(row["persons"])
    return round(p * AGE_PROXY_FACTOR)


_C15_SEX_ROWS: list | None = None


def _c15_sex_rows() -> list:
    global _C15_SEX_ROWS
    if _C15_SEX_ROWS is None:
        _C15_SEX_ROWS = list(csv.DictReader(C15_SEX_L2.open()))
    return _C15_SEX_ROWS


def population_18_23_cut(religions, state_code: str = "00", sex: str = "persons") -> int:
    """0.6 x (15-19 + 20-24) summed over `religions` for one state_code + sex,
    residence=total, from Census C-15 (age x sex x religion). state_code '00' is
    All India; sex in {'persons','males','females'}."""
    p = 0
    for r in _c15_sex_rows():
        if (r["state_code"] == state_code and r["residence"] == "total"
                and r["sex"] == sex and r["religion"] in religions
                and r["age_group"] in ("15-19", "20-24")):
            p += int(r["value"])
    return round(p * AGE_PROXY_FACTOR)


def muslim_enrolment_by_sex(year: int) -> tuple[int, int]:
    """National Muslim (male, female) enrolment for one year from the canonical
    count metric (itself AISHE Table 15)."""
    m = f = None
    for r in csv.DictReader(MUSLIM_ENROL_L3.open()):
        if r["geography_level"] == "national" and r["religion"] == "muslim" and int(r["year"]) == year:
            if r["sex"] == "male":
                m = int(float(r["value"]))
            elif r["sex"] == "female":
                f = int(float(r["value"]))
    if m is None or f is None:
        raise RuntimeError(f"Muslim national male/female enrolment not found for {year}")
    return m, f


def muslim_enrolment_by_state(year: int) -> dict[str, int]:
    """{geography_code: enrolment} for Muslim state rows for one year."""
    out: dict[str, int] = {}
    for r in csv.DictReader(MUSLIM_ENROL_L3.open()):
        if (r["geography_level"] == "state" and r["religion"] == "muslim"
                and int(r["year"]) == year and r.get("sex", "all") in ("all", "")):
            out[r["geography_code"]] = int(float(r["value"]))
    return out


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-ger-higher-ed-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    # Denominators are the FIXED Census 2011 cohort, shared by every round.
    muslim_pop = population_18_23("muslim")
    all_pop = population_18_23("all")
    othmin_pop = sum(population_18_23(r) for r in OTHER_MINORITY_DENOM)
    sex_pop = {  # (religions, sex) -> 18-23 proxy
        ("muslim", "male"): population_18_23_cut(("muslim",), "00", "males"),
        ("muslim", "female"): population_18_23_cut(("muslim",), "00", "females"),
        ("othmin", "male"): population_18_23_cut(OTHER_MINORITY_DENOM, "00", "males"),
        ("othmin", "female"): population_18_23_cut(OTHER_MINORITY_DENOM, "00", "females"),
    }

    out_rows: list[list] = []
    summary: list[str] = []
    for rd in ROUNDS:
        year, ay = rd["year"], rd["ay"]
        ai, aishe_src_doc = aishe_allindia(rd["l2"])
        muslim_enrol = ai["muslim_total"]
        total_enrol = rd["total_enrol"]
        othmin_enrol = ai["other_minority_total"] if ai["other_minority_total"] is not None else rd["othmin_total_fallback"]

        muslim_ger = round(muslim_enrol / muslim_pop * 100, 2)
        national_ger = round(total_enrol / all_pop * 100, 2)
        othmin_ger = round(othmin_enrol / othmin_pop * 100, 2)

        note_common = (
            f"Numerator: AISHE {ay} enrolment. Denominator: Census 2011 C-15 "
            f"population (15-19 + 20-24) x {AGE_PROXY_FACTOR} as an 18-23 proxy, "
            f"held fixed across rounds (Census 2021 deferred). Published national "
            f"GER {ay} approx 28% (MoSPI projected denominator); our 2011-denominator "
            f"computation sits a few pp above. The Muslim-vs-national gap is the "
            f"story and is robust to the denominator. Total enrolment "
            f"{total_enrol:,} from the AISHE {ay} Report p{rd['total_enrol_page']} "
            f"prose. Muslim enrolment is the All-India 'Muslim Minority' Table 15 "
            f"total (the official aggregate, not a sum of state rows)."
        )

        out_rows.append([
            "ger-higher-ed", "national", "IN", year, "muslim", "all", muslim_ger,
            f"population_18_23_{muslim_pop}", muslim_enrol, "", "",
            "aishe", aishe_src_doc, extraction_run,
            f"{note_common} Muslim numerator: {muslim_enrol:,}; Muslim 18-23 "
            f"proxy: {muslim_pop:,}.", "false",
        ])
        out_rows.append([
            "ger-higher-ed", "national", "IN", year, "all", "all", national_ger,
            f"population_18_23_{all_pop}", total_enrol, "", "",
            "aishe", rd["report_doc"], extraction_run,
            f"{note_common} National numerator: {total_enrol:,}; "
            f"national 18-23 proxy: {all_pop:,}.", "false",
        ])
        out_rows.append([
            "ger-higher-ed", "national", "IN", year, "other_minority", "all", othmin_ger,
            f"population_18_23_{othmin_pop}", othmin_enrol, "", "",
            "aishe", aishe_src_doc, extraction_run,
            "AISHE groups every non-Muslim minority into one 'Other Minority "
            "Community' (Christian, Sikh, Buddhist, Jain, Parsi) and never splits "
            "them, so this is the finest community comparison the source allows. "
            f"Numerator: All-India Other Minority enrolment ({othmin_enrol:,}) for "
            f"{ay}. Denominator: Census 2011 C-15 (15-19 + 20-24) x {AGE_PROXY_FACTOR}, "
            f"summed over Christian, Sikh, Buddhist and Jain "
            f"({othmin_pop:,}).", "false",
        ])

        # national by sex: Muslim + Other minorities, male and female
        mus_m, mus_f = muslim_enrolment_by_sex(year)
        if ai["other_minority_male"] is not None:
            om_m, om_f = ai["other_minority_male"], ai["other_minority_female"]
            sex_src = (f"By-sex GER: All-India Muslim and Other-Minority enrolment by "
                       f"sex from the recovered AISHE {ay} Table 15 row, over Census "
                       f"2011 C-15 18-23 population by sex.")
        else:
            om_m = rd["minority_male"] - mus_m
            om_f = rd["minority_female"] - mus_f
            sex_src = (f"By-sex GER: published All-India Minority enrolment by sex "
                       f"(AISHE {ay} Report prose) over Census 2011 C-15 18-23 "
                       f"population by sex; other minorities by sex = total Minority "
                       f"minus Muslim.")
        for rel, enrol_pair, denom_key in (
                ("muslim", (mus_m, mus_f), "muslim"),
                ("other_minority", (om_m, om_f), "othmin")):
            for i, sex_key in enumerate(("male", "female")):
                enrol = enrol_pair[i]
                d = sex_pop[(denom_key, sex_key)]
                out_rows.append([
                    "ger-higher-ed", "national", "IN", year, rel, sex_key,
                    round(enrol / d * 100, 2), f"population_18_23_{d}", enrol, "", "",
                    "aishe", aishe_src_doc, extraction_run, sex_src, "false",
                ])

        # by state: Muslim GER (both sexes)
        state_note = (
            f"Per-state Muslim GER: Muslim enrolment as reported by each state to "
            f"AISHE {ay} over Census 2011 C-15 Muslim 18-23 by state. States report "
            f"minority enrolment with varying completeness, so read the spread "
            f"across states, not the precise level."
        )
        n_states = 0
        for code, enrol in sorted(muslim_enrolment_by_state(year).items()):
            d = population_18_23_cut(("muslim",), code.split("-S")[-1], "persons")
            if not d:
                continue
            out_rows.append([
                "ger-higher-ed", "state", code, year, "muslim", "all",
                round(enrol / d * 100, 2), f"population_18_23_{d}", enrol, "", "",
                "aishe", aishe_src_doc, extraction_run, state_note, "false",
            ])
            n_states += 1
        summary.append(f"  {ay}: muslim {muslim_ger}%, other-min {othmin_ger}%, "
                       f"all {national_ger}%; {n_states} states")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "sex", "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run", "methodology_note", "break_flag",
        ])
        w.writerows(out_rows)

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(out_rows)} rows)")
    print("\n".join(summary))


if __name__ == "__main__":
    canonicalize()
