# Runbook: NSS education-spending surveys - 75th round (2017-18) + CMS:E (2025)

## Source identity

- Manifest entries: `nss75-education` + `education-2025` (manifest/sources.yaml)
- Surveys: Household Social Consumption: Education, NSS 75th round Sch
  25.2, July 2017 - June 2018 (1,13,757 households; 1,52,992 students aged
  3-35 currently attending; published as NSS Report 585) and the
  Comprehensive Modular Survey: Education (CMS:E), NSS 80th round, April -
  June 2025 (52,085 households; 57,742 students enrolled in school
  education; published as NSS Report 595, whose primary objective is
  estimating household expenditure on school education).
- Feeds: **`school-edu-spend`** - average expenditure per enrolled school
  student per academic year, excluding private coaching, by religion of
  household head (both publications stop at course type, level, school
  type and state, never religion).

## The two distribution channels

The NADA catalog ships the 75th round ONLY as a proprietary `.Nesstar`
binary (id 151; banked in `sources/nada/education-2017-18/`); the parseable
official channel is MoSPI's original fixed-width TXT distribution, still
served from the unlinked Drupal-era directory
`mospi.gov.in/sites/default/files/NSS75252E/` (8 files `R75252L01..L08.TXT`
+ `KI_Education_75th_Final.pdf`, the validation-anchor report). URLs +
sha256: `sources/nss75-education/PROVENANCE-note.md`; the ~170 MB stays
local at `~/Desktop/nada-work/education-2017-18-alt/`.

CMS:E 2025 is a normal NADA API pull (id 255, CSV distribution with
descriptive headers, 3 files; `sources/nada/education-2025/`; ~27 MB local
at `~/Desktop/nada-work/education-2025/`). NSS Report 595 carrying the
published anchors is banked alongside.

## How to recompute

```bash
# L1 -> L2 (gates: 2017 aborts unless all 27 cells of Report 585
# Statements 19 + 21 reproduce within 0.5%; 2025 aborts unless all 7
# Report 595 per-student cells reproduce within 0.5%. Observed worst gap
# in both: 0.01%.)
.venv/bin/python transform/education/extract_education_2017_by_religion.py
.venv/bin/python transform/education/extract_education_2025_by_religion.py
# L2 -> L3
.venv/bin/python transform/canonicalize/school_edu_spend.py
```

Weights: 2017-18 = MLT/100 if NSS=NSC else MLT/200; 2025 = mult/100 flat.
Byte/column map and gotchas: `nada/education-layout-map.md`.

## What we publish (all-India, by religion of head, Rs nominal per student per academic year)

| religion | 2017-18 | 2025 |
|---|---|---|
| Muslim | 5,532 | 9,249 |
| Hindu | 7,050 | 12,941 |
| all-India | 7,041 | 12,616 |

The Muslim household spends about 72% of what the Hindu household spends
per school student in 2025, down from 78% in 2017-18. School choice is not
the driver: government-school shares are nearly equal (2025 Muslim 55.4%
vs Hindu 56.5%) - the gap comes from how much families spend in whichever
school they use (fees, books, transport). Private coaching, the excluded
companion, averages another INR 2,409 per student in 2025 (collected
separately in both rounds).

## Caveats (NSO unit-data rider + the break flag)

Religion is self-reported and unverified; the survey is stratified for
states, not religions - the split is indicative, no sub-state estimates.
Values are nominal rupees of each round (no deflation). The 2025 rows
carry break_flag=true (dashed connector): Report 595's own comparability
section (1.2) lists concept revisions vs the 75th round - CMS:E covers
school education only, counts anganwadi enrolment as pre-primary (the 75th
classed it as non-formal), takes age 3+ rather than 3-35, and itemises
coaching - so the step between rounds is indicative. The 75th leg is
aligned as far as the instruments allow: school levels only, coaching
excluded. The 71st round (2014) education survey is banked but
Nesstar-locked (the Windows-VM unlock set).

## Higher-education attendance (`ger-higher-ed`), same NSS 75th round (Commit GO)

The same 75th 25.2 microdata also feeds the rebuilt `ger-higher-ed` card (it
replaced the AISHE administrative GER, an undercount: AISHE tags only ~7% of
enrolment to a religion, reading an impossible ~13% for the educated
Christian/Sikh/Jain group, and carries no Hindu figure). The construct is the
NSS Gross Attendance Ratio for "post higher secondary": persons currently
attending graduate or postgraduate study over the population aged 18-23.

```bash
# L1 -> L2 (gate: reproduces all 9 NSS Report 585 Statement 8 cells
# - post higher secondary GAR, rural/urban/all x male/female/person -
# to <=0.25pp; observed worst 0.05pp. Aborts, writes nothing, if breached.)
.venv/bin/python transform/education/extract_higher_ed_gar_2017_by_religion.py
# L2 -> L3
.venv/bin/python transform/canonicalize/ger_higher_ed.py
```

- Numerator = L05 (currently attending) "level of current enrolment" codes 15
  (graduate) + 16 (postgraduate & above), any age. Code 14 (diploma/certificate
  at graduation level) is EXCLUDED: it overshoots the published cells by ~6%;
  {15,16} are "post higher secondary" in the GAR ladder. Denominator = L04
  (person roster) persons aged 18-23. Gender for the numerator joins L05->L04 on
  person serial (40-41); religion via the L02 household key. Byte map +
  derivation: the extractor docstring + `nada/education-layout-map.md`.
- The published statement never splits by religion (as with school-spend), so
  the religion split is the validated pipeline applied to the religion-of-head
  variable: Muslim 14.5% / Hindu 24.2% / Christian 28.3% / Sikh 24.1% / all 22.8%.
- ONE validated round = a SNAPSHOT. PLFS has a single looser "current attendance"
  code, publishes no attendance ratio, and runs ~8pp high for 2017-18 (a 37%
  larger numerator, incl. implausible under-18 "graduates"), so it is not a
  validatable trend source; the 71st (2014) round is Nesstar-locked.
