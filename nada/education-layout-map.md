# NSS education surveys byte/column map (75th Sch 25.2 2017-18 TXT, CMS:E 2025 CSV)

Positions sufficient to compute school-education expenditure per enrolled
student by religion of household head, weighted. Feeds `school-edu-spend`.

**Verified end-to-end 2026-06-11**: the 2017-18 estimator reproduces all 27
anchor cells of NSS Report 585 (Statement 19: total basic-course
expenditure per student by course type x sector, 9 cells; Statement 21: the
same by school level for general-course students, 18 cells) within 0.01%;
the 2025 estimator reproduces all seven Report 595 per-student cells within
0.01%. Extractors:
`transform/education/extract_education_201{7,2025}_by_religion.py` ->
`extracted/education/education-{2017,2025}-school-spend-by-religion.csv`.

## The construct (CMSE-aligned trend)

Average expenditure per student enrolled at SCHOOL levels during the
current academic year = course fee + books/stationery/uniform + transport +
other items, EXCLUDING private coaching (separate item/block in both
instruments; outside the CMS:E published headline). Denominator = all
enrolled school students (zero-expenditure students included). 75th school
levels = enrolment codes {06 pre-primary, 07 primary, 08 upper primary, 10
secondary, 11 higher secondary, 12 diploma upto secondary, 13 diploma
higher-secondary equivalent}; codes 03/04/05 (non-formal) have no
expenditure block, 14/15/16 (graduate+) are out of CMSE scope.

## 75th round (R75252L01..L08.TXT, record = 142 chars + CRLF)

8 levels = blocks: L01 blocks 1-2+11 (identification), L02 block 3
(household incl religion), L03 block 3.1 (former hostel members), L04 block
4 (person roster), L05 block 5 (education particulars of those currently
attending, 3-35), L06 block 6 (basic-course expenditure), L07 block 7
(persons 3-35 NOT currently attending), L08 block 8 (PGDM/PG diploma).
Weights/key identical to Sch 25.0: NSS 127-129, NSC 130-132, MLT 133-142;
**weight = MLT/100 if NSS == NSC else MLT/200**; household key =
FSU(4-8) + segment(31) + SSS(32) + hh(33-34); person serial 40-41 joins
L05 <-> L06 (152,992 vs 152,558 - 434 attending students carry no
expenditure record and stay out of the denominator, exactly reproducing
the published cells).

| Field | Level | Bytes (1-based) | Notes |
|---|---|---|---|
| Sector | any | 15 | 1 rural, 2 urban |
| Religion of head | L02 | 53 | 1 Hindu, 2 Islam, 3 Christian, 4 Sikh, 5 Jain, 6 Buddhist, 7 Zoroastrian, 9 other |
| Level of current enrolment | L05 | 51-52 | school = 06/07/08/10/11/12/13 |
| Course currently attending | L05 | 53-54 | general = 01-04, technical/professional = 05-19 |
| Type of institution | L05 | 59 | 1 govt, 2 private aided, 3 private unaided, 4 not known |
| Course fee | L06 | 45-52 | block 6 col 3 |
| Books, stationery, uniform | L06 | 53-60 | col 4 |
| Transport | L06 | 61-68 | col 5 |
| Private coaching | L06 | 69-76 | col 6 - EXCLUDED from the construct |
| Other expenditure | L06 | 77-84 | col 7 |
| Total (cols 3-7) | L06 | 85-92 | equals the item sum on every row |

## CMS:E 2025 (CMSE80HH25 / CMSE80PER25 / CMSE80PERST25.csv, descriptive headers)

- 52,085 households, 57,742 enrolled students (the Report 595 / press-note
  count reproduces on current members alone; CMSE80PERST25 = 1,675
  erstwhile hostel-resident students, OUTSIDE the published per-student
  tables - do not add them).
- **Weight = mult/100 flat.** Household key = fsu_serial_no +
  second_stage_stratum_no + sample_hhld_no; person -> household join is m:1.

| Field | File | Column |
|---|---|---|
| Sector | any | `sector` (1 rural, 2 urban) |
| Religion of head | HH | `religion` (same codes as 75th) |
| Enrolled in school | PER | `currently_enrolled_school` == 1 |
| School expenditure total | PER | `school_exp_total` (fee + transport + uniform + textbooks/stationery + other) |
| Private coaching total | PER | `private_coaching_exp_total` (separate block, excluded) |
| Type of school | PER | `school_type`: 1 govt, 2 private aided, 3 private unaided recognised, 4 private unaided unrecognised, 5 others |

## Gotchas

- Report 595's "Others" school-type bar (14,315) = codes 4 AND 5 combined;
  gating "others" on code 4 alone misses by ~2%.
- Report 595 Section 1.2 lists the concept revisions vs the 75th round
  (school-only coverage, anganwadi counted as pre-primary, age 3+ vs 3-35,
  itemised coaching) - the canonical 2025 rows carry break_flag=true, the
  card connector renders dashed.
- The 75th block-6 expenditure is filled only for formal levels (06-16);
  non-formal students (codes 03-05) have no expenditure rows and are
  outside both rounds' universes.
- 75th L03 (block 3.1) and L08 (block 8) are thin special-purpose rosters
  (former hostel members, PGDM holders) - not student frames.
- Unlike hospital costs, the religion gap here is NOT institution mix:
  government-school shares are nearly equal (2025 Muslim 55.4% vs Hindu
  56.5%; 2017-18 61.8% vs 61.1%) - the gap is in what is spent within
  school types.
