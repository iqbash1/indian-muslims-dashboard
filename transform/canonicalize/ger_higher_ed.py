"""
L2 -> L3 for the `ger-higher-ed` metric (Gross Enrolment Ratio, higher education).

Reads:
  extracted/aishe/aishe-2021-22-table15-state-minority-enrolment.csv  (Muslim)
  extracted/census-2011/c15-national-age-by-religion.csv              (denominator)
Writes:
  canonical/ger-higher-ed.csv

GER (the official AISHE definition) = student enrolment in higher education /
population in the 18-23 age group * 100. We use Census 2011 C-15 5-year bands
(15-19 + 20-24 = 10 years) scaled by 0.6 as a 18-23 effective population
proxy — Census 2021 was deferred, so the 2011 cohort is the cleanest primary
denominator available. This understates the 2021-22 actual cohort by ~5-7%
(MoSPI projections show the 18-23 cohort grew slightly between 2011 and 2021),
so our computed GER sits a touch ABOVE the published MoSPI GER. The cross-
religion comparison (the dashboard story) is unaffected by the level shift —
the Muslim-vs-national gap is robust to the choice of denominator.

AISHE national-total source:
  AISHE 2021-22 Report (sources/aishe/aishe-report-2021-22.pdf), page 29
  prose: "The total estimated enrolment in Higher Education Institutions is
  4,32,68,181" = 43,268,181.
The Muslim total is the published All-India "Muslim Minority" enrolment row
(serial 0) from the Table 15 L2 extraction — NOT a sum of the state rows. The
published All-India aggregate (2,108,033) exceeds the sum of the listed state
rows (~1.77 M) because some states report minority enrolment incompletely; the
official All-India figure is the authoritative one (cross-checked: 2,108,033 =
4.87% of 4,32,68,181 total enrolment, AISHE 2021-22).

Validated: published AISHE 2021-22 National GER = 28.4% (MoSPI projections);
our 2011-denominator computation = ~31% (the +2.6pp shift attributable to the
older denominator). The Muslim-vs-national gap of roughly half is the story.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
AISHE_L2 = REPO_ROOT / "extracted" / "aishe" / "aishe-2021-22-table15-state-minority-enrolment.csv"
C15_L2 = REPO_ROOT / "extracted" / "census-2011" / "c15-national-age-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "ger-higher-ed.csv"
CANONICALIZER_VERSION = "1.0.0"

# Primary number from AISHE 2021-22 Report p29 prose.
AISHE_TOTAL_ENROLMENT_2021_22 = 43_268_181
AISHE_REPORT_DOC = "sources/aishe/aishe-report-2021-22.pdf"
AISHE_REPORT_PAGE = 29

# Single-year-age proxy factor: 18-23 (6 years) / 15-24 (10 years) under the
# assumption that single-year cohorts are roughly uniform within each 5-year band.
AGE_PROXY_FACTOR = 0.6


def aishe_muslim_national() -> tuple[int, str]:
    """Return the published Muslim national enrolment row (serial=0, state=All India)
    from the AISHE Table 15 L2 — NOT a sum-of-states (the L2 carries both the
    state breakdown AND the published All India aggregate, and the published
    aggregate exceeds the state sum by ~17% due to states with incomplete
    minority reporting)."""
    src_doc = ""
    for row in csv.DictReader(AISHE_L2.open()):
        src_doc = row["source_document"]
        if (row.get("serial") or "").strip() == "0" and (row.get("state_name") or "").strip().lower() == "all india":
            return int(row["muslim_total"]), src_doc
    raise RuntimeError("All India row not found in AISHE L2")


# AISHE's "Other Minority Community" = Christian, Sikh, Buddhist, Jain, Parsi
# (always grouped; AISHE never breaks them out individually). The matching
# Census denominator sums the four sizeable ones present in Census C-15.
OTHER_MINORITY_DENOM = ("christian", "sikh", "buddhist", "jain")

# Published All-India "Other Minority Community" enrolment. AISHE 2021-22 Report
# prose: "...21,08,033 students belong to Muslim Minority and 9,05,159 are from
# other Minority Communities." The Table 15 All India row carries only the
# Muslim aggregate (other_minority blank there), so this national figure is
# taken from the report prose, the same provenance tier as the Muslim and
# total-enrolment published figures.
AISHE_OTHER_MINORITY_2021_22 = 905_159


def population_18_23(religion: str) -> int:
    """0.6 * (15-19 + 20-24) for a given religion, national total residence."""
    p = 0
    for row in csv.DictReader(C15_L2.open()):
        if row["religion"] != religion:
            continue
        if row["age_group"] in ("15-19", "20-24"):
            p += int(row["persons"])
    return round(p * AGE_PROXY_FACTOR)


# --- by-sex + by-state inputs (Census C-15 age x sex x religion + the canonical
#     Muslim enrolment counts) ---------------------------------------------------
C15_SEX_L2 = REPO_ROOT / "extracted" / "census-2011" / "c15-religion-by-age-sex.csv"
MUSLIM_ENROL_L3 = REPO_ROOT / "canonical" / "muslim-higher-ed-enrolment.csv"

# Published All-India Minority enrolment by sex, AISHE 2021-22 Report prose:
# "...14,96,191 are male students and 15,17,001 are female students" (total
# Minority Community). Other-minority by sex = total Minority minus Muslim.
TOTAL_MINORITY_MALE_2021_22 = 1_496_191
TOTAL_MINORITY_FEMALE_2021_22 = 1_517_001

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


def muslim_enrolment_by_sex() -> tuple[int, int]:
    """National Muslim (male, female) enrolment from the canonical count metric
    (itself AISHE Table 15)."""
    m = f = None
    for r in csv.DictReader(MUSLIM_ENROL_L3.open()):
        if r["geography_level"] == "national" and r["religion"] == "muslim":
            if r["sex"] == "male":
                m = int(float(r["value"]))
            elif r["sex"] == "female":
                f = int(float(r["value"]))
    if m is None or f is None:
        raise RuntimeError("Muslim national male/female enrolment not found")
    return m, f


def muslim_enrolment_by_state() -> dict[str, int]:
    """{geography_code: enrolment} for Muslim state rows (canonical count metric,
    AISHE Table 15 as reported by states)."""
    out: dict[str, int] = {}
    for r in csv.DictReader(MUSLIM_ENROL_L3.open()):
        if (r["geography_level"] == "state" and r["religion"] == "muslim"
                and r.get("sex", "all") in ("all", "")):
            out[r["geography_code"]] = int(float(r["value"]))
    return out


def canonicalize() -> None:
    muslim_enrol, aishe_src_doc = aishe_muslim_national()
    muslim_pop_18_23 = population_18_23("muslim")
    all_pop_18_23 = population_18_23("all")

    muslim_ger = round(muslim_enrol / muslim_pop_18_23 * 100, 2)
    national_ger = round(AISHE_TOTAL_ENROLMENT_2021_22 / all_pop_18_23 * 100, 2)

    othmin_enrol = AISHE_OTHER_MINORITY_2021_22
    othmin_pop_18_23 = sum(population_18_23(r) for r in OTHER_MINORITY_DENOM)
    othmin_ger = round(othmin_enrol / othmin_pop_18_23 * 100, 2)

    extraction_run = (
        f"canonicalize-ger-higher-ed-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    note_common = (
        f"Numerator: AISHE 2021-22 enrolment. Denominator: Census 2011 C-15 "
        f"population (15-19 + 20-24) × {AGE_PROXY_FACTOR} as an 18-23 proxy "
        f"(single-year-age table not pulled). Published national GER 2021-22 = "
        f"28.4% (MoSPI projected denominator); our 2011-denominator computation "
        f"sits ~2-3pp above due to projection vs Census gap. The Muslim-vs-"
        f"national gap is the story and is robust to the choice of denominator. "
        f"Total enrolment 4,32,68,181 from AISHE 2021-22 Report p29 prose. "
        f"Muslim enrolment is the published All-India 'Muslim Minority' total "
        f"from AISHE Table 15 (the official aggregate, not a sum of state rows)."
    )

    # Stage-2 drill-down inputs (by sex, by state).
    mus_m_enrol, mus_f_enrol = muslim_enrolment_by_sex()
    om_m_enrol = TOTAL_MINORITY_MALE_2021_22 - mus_m_enrol
    om_f_enrol = TOTAL_MINORITY_FEMALE_2021_22 - mus_f_enrol
    muslim_state_enrol = muslim_enrolment_by_state()
    sex_note = (
        "By-sex GER: published All-India Minority enrolment by sex (AISHE 2021-22 "
        "Report prose) over Census 2011 C-15 18-23 population by sex; other "
        "minorities by sex = total Minority minus Muslim."
    )
    state_note = (
        "Per-state Muslim GER: Muslim enrolment as reported by each state to "
        "AISHE 2021-22 over Census 2011 C-15 Muslim 18-23 by state. States report "
        "minority enrolment incompletely (the All-India total exceeds the state "
        "sum), so read the spread across states, not the precise level."
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "sex", "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run", "methodology_note", "break_flag",
        ])
        w.writerow([
            "ger-higher-ed", "national", "IN", 2021, "muslim", "all", muslim_ger,
            f"population_18_23_{muslim_pop_18_23}", muslim_enrol, "", "",
            "aishe", aishe_src_doc, extraction_run,
            f"{note_common} Muslim numerator: {muslim_enrol:,}; Muslim 18-23 "
            f"proxy: {muslim_pop_18_23:,}.", "false",
        ])
        w.writerow([
            "ger-higher-ed", "national", "IN", 2021, "all", "all", national_ger,
            f"population_18_23_{all_pop_18_23}", AISHE_TOTAL_ENROLMENT_2021_22, "", "",
            "aishe", AISHE_REPORT_DOC, extraction_run,
            f"{note_common} National numerator: {AISHE_TOTAL_ENROLMENT_2021_22:,}; "
            f"national 18-23 proxy: {all_pop_18_23:,}.", "false",
        ])
        w.writerow([
            "ger-higher-ed", "national", "IN", 2021, "other_minority", "all", othmin_ger,
            f"population_18_23_{othmin_pop_18_23}", othmin_enrol, "", "",
            "aishe", aishe_src_doc, extraction_run,
            "AISHE groups every non-Muslim minority into one 'Other Minority "
            "Community' (Christian, Sikh, Buddhist, Jain, Parsi) and never splits "
            "them, so this is the finest community comparison the source allows. "
            "Numerator: published All-India Other Minority enrolment (9,05,159) "
            "from AISHE 2021-22 Report prose alongside the Muslim Minority figure. "
            f"Denominator: Census 2011 C-15 (15-19 + 20-24) × {AGE_PROXY_FACTOR}, "
            f"summed over Christian, Sikh, Buddhist and Jain. Other-minority "
            f"numerator: {othmin_enrol:,}; 18-23 proxy: {othmin_pop_18_23:,}.", "false",
        ])
        # national by sex: Muslim + Other minorities, male and female
        n_rows = 3
        for sex_key, c15_sex in (("male", "males"), ("female", "females")):
            for rel, enrol, drels in (
                    ("muslim", mus_m_enrol if sex_key == "male" else mus_f_enrol, ("muslim",)),
                    ("other_minority", om_m_enrol if sex_key == "male" else om_f_enrol, OTHER_MINORITY_DENOM)):
                d = population_18_23_cut(drels, "00", c15_sex)
                w.writerow([
                    "ger-higher-ed", "national", "IN", 2021, rel, sex_key,
                    round(enrol / d * 100, 2), f"population_18_23_{d}", enrol, "", "",
                    "aishe", aishe_src_doc, extraction_run, sex_note, "false",
                ])
                n_rows += 1
        # by state: Muslim GER (both sexes)
        n_states = 0
        for code, enrol in sorted(muslim_state_enrol.items()):
            d = population_18_23_cut(("muslim",), code.split("-S")[-1], "persons")
            if not d:
                continue
            w.writerow([
                "ger-higher-ed", "state", code, 2021, "muslim", "all",
                round(enrol / d * 100, 2), f"population_18_23_{d}", enrol, "", "",
                "aishe", aishe_src_doc, extraction_run, state_note, "false",
            ])
            n_rows += 1
            n_states += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    print(f"  national all-sex: muslim {muslim_ger}%, other-min {othmin_ger}%, all {national_ger}%")
    print(f"  by sex: Muslim male {round(mus_m_enrol / population_18_23_cut(('muslim',), '00', 'males') * 100, 1)}% / female {round(mus_f_enrol / population_18_23_cut(('muslim',), '00', 'females') * 100, 1)}%")
    print(f"  by state: {n_states} states (Muslim GER, as-reported)")


if __name__ == "__main__":
    canonicalize()
