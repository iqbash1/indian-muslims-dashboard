# PLFS unit-level column map, 2017-18 to 2023-24 (7 rounds)

Per-round column map sufficient to compute, for persons aged 15+, by religion:
LFPR, WPR, unemployment rate (all usual status ps+ss) and salaried/regular-wage
share among workers, weighted. Source archives live in
`~/Desktop/nada-work/plfs-YYYY-YY/` (one dir per July-June round).

**Verified end-to-end 2026-06-10**: for every round, the person-household join
matched 100% of person records (0 unmatched, household key unique), and the
weighted all-India 15+ usual-status (ps+ss) estimates reproduce the published
PLFS annual report figures to one decimal:

| Round | LFPR computed | WPR computed | UR computed | Published (LFPR/WPR/UR) |
|---|---|---|---|---|
| 2017-18 | 49.8 | 46.8 | 6.0 | 49.8 / 46.8 / 6.0 |
| 2018-19 | 50.2 | 47.3 | 5.8 | 50.2 / 47.3 / 5.8 |
| 2019-20 | 53.5 | 50.9 | 4.8 | 53.5 / 50.9 / 4.8 |
| 2020-21 | 54.9 | 52.6 | 4.2 | 54.9 / 52.6 / 4.2 |
| 2021-22 | 55.2 | 52.9 | 4.1 | 55.2 / 52.9 / 4.1 |
| 2022-23 | 57.9 | 56.0 | 3.2 | 57.9 / 56.0 / 3.2 |
| 2023-24 | 60.1 | 58.2 | 3.2 | 60.1 / 58.2 / 3.2 |

## Shared structure (all 7 rounds)

- Each data zip holds 4 CSVs: household first visit (HHV1/HHFV), person first
  visit (PERV1/PERFV), household revisit (HHRV), person revisit (PERRV). The
  annual usual-status estimates use the FIRST VISIT person file only (V1 covers
  all 4 quarters; revisits repeat panel households and carry no block 5.1/5.2).
  No combined file exists in any round.
- **All CSVs have a header row.** Column names are schedule block-question codes
  (`b4q5`, `b5pt1q3`) plus a file suffix that varies by era (below). No
  positional parsing needed; the layout xlsx is only the decoder for names.
- **Religion is NOT in the person file in any round.** It is household-level:
  block 3 item 3, column `b3q3<hh suffix>` in the household first-visit file.
  Join required (keys below).
- Values are messy strings: leading zeros ("01"), float artefacts ("184596.0",
  "1.0"). Normalise keys (strip, drop trailing .0, drop leading zeros) and
  numeric-coerce code columns before use.

### Join keys (person FV -> household FV), all rounds

Per every round's README, the common primary key is Quarter, Visit, FSU,
Hamlet-group/sub-block no., Second-stage-stratum no., Sample household no.
Within the FV files Visit is constant ("V1"), so join on:

| Concept | Person col | Household col |
|---|---|---|
| Quarter | `quarter_*` (2017-20) / `qtr_*` (2020-24) | `qtr_*` |
| FSU serial no. | `fsu_*` (2017-20) / `b1q1_*` (2020-24) | `b1q1_*` |
| Sample sg/sb (hamlet group) no. | `b1q13_*` | `b1q13_*` |
| Second stage stratum no. | `b1q14_*` | `b1q14_*` |
| Sample household no. | `b1q15_*` | `b1q15_*` |

This 5-tuple is unique in every HHV1 file (validated m:1, zero duplicates,
zero unmatched persons in all 7 rounds).

### Weight formula (identical wording in all 7 READMEs)

> For generating combined estimate (taking both the subsamples together):
> Final weight = MULT/100 if NSS = NSC, = MULT/200 otherwise.
> Generation of combined estimate for the entire Year: for annual estimate,
> MULT may be divided by NO_QTR (count of occurrences of surveyed FSUs in a
> sector x state x stratum x substratum).

(2017-21 READMEs say "divided by number of quarters"; 2020-21 onward spell out
that this means the per-record NO_QTR count, which the data carries. NO_QTR is
4 for almost all records.) So the annual person weight is:

```
w = (MULT/100 if NSS == NSC else MULT/200) / NO_QTR
```

NSS = FSU count for the record's sub-sample within sector x state x stratum x
substratum; NSC = same count for both sub-samples combined. All three columns
sit at the end of both person and household files. MULT has 2 implied decimals,
hence the /100.

### Code lists (verified identical in all rounds: 2017-18 Instructions Vol-I,
### 2020-21 and 2022-23 FV schedules, 2023-24 Instruction Manual Vol-II)

Religion (`b3q3`, household file): 1 Hinduism, 2 Islam, 3 Christianity,
4 Sikhism, 5 Jainism, 6 Buddhism, 7 Zoroastrianism, 9 Others.

Usual activity status (block 5.1 col 3 principal, block 5.2 col 3 subsidiary):

| Code | Meaning |
|---|---|
| 11 | self-employed: own account worker |
| 12 | self-employed: employer |
| 21 | helper in household enterprise (unpaid family worker) |
| 31 | regular salaried/wage employee |
| 41 | casual wage labour: public works |
| 51 | casual wage labour: other work |
| 81 | did not work but was seeking and/or available for work (unemployed) |
| 91-95, 97 | out of labour force (student, domestic duties, domestic+free collection, rentiers/pensioners, disabled, others) |

Block 5.2 (subsidiary) status only ever takes 11-51. Block 5.2 is filled when
block 5.1 col 7 ("whether engaged in any work in subsidiary capacity",
1 yes / 2 no) = 1; it is asked of everyone including principal-status 81/91-97.

### Indicator definitions (usual status ps+ss, age 15+, weighted)

- worker = principal status in {11,12,21,31,41,51} OR subsidiary status in
  {11,12,21,31,41,51}
- unemployed = principal status 81 AND not worker
- LFPR = (worker + unemployed) / population; WPR = worker / population;
  UR = unemployed / (worker + unemployed)
- salaried share among workers: classify each worker by principal status if
  principal-employed, else by subsidiary status; share with code 31.
- Age filter: `b4q6 >= 15`. Sex `b4q5` (1 male, 2 female, 3 transgender).
  Sector `b1q3` (1 rural, 2 urban). State `state` (NSS codes, sheet "State
  code" in each layout xlsx; J&K=01 ... Telangana=36).

## Per-round specifics

Era A = 2017-18, 2018-19, 2019-20 (suffixes `_per_fv` / `_hh_fv`).
Era B = 2020-21 to 2023-24 (suffixes `_perv1` / `_hhv1`).

### 2017-18
- Zip: `CSV_PLFS_July2017_June2018.zip`. Members:
  `CSV_PLFS_July2017_June2018/hh_per_fv_2017-18.csv` (person FV, despite the
  "hh_per" name), `hhfv_2017-18.csv` (household FV), `hh_per_rv_2017-18.csv`
  (person RV), `hh_rv_2017-18.csv` (household RV).
- Person FV columns: quarter `quarter_per_fv`, FSU `fsu_per_fv`, sg/sb
  `b1q13_per_fv`, SSS `b1q14_per_fv`, HH no `b1q15_per_fv`, sector
  `b1q3_per_fv`, state `state_per_fv`, district `b1q4_per_fv`, person srl
  `b4q1_per_fv`, sex `b4q5_per_fv`, age `b4q6_per_fv`, principal status
  `b5pt1q3_per_fv`, subsidiary-work flag `b5pt1q7_per_fv`, subsidiary status
  `b5pt2q3_per_fv`, weights `NSS_per_fv` `NSC_per_fv` `MULT_per_fv`
  `No_qtr_per_fv`.
- Household FV columns: quarter `qtr_hh_fv`, FSU `b1q1_hh_fv`, sg/sb
  `b1q13_hh_fv`, SSS `b1q14_hh_fv`, HH no `b1q15_hh_fv`, religion `b3q3_hh_fv`
  (b3q1 size, b3q2 hh type, b3q4 social group, b3q5 monthly consumer exp),
  district `dist_code_hh_fv`, weights `NSS/NSC/MULT/No_Qtr_hh_fv`.
- README: `README.doc` (convert with `textutil -convert txt`). Weight rule as
  above ("MLTS" = MULT).

### 2018-19
- Zip: `PLFS_2018_19_CSV.zip`. Members: `PLFS_2018_19_CSV/PerV1_2018-19.csv`,
  `HHV1_2018-19 (1).csv` (note the literal " (1)" in the member name),
  `PerRV_2018-19.csv`, `HHRV-2018-19 (1).csv`.
- Person FV columns: identical names to 2017-18 (`_per_fv` suffix).
- **Gotcha: the HHV1 header uses the `_hh_rv` suffix even though the file is
  first visit** (file-identification value FVH1, quarters Q5-Q8). Religion is
  `b3q3_hh_rv`, FSU `b1q1_hh_rv`, quarter `qtr_hh_rv`, etc.
- README: `README_July18_June19.pdf`. Same weight rule.

### 2019-20
- Zip: `CSV_PLFS_19_20.zip`. Members: `CSV_PLFS_19_20/PERFV_2019-20.csv`,
  `HHFV_2019-20.csv`, `PERRV_2019-20.csv`, `HHRV_2019-20.csv`.
- Columns: identical to 2017-18 (`_per_fv` / `_hh_fv`).
- README: `README.pdf`. Same weight rule.
- FOD sub-region (`b1q12`) can be non-numeric here ("MAN"): keep dtype=str.

### 2020-21
- Zip: `CSV_Unit_level_data_PLFS_July2020_June2021.zip`. Members under
  `CSV_Unit_level_data_PLFS_July2020_June2021/`: `perv1.csv`, `hhv1.csv`,
  `perrv.csv`, `hhrv.csv`.
- Era B renames: suffix `_perv1`/`_hhv1`, quarter `qtr_perv1`, FSU now
  `b1q1_perv1` in the PERSON file too, district `distcode_*`, weights
  lower-case `mult_perv1` `no_qtr_perv1` (NSS/NSC stay upper in perv1 but are
  lower-case `nss_hhv1`/`nsc_hhv1` in hhv1).
- Core indicator columns keep the same b-q names: sex `b4q5_perv1`, age
  `b4q6_perv1`, principal `b5pt1q3_perv1`, flag `b5pt1q7_perv1`, subsidiary
  `b5pt2q3_perv1`. Religion `b3q3_hhv1`. Household consumer expenditure now
  split into `b3q5pt1..pt6_hhv1` (pt6 = usual monthly total).
- New blocks: 5.1 q14, 5.2 q13, block 5.3 (`b5pt3q5..q12`), migration blocks
  7.1/7.2 (`b7pt1_*`, `b7pt2_*`).
- **Gotcha: perv1 includes TEMPORARY VISITORS (block 7.2) with person serial
  no. `b4q1_perv1` >= 81. Exclude them (`b4q1 < 81`) from all estimates.**
  Only this round has them.
- README: `plfsREADMEjuly20_jun21_1_(4).pdf`. Same weight rule, NO_QTR division
  spelt out.

### 2021-22
- Zip: `PLFS_Data_2021-22_CSV.zip`. Members under `PLFS_Data_2021-22_CSV/`:
  `perv1.csv`, `hhv1.csv`, `perrv.csv`, `hhrv.csv`.
- Columns as 2020-21 (no migration blocks, no visitors). Adds 5.1 q15/q16 and
  5.2 q14/q15 (product-specification questions); indicator columns unchanged.
- README: `README_Final.pdf`. Same weight rule.

### 2022-23
- Zip: `Data_in_CSV.zip`. Members under `Data_in_CSV/`: `perv1.csv`,
  `hhv1.csv`, `perrv.csv`, `hhrv.csv`.
- Columns as 2020-21 (5.1 up to q14, 5.2 up to q13, block 5.3; the q15/q16
  product-specification items were dropped again). Indicator columns unchanged.
- README: `README.pdf` (states the MULT/NO_QTR rule explicitly).
- **Gotcha: one Assam FSU carries an extremely high multiplier.** NSO's
  `Technical_clarification_regarding_high_multiplier_value_in_PLFS_2022_23.pdf`
  confirms it is by design (uninhabited-village PPS convention). Do not trim.

### 2023-24
- Zip: `CSV_data_PLFS_2023_2024.zip`. Members under
  `CSV_data_PLFS_2023_2024/`: `perv1.csv`, `hhv1.csv`, `perrv.csv`, `hhrv.csv`.
- Columns identical to 2022-23. README `1_README.docx` (textutil-convertible);
  adds SECTOR to the stated primary key (harmless: FSU serials already unique).
- The layout xlsx gains per-file sheets (`hhv1`, `perv1`, ...) with MoSPI short
  names (relg, pas, sas, has_sas, mult); the shipped CSVs still use the b-q
  header names, NOT these short names.

## Gotchas for the trend pipeline

1. **Era A vs Era B suffix rename** (2019-20 -> 2020-21): `_per_fv`/`_hh_fv`
   becomes `_perv1`/`_hhv1`; person FSU column renames `fsu_*` -> `b1q1_*`;
   person quarter column renames `quarter_*` -> `qtr_*`; `MULT`/`No_qtr`
   become lower-case `mult`/`no_qtr`; district `b1q4_*`+`dist_code_*` become
   `distcode_*` in both files.
2. **2018-19 HHV1 header mislabel**: household first-visit columns carry the
   `_hh_rv` suffix. Match on suffix per file, never assume `_hh_fv`.
3. **2020-21 temporary visitors**: drop perv1 rows with `b4q1_perv1 >= 81`
   before estimating, or the denominators are wrong (only round affected).
4. **Religion needs a household join in every round** (it is never in the
   person file). Join on quarter + FSU + b1q13 + b1q14 + b1q15 after string
   normalisation (leading zeros and ".0" artefacts differ between files).
5. **Weight rule is stable across all 7 rounds** (MULT/100 or /200 by NSS==NSC,
   then /NO_QTR for annual). No round switched to a plain MULT/100 rule.
6. **Household expenditure changed shape in Era B** (`b3q5` -> `b3q5pt1..pt6`):
   irrelevant for the labour indicators but breaks any naive b3q5 read.
7. **2022-23 Assam high multiplier** is intentional; keep, do not winsorise.
8. Quarter labels alternate by panel: Q1-Q4 in 2017-18, 2019-20, 2021-22,
   2023-24 but Q5-Q8 in 2018-19, 2020-21, 2022-23. Treat quarter as an opaque
   string join key, not an integer 1-4.
9. Code lists (religion, activity status) are byte-identical across rounds:
   31 = regular wage/salaried, employed = {11,12,21,31,41,51}, 81 = unemployed,
   91+ = out of labour force. No re-mapping needed between rounds.
10. Read everything as dtype=str first (mixed "01"/"1"/"1.0" representations,
    alphanumeric FOD sub-region values like "MAN").

## Earnings columns (added 2026-06-10, for the earnings-gap metric)

Average monthly earnings of regular wage/salaried employees come from schedule
block 6 ("current weekly activity particulars"), item 9: "for 31, 71 or 72 in
item 5 [current weekly status], earnings (received/receivable) during the
preceding calendar month for regular salaried/wage activity (Rs.)". CSV columns,
identical concept in all 7 rounds (person first-visit file):

| Concept | 2017-18 .. 2019-20 | 2020-21 .. 2023-24 |
|---|---|---|
| Current weekly status (CWS) | `b6q5_per_fv` | `b6q5_perv1` |
| Monthly earnings, regular salaried (item 9) | `b6q9_per_fv` | `b6q9_perv1` |
| Self-employment earnings, last 30 days (item 10) | `b6q10_per_fv` | `b6q10_perv1` |

Gotchas:
1. **Exact-name lookup is mandatory for the block-6 items.** The day-wise
   casual-wage columns (`b6q9_Act1_3pt7`, `b6q9_3pt7_perv1`, ...) share the
   `b6q9` prefix; a suffix-tolerant prefix match grabs the wrong column.
2. **The 2017-18 .. 2020-21 layout xlsx mislabels item 10** as "Earnings For
   Regular Salarid/Wage Activity". Empirically (all rounds) `b6q10` is populated
   only for CWS 11/12/61/62, i.e. it is the self-employment earnings item, and
   `b6q9` only for CWS 31/71/72. The 2021-22+ layouts label item 10 correctly.
3. **Definition that reproduces the published tables**: weighted mean of `b6q9`
   over persons with CWS in {31, 71, 72} who reported POSITIVE earnings
   (zero/not-reported excluded; 99.4-99.9% report, except 96.7% in 2019-20),
   first-visit file only, annual weight = (MULT/100 or /200 by NSS==NSC)/NO_QTR,
   NO age filter (the published tables are all-ages; sample counts match
   exactly). The published QUARTERLY statements (e.g. Statement 10 in 2023-24)
   instead pool first-visit + revisit schedules in urban areas, so their
   mean-of-quarters sits ~1.7% below the first-visit annual figure; the annual
   by-occupation tables (Table 55 in 2021-22, Table 33 in 2022-23, Tables 50/33
   in 2023-24, "Figures based on the first visit schedule ... combining all the
   four quarters") are the correct validation target for an FV-only pipeline.
   In the 2023-24 report PDF those table pages carry a stale "PLFS, 2022-23"
   footer; the values are 2023-24 (they differ from the 2022-23 report's own
   table and the sample counts match the 2023-24 microdata exactly).

**Verified 2026-06-10** (`transform/plfs/extract_earnings_by_religion.py`): all
9 all-India cells (rural/urban/total x male/female/person) match the published
annual tables within 0.03% for every round whose annual report is archived in
sources/plfs/annual/, with exact sample-count matches (max deviation 3 records
on male cells, the reports apparently fold the few transgender reporters into
"male"):

| Round | Published r+u person (n) | Computed (n) |
|---|---|---|
| 2021-22 | Rs 18,945 (43,064) | Rs 18,947 (43,064) |
| 2022-23 | Rs 19,744 (44,873) | Rs 19,745 (44,873) |
| 2023-24 | Rs 21,047 (46,294) | Rs 21,048 (46,294) |

2017-18 .. 2020-21 annual report PDFs are not archived locally, so those rounds
carry structural gates only (earnings reported only by CWS 31/71/72, >= 95%
reporting); columns, join, weights and code lists are byte-identical to the
validated rounds. The L2 (`extracted/plfs/plfs-earnings-2017-24-by-religion.csv`)
applies a 15+ age filter on top of the published all-ages definition (drops
20-42 under-15 reporters per round, <= 0.1%).
