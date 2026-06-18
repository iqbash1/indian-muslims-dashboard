"""
L2 -> L3 for the `ger-higher-ed` metric: higher-education attendance by religion.

Reads:
  extracted/education/higher-ed-gar-2017-by-religion.csv   (NSS 75th, validated)
Writes:
  canonical/ger-higher-ed.csv

WHY NSS, NOT AISHE. The card used to read the AISHE administrative GER. AISHE
tags only ~7% of all enrolment to a religion (one "Muslim Minority" cell + one
grouped "Other Minority Community"), so the Muslim GER (~9-10%) was an
UNDERCOUNT, not comparable to the fully-counted national figure, and AISHE
publishes no Hindu figure at all. The tell: AISHE put "other minorities"
(Christian, Sikh, Jain - among India's most educated communities) at ~13%, which
cannot be their true rate. A household survey samples everyone and asks religion,
so Muslim, Hindu and all-India sit on ONE basis. The numbers move accordingly:
AISHE Muslim 9.8% becomes a validated 14.5%; the gap to Hindu (24.2%) is real and
about 60% of the Hindu rate, not the "third of the national rate" the AISHE
comparison implied.

THE CONSTRUCT. NSS Gross Attendance Ratio for "post higher secondary": persons
CURRENTLY ATTENDING graduate or postgraduate study (any age) over the population
aged 18-23, x100. NSS 75th round (Schedule 25.2, July 2017-June 2018) unit-level
data; gated against NSS Report 585 Statement 8 to <=0.05pp on all nine all-India
cells (see transform/education/extract_higher_ed_gar_2017_by_religion.py). One
validated round = a snapshot: PLFS publishes no attendance ratio and runs ~8pp
high for the same year, and the 71st (2014) education round is Nesstar-locked, so
there is no validatable trend.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
GAR_L2 = REPO_ROOT / "extracted" / "education" / "higher-ed-gar-2017-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "ger-higher-ed.csv"
CANONICALIZER_VERSION = "3.0.0"

SOURCE_ID = "nss75-education"
SOURCE_DOC = "sources/nss75-education/PROVENANCE-note.md"
YEAR = 2017                       # NSS 75th round, July 2017 - June 2018
# Carded communities: well-sampled enough to stand behind (Muslim 10,478 and
# Hindu 54,593 in the 18-23 base; Christian 4,414; Sikh 1,796). Jain (184) and
# Buddhist (689) are computed by the extractor but too thin to show.
CARDED = ("muslim", "hindu", "christian", "sikh", "all")

NOTE_MAIN = (
    "Household-survey Gross Attendance Ratio: persons currently attending higher "
    "education (graduate or postgraduate study; NSS 'level of current enrolment' "
    "codes 15-16, of any age) over the population aged 18-23, x100. NSS 75th round "
    "(Schedule 25.2, July 2017-June 2018) unit-level data. Replaces the AISHE "
    "administrative GER, which tagged only ~7% of enrolment to a religion and so "
    "undercounted every community (its 'other minorities' read an implausible 13% "
    "for Christians/Sikhs/Jains) and carried no Hindu figure; a household survey "
    "asks every family directly, so Muslim, Hindu and all-India sit on one basis. "
    "The pipeline reproduces all nine published Statement 8 cells (post higher "
    "secondary GAR, rural/urban/all x male/female/person) of NSS Report 585 to "
    "within 0.05pp; the statement does not split by religion, so the religion "
    "split is that validated pipeline applied to the religion-of-head variable. "
    "Weight MLT/200 (sub-sample-combined). Religion is self-reported; the survey "
    "is stratified for states, not religions, so the split is indicative."
)
NOTE_SEX = (
    "By-sex Gross Attendance Ratio (graduate + postgraduate attendance over the "
    "18-23 population), NSS 75th round 2017-18 unit data; same validated pipeline "
    "as the headline figure, reproducing the published all-India male 24.7 / female "
    "20.7 (Statement 8) to <=0.05pp."
)


def main() -> None:
    rows = {(r["religion"], r["sex"], r["residence"]): r
            for r in csv.DictReader(GAR_L2.open())}
    extraction_run = (
        f"canonicalize-ger-higher-ed-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    out: list[list] = []

    def emit(religion: str, sex: str, note: str) -> None:
        r = rows.get((religion, "person" if sex == "all" else sex, "all"))
        if not r:
            return
        out.append([
            "ger-higher-ed", "national", "IN", YEAR, religion, sex,
            f"{float(r['gar_pct']):.1f}", "persons_age_18_23", r["n_pop_18_23"],
            "", "", SOURCE_ID, SOURCE_DOC, extraction_run, note, "false",
        ])

    for rel in CARDED:                       # headline community snapshot
        emit(rel, "all", NOTE_MAIN)
    for rel in CARDED:                       # by-sex drill-down
        for sex in ("male", "female"):
            emit(rel, sex, NOTE_SEX)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "sex", "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run", "methodology_note", "break_flag",
        ])
        w.writerows(out)

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(out)} rows)")
    snap = {r[4]: r[6] for r in out if r[5] == "all"}
    print("  national GAR: " + ", ".join(f"{k} {v}%" for k, v in snap.items()))


if __name__ == "__main__":
    main()
