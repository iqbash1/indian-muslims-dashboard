# EUS (NSS Employment & Unemployment Survey, Sch 10) unit-level map - the pre-PLFS rounds

Column/file map sufficient to compute 15+ usual-status (ps+ss) LFPR / WPR /
UR / salaried share by religion x sector x sex from the three quinquennial
"thick" EUS rounds whose NADA distributions are plain CSV zips:

| round | fieldwork | NADA id | local archive | data zip |
|---|---|---|---|---|
| 61st | Jul 2004 - Jun 2005 | 109 | eus-2004-05 | Emp_Unemp_2004_2005_CSV.zip |
| 66th | Jul 2009 - Jun 2010 | 124 | eus-2009-10 | Emp_Unemp_2009_2010_CSV.zip |
| 68th | Jul 2011 - Jun 2012 | 127 | eus-2011-12 | U_M_2011_2012_CSV.zip |

**The 64th round (2007-08, Sch 10.2) is EXCLUDED by design**: it is the thin
annual round (572,254 persons, migration-focused) and NSSO published NO
employment-by-religion tables for it (verified in Report 531), so a
by-religion extraction has no gate. Its CSV zip is banked anyway
(eus-2007-08; religion = B3_q5 in Block-3, person-level usual status =
B4_c9/B4_c14 in Block-4, per the IHSN study report in that archive).
The 2009-10 round also ships a 66th-Sch-10 "new format" rar - that one is a
Nesstar disc image, ignore it; the CSV zip is the open distribution.

**Verified end-to-end 2026-06-11** (transform/eus/extract_microdata_trends.py):
all 310 gate cells - all-ages LFPR/WPR/UR per 1000 by religion (muslim,
hindu, christian, sikh, all) x sector x sex x round vs NSS Report 568
Statements 3.12/3.13/3.17 (which tabulate all three rounds side by side;
Report 552's overlapping columns agree), plus salaried-per-1000-workers vs
Report 568 Statement 3.16 (2011-12) and Report 552 Statement 3.16 (2009-10)
- pass. LFPR/WPR reproduce at printed precision in every cell. The UR gate
uses a propagated tolerance max(1.5, 750/published-LFPR) per 1000: the
published UR divides an unemployed share (itself the difference of two
independently rounded statements) by small female labour forces, so printed
rounding amplifies; the underlying population shares all match at printed
precision. Anchor PDFs + extracted text: ~/Desktop/nada-work/eus-anchors/
(reports 521, 531, 533, 552, 563, 568 fetched live from mospi.gov.in
publication stores 2026-06-11; 521 = 61st religious-groups report, its
Statement 3.14 PDF text fails its own row-sum check so 2004-05 salaried is
machinery-validated rather than gated).

## Per-round structure (the layout drift IS the gotcha list)

### 61st (2004-05) - block files named Block_<n>_level_<nn>.csv
- `Block_1_2_and_3_level_01.csv`: blocks 1+2+3 MERGED, one row per household:
  `HHID` (9 chars), `RELIGION`, `SOCIAL_GRP`, `Sector`, MPCE, response codes,
  weights.
- `Block_5pt1_level_04.csv` (usual principal, one row per PERSON, all
  members): `PID` (= HHID + 2-digit serial, verified unique across 602,833
  rows), `Age`, **`Sex` (in-file - block 4 not needed)**,
  `Usual_principal_activity_status`, `WEIGHT_COMBINED`, `Sector`.
- `Block_5pt2_level_05.csv` (subsidiary, only persons with one):
  `PID`, `Usual_subsidiary_economic_activi` (header truncated at 32 chars).
- Block_4_level_03 (demographics) exists but is not needed.

### 66th (2009-10) - descriptive member names
- `Block_3_Household characteristics.csv`: `HHID`, `Religion`, `Social_Group`.
- `Block_5_1_Usual principal activity...csv`: `HHID`, `PID`, `Age`,
  `Usual_Principal_Activity_Status`, `WEIGHT`, `Sector` - **no Sex column**.
- `Block_4_Demographic particulars...csv`: `PID` -> `Sex` (join).
- `Block_5_2_Usual subsidiary...csv`: `PID` -> `Usual_Subsidiary_Activity_Status`.

### 68th (2011-12) - descriptive names, no PID anywhere
- `Block_3_Household characteristics.csv`: `Religion`, `Social_Group` but
  **NO HHID column** - compose it the way block 4 spells its HHID:
  FSU_Serial_No(5) + Hamlet_Group_Sub_Block_No(1) +
  Second_Stage_Stratum_No(1) + Sample_Hhld_No(2).
- `Block_5_1_...csv`: `HHID`, `Person_Serial_No`, `Age`,
  `Usual_Principal_Activity_Status`, `Multiplier_comb`, `Sector` - no Sex.
- `Block_4_...csv`: HHID + Person_Serial_No -> `Sex`.
- `Block_5_2_...csv`: HHID + Person_Serial_No -> `Usual_Subsidiary_Activity_Status`.

## Estimator (identical to the PLFS pipeline)

Employed = principal OR subsidiary status in {11,12,21,31,41,51}; unemployed
= not employed AND principal == 81; salaried = classifying status (ps if
ps-employed else ss) == 31. Weight = the round's precomputed combined
multiplier on the person row (`WEIGHT_COMBINED` / `WEIGHT` /
`Multiplier_comb`); every published rate is a weighted ratio so the
multiplier's scale cancels. Status codes seen per round (frequency-checked):
11/12/21/31/41/51 work, 81 unemployed, 91-97 out of labour force, 99
infants/not-recorded, 95 disabled (4,884 rows in 2004-05). Religion codes
1-7, 9 = the standard NSS list (1 Hinduism, 2 Islam, ...); 'other' buckets
7+9. Persons in households without a religion record: 74 (2004-05), 0
(2009-10), 1 (2011-12) - dropped with a printed warning.

## Feeding the dashboard

L2 `extracted/eus/eus-microdata-2004-12-by-religion.csv` -> the
2004/2009/2011 rows of lfpr-15plus / wpr-15plus / salaried-share /
unemployment-rate-15plus via `eus_trend_rows` in
transform/canonicalize/_plfs_microdata.py. The EUS->PLFS design break
(sampling, CAPI, rotation panel) is flagged break_flag=true on the 2017 PLFS
rows - mpce's Sachar->HCES convention; the card line renders dashed.
salaried-earnings stays PLFS-only (the EUS wage instrument differs).
