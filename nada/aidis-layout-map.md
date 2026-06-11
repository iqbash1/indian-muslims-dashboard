# AIDIS 2013 (NSS 70th round, Sch 18.2) unit-level map, Visit 1

File/block/column map sufficient to compute, per household and by religion of
head: average value of assets (AVA), average outstanding debt (AOD), net worth,
incidence of indebtedness (IOI) and the institutional share of outstanding debt,
all as on 30.06.2012 (the 70th round reference date). Source archive:
`~/Desktop/nada-work/aidis-2013-v1/` (idno
`DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec20131`, sha256s in MANIFEST.json).
Visit 2 is a separate dataset (idno suffix `V2`, dir `aidis-2013-v2`): it carries
only the Jul-Dec 2013 capital-formation flows, NOT the asset/debt stocks, so the
wealth card never needs it.

**Verified end-to-end 2026-06-10** (transform/aidis/extract_wealth_2013_by_religion.py)
against NSS KI(70/18.2) "Key Indicators of Debt and Investment in India"
(19 Dec 2014; fetched from mospi.gov.in, sha256
5d44603b34275a3e244f98badbff7ea99ae5b70b38b90ebd089c2ecc12443b30):

| indicator (all-India) | computed | published | delta |
|---|---|---|---|
| households surveyed rural / urban | 62,135 / 48,665 | 62,135 / 48,665 | exact |
| AVA rural (Rs) | 1,004,647 | 1,006,985 | -0.23% (block 10 empty, see gotcha 1) |
| AVA urban (Rs) | 2,267,907 | 2,285,135 | -0.75% (ditto) |
| AOD rural / urban (Rs) | 32,522 / 84,625 | 32,522 / 84,625 | exact to the rupee |
| IOI rural / urban (%) | 31.44 / 22.37 | 31.44 / 22.37 | exact |
| institutional share of debt rural / urban (%) | 55.98 / 84.48 | 56.0 / 84.5 (Table 8) | exact |

## The data zip

`CSV_NSS_70th_Debt_&_Investment_Visit1_Jan_Dec_2013.zip` (39 MB), one CSV per
schedule block under a same-named folder. ALL CSVs have a header row and repeat
the full household identification + weight columns on every record:

- `HHID` = 9-digit household key: `Vill_Blk_Slno`(5) + `HG_SubBlkNo`(1) +
  `Second_Stratum`(1) + `Hhold_no`(2). Unique per household, identical across
  all files: the ONLY join key needed.
- `Sector` 1 rural / 2 urban; `State` (NSS codes, see State_code.doc);
  `State_District`; `Sample` = 1 everywhere (central sample only, which is what
  the published KI uses too).
- Weights on every row: `NSS`, `NSC`, `MLT`, plus precomputed `Weight_SS`
  (= MLT/100) and `Weight_SC` (= MLT/200). Combined-subsample household weight =
  `Weight_SS if NSS == NSC else Weight_SC` (the usual NSS rule; Appendix C of the
  KI gives the estimator). Yields 156.1M rural + 83.7M urban households for 2013.
  Using Weight_SS alone double-counts (312M rural).

| zip member (prefix) | level | schedule block | rows |
|---|---|---|---|
| `Visit 1_Block 12_Identification...` | 01 | blocks 1-2 ident. + field ops (MISNAMED: it is NOT block 12) | 1/hh |
| `Visit 1_Block 3_Household Characteristics` | 02 | block 3: size, type, RELIGION `b3q6`, social group `b3q7`, bank-account items | 1/hh, all 110,800 |
| `Visit 1 _Block 4_Demographic...` | 03 | block 4 person roster (note the space before `_Block`) | 1/person |
| `Visit 1_Block 5_Questions...` | 04 | block 5 land-ownership y/n screeners | 1/hh |
| `Visit 1_Block 5pt1_...` | 05 | block 5.1 rural-type land plots | 1/plot |
| `Visit 1_Block 5pt2_...` | 06 | block 5.2 urban-type land plots | 1/plot |
| `Visit 1_Block 6_Buildings...` | 07 | block 6 buildings | 1/item |
| `Visit 1_Block 7_Livestock...` | 08 | block 7 livestock | 1/item |
| `Visit 1_Block 8_Transport...` | 09 | block 8 transport equipment | 1/item |
| `Visit 1_Block 9_Agricultural machinery...` | 10 | block 9 agri machinery | 1/item |
| `Visit 1_Block 10_Non-farm...` | 11 | block 10 non-farm business equipment | 1/item |
| `Visit 1_Block 11_.csv` | 12 | block 11 shares & debentures | 1/institution-type |
| `Visit 1_Block 12.csv` | 13 | block 12 financial assets other than shares | 1/item |
| `Visit 1_Block 13.csv` | 14 | block 13 amount receivable | 1/head |
| `Visit 1_Block 14.csv` | 15 | block 14 CASH LOANS | 1/loan |
| `Visit 1_Block 15.csv` | 16 | block 15 kind loans | 1/loan |
| `Visit 1_Block 16.csv` + `_value.csv` | 17/18 | block 16 capital expenditure flows (huge, ~450 MB; not needed for stocks) | 1/item |

Column names are block-question codes (`b5_1_6`, `b14_q17`); the decoder is
`data_layout18.2v1.xls` (single sheet, byte-layout of the old fixed-width dump;
the CSV column ORDER follows it but the weights exist only in the CSV).

## Asset blocks (stocks as on 30.06.2012)

Every asset block carries item rows AND a household TOTAL row in the same file.
Per-block serial (`srl`) semantics, value column, and the safe aggregation:

| block | srl col | value col | TOTAL srl | internal subtotals (skip when summing items) |
|---|---|---|---|---|
| 5.1 land rural-type | `b5_1_1` | `b5_1_6` | 99 | none, but srl 96 = "land outside FSU" catch-all ITEM, 98 = housesite item |
| 5.2 land urban-type | `b5_2_1` | `b5_2_6` | 99 | srl 97 = outside-FSU catch-all, 98 housesite |
| 6 buildings | `b6_q3` | `b6_q6` | 11 | none (items 1-10) |
| 7 livestock | `b7_q2` | `b7_q5` | 22 | srl 17 = subtotal of items 1-16 |
| 8 transport | `b8_q2` | `b8_q5` | 8 | none (items 1-7) |
| 9 agri machinery | `b9_q2` | `b9_q4` | 8 | none (items 1-7) |
| 10 non-farm equipment | `b10_q2` | `b10_q3` | 15 | srl 12 = subtotal of items 1-11 |
| 11 shares & debentures | `b11_q1` | `b11_q6` | 5 | none (items 1-4); q6 = 30.06.12 value derived as q3+q5-q4 (market value on survey date adjusted for acquisitions/disposals) |
| 12 financial assets | `b12_q1` | `b12_q3` | 11 | srl 8 = NO. of insurance policies (count), 9 = total sum assured, 12 = bullion & ornaments: ALL THREE excluded from the total (= items 1-7 & 10) |
| 13 amount receivable | `b13_q2` | `b13_q4` | 7 | none (items 1-6) |

AVA = sum of the 10 block totals. Use the TOTAL row when present (item-sums
reconcile with it to ~1.000 in every block) and fall back to the item-row sum
(minus subtotal serials) for the <=21 households per block whose total row is
missing. A handful of junk serials exist (3 rows of srl 17 in block 8, 1 row
each of 96/99 in block 6); serials above the block's total serial are noise.

## Debt block (block 14, cash loans)

One row per loan + a srl-99 household total row (`b14_q1` = serial).

- `b14_q4` period of loan: 1 = outstanding on 30.06.2012, 2 = contracted after
  1.7.2012. **`b14_q17` (amount outstanding incl. interest as on 30.06.2012) is
  filled ONLY for period-1 loans** (verified: 0 on all 48,182 period-2 rows);
  q17 = q14 (repaid since) + q15 (written off since) + q16 (outstanding on
  survey date).
- Household debt as on 30.06.2012 = sum of q17 over period-1 ITEM rows (the
  srl-99 row reconciles within 0.8% overall but disagrees for 427 households;
  item rows are the primary records and are needed for the agency split anyway).
- IOI = weighted share of households with that sum > 0. Reproduces the published
  31.44 rural / 22.37 urban exactly, and AODL (debt per indebted household)
  103.4k/378.3k to 0.02%.
- `b14_q6` credit agency: institutional = {01 govt, 02 co-op society/bank,
  03 commercial bank incl. RRB, 04 insurance, 05 provident fund, 06 financial
  corp., 07 financial company, 08 SHG-bank-linked, 10 SHG-NBFC, 11 other
  institutional}; non-institutional = {12 landlord, 13 agricultural moneylender,
  14 professional moneylender, 15 input supplier, 16 relatives & friends,
  17 doctors/lawyers/other professionals, 09 others}. **Code 09 is
  NON-institutional** despite sitting numerically inside the institutional run.
- Block 15 (kind loans) outstanding is as on the DATE OF SURVEY, not 30.06.2012;
  the published AOD is cash loans only. Exclude it.

## Block 3 codes (level 02)

Religion `b3q6`: 1 Hinduism, 2 Islam, 3 Christianity, 4 Sikhism, 5 Jainism,
6 Buddhism, 7 Zoroastrianism, 9 others (no blanks in the data; sample counts
rural/urban: Hindu 49,385/36,710, Muslim 6,349/7,352, Christian 4,009/2,980,
Sikh 1,207/759). Social group `b3q7`: 1 ST, 2 SC, 3 OBC, 9 others. `HH_type`
column = household-type code.

## Gotchas

1. **Block 10's value column (`b10_q3`) is EMPTY for all 85,330 rows** of the
   CSV conversion (serials and weights present, every value blank). Non-farm
   business equipment is 0.25% (rural) / 0.76% (urban) of published AVA, which
   is exactly the AVA shortfall the extraction shows. Nothing to fix CSV-side;
   the SPSS/STATA/JSON conversions on the portal MIGHT carry the values if the
   gap ever matters.
2. **Bullion & ornaments are collected but excluded from the published AVA**
   (block 12 srl 12; KI Statement 3.3 footnote "excl. bullion and ornaments").
   93,394 of 110,800 households report some: weighted avg Rs 39,775/hh rural,
   Rs 85,474 urban, i.e. ~3.7-3.9% on top of AVA. Household durables are not
   collected at all in this round. Keep the L2 on the published concept; mention
   both exclusions in card prose.
3. **Subtotal serials double-count if item rows are summed naively** (livestock
   srl 17, non-farm srl 12; block 12's srl 8/9 are a count and a sum-assured,
   not values). Safest: use each block's TOTAL serial row.
4. The level-01 identification file is MISNAMED "Block 12_Identification...";
   block 4's member name has a stray space ("Visit 1 _Block 4_"). Match members
   by prefix, not exact name.
5. Values are plain Rs (no thousands scaling anywhere); numerics carry float
   artefacts ("2012.0") and leading zeros, so normalise serials as strings and
   coerce values with a tolerant float().
6. Statement 3.4/3.2 of the KI are the validation anchors (AOD/IOI exact, AVA
   within the block-10 gap); KI Table 8 gives the credit-agency split per Rs
   1000 for the institutional-share check.
7. Survey weights: the same 4,529 rural + 3,507 urban FSU central sample as the
   KI; household counts match it exactly, so NADA ships the central sample only.

# AIDIS 2019 (NSS 77th round, Sch 18.2) unit-level map, Visit 1

NADA (catalog id 156) ships this survey ONLY as a Nesstar `.NSDstat` binary,
but MoSPI's ORIGINAL fixed-width TXT distribution survives in the unlinked
Drupal-era directory `mospi.gov.in/sites/default/files/NSS7718/` (same trick
as NSS 76 Sch 1.2 housing, see docs/runbooks/nss76-housing.md; the deleted
release page was found via the Wayback snapshot of its mospi.NIC.in twin,
`unit-level-data-report-nss-77-th-round-schedule-182-january-2019-...-debt-
and-investment`, captured 2021-11-17). Visit 1 = `r77182v1L01.TXT`..`L17.TXT`
(case matters: lowercase stem, UPPERCASE extension), 2,717,476 records, plus
`README77182_v1m.pdf`, `README77182_v2m.pdf`, the layout
`NSS_77th_Layout_Sch_18.2_mult_post.xls`, instructions and tabulation plan -
all still served with their original Aug 2021 Last-Modified stamps. Local
archive: `~/Desktop/nada-work/aidis-2018-19-alt/`; sha256s + URLs in
`sources/nss77-aidis/`. Record counts per level match the NADA DDI's
caseQnty AND the README exactly (two independent distributions agree).

**Verified end-to-end 2026-06-11**
(transform/aidis/extract_wealth_2018_by_religion.py) against the MoSPI press
note of 24.08.2021 (press_note-AIDIS-240821.pdf, fetched live; full report =
NSS Report No. 588), all as on 30.06.2018:

| indicator (all-India) | computed | published | delta |
|---|---|---|---|
| households rural / urban | 69,455 / 47,006 | 69,455 / 47,006 | exact |
| AVA rural / urban (Rs) | 15,92,379 / 27,17,081 | 15,92,379 / 27,17,081 | **exact to the rupee** |
| ... physical / financial split | all four cells | press-note figures | exact to the rupee |
| AOD rural / urban (Rs) | 59,748 / 1,20,336 | 59,748 / 1,20,336 | exact to the rupee |
| IOI rural / urban (%) | 35.04 / 22.41 | 35.0 / 22.4 | exact at printed precision |
| institutional debt share (%) | 66.1 / 87.1 | 66 / 87 | exact at printed precision |
| AODL rural / urban (Rs) | 1,70,514 / 5,36,975 | 1,70,533 / 5,36,861 | 0.01-0.02% (IOI rounding) |

Unlike 2013's CSV conversion there is NO empty-column defect: the TXT
distribution reproduces published AVA exactly (the 2013 block-10 gap was a
conversion artefact, not a survey feature). Weighted households 172.4M rural
/ 87.6M urban.

## Record format (README77182_v1m.pdf)

139 data bytes + CRLF (141 bytes/record on disk). Bytes 1-126 data, 127-129
NSC, 130-139 multiplier (two implied decimals). **Final household weight =
MLT/100, flat** - there is NO NSS field in this round's posted data and no
sub-sample halving rule (unlike 2013). Common ID: FSU serial 4-8, Sample 14
('1' everywhere bar 36 blanks), Sector 15 (1 rural / 2 urban), NSS-Region
16-18, District 19-20, Stratum 21-22, Sub-stratum 23-24, SSS 30, household
no. 31-32, visit 33, level 34-35. Household key = FSU+SSS+hhno (8 chars,
verified unique across the 116,461 L01/L03 rows).

## Level -> block map (Visit 1; 2019 RENUMBERED the early blocks vs 2013)

| level | block | content | rows |
|---|---|---|---|
| 01 | 1+2 | identification | 116,461 |
| 02 | 3 | person roster (demographics + financial inclusion) | 495,573 |
| 03 | 4 | household characteristics: size 41-43, **RELIGION 44**, social group 45, hh type 46 | 116,461 |
| 04 | 4 | usual consumer expenditure (UMPCE pieces) | 116,461 |
| 05 | 5.1 | rural-type land plots: srl 39-40, value 49-60 | 216,960 |
| 06 | 5.2 | urban-type land plots: srl 39-40, value 49-60 | 67,765 |
| 07 | 6 | buildings: srl 39-40, value 51-62 | 236,873 |
| 08 | 7 | livestock: srl 39-40, value 51-62 | 162,217 |
| 09 | 8 | transport: srl 40, value 51-62 | 186,968 |
| 10 | 9 | agri machinery: srl 39-40, value 51-62 | 131,885 |
| 11 | 10 | non-farm equipment: srl 39-40, value 41-52 | 63,223 |
| 12 | 11a | financial assets INCL. RECEIVABLES (not shares): srl 39-40, cols 3/4/5/6 = 41-52/53-64/65-76/77-88 | 504,309 |
| 13 | 11b | shares & related instruments: srl 40, same 4-col structure | 3,333 |
| 14 | 12 | CASH LOANS: srl 39-40, year 41-44, unpaid-on-30.6.18 flag 45, agency 58-59, outstanding-as-on-30.06.2018 = **108-119** | 178,971 |
| 15 | 13 | kind loans (as on survey date - outside published AOD) | 16,656 |
| 16 | 14 | capital expenditure cols 2-8 (flows) | 51,680 |
| 17 | 14 | capital expenditure cols 2, 9-14 (flows) | 51,680 |

Religion codes (b4q2, byte 44): 1 Hinduism, 2 Islam, 3 Christianity,
4 Sikhism, 5 Jainism, 6 Buddhism, 7 Zoroastrianism, 9 others. Sample counts:
Hindu 91,306, Muslim 13,520, Christian 7,119, Sikh 2,076.

## The official AVA recipe (Final Tabulation Plan, Sec 2 para 16)

AVA as on 30.06.2018 = sum per household of each block's TOTAL row:
5.1 srl 99 + 5.2 srl 99 + block 6 srl 10 + block 7 srl 17 + block 8 srl 8 +
block 9 srl 13 + block 10 srl 20 + block 11a srl 19 (col 6) + block 11b srl 5
(col 6). Land blocks keep the 2013 special ITEM serials (96/97 outside-FSU
catch-all, 98 housesite - genuine items inside the total). Blocks 11a/11b
record survey-date stocks plus transactions since 1.7.2018; col 6 = col 3 +
col 5 - col 4 backs out the 30.06.2018 value. **Block 11a srl 20 = bullion &
ornaments, srl 21 = paintings/artistic originals - memo items OUTSIDE the
total** (the 2013 bullion exclusion, formalised); item 12 is a policy COUNT
and 13 a sum-assured (shaded value cols). Debt = level 14 item rows with
byte 45 == 1, summing bytes 108-119; the srl-99 row is a household total
(q3 blank there). IOI = weighted share with that debt > 0.

## Credit-agency codes (block 12 col 5) - the 09/10 trap, 2019 edition

Instructions Vol-I 4.12.5: 01 scheduled commercial bank, 02 RRB, 03 co-op
society, 04 co-op bank, 05 insurance, 06 provident fund, 07 employer,
08 financial corporation/institution, **10** NBFC/MFI, 11 bank-linked
SHG/JLG, 12 non-bank-linked SHG/JLG, 13 other institutional, 14 landlord,
15 agricultural moneylender, 16 professional moneylender, 17 input supplier,
18 relatives & friends, 19 chit fund, 20 market commission agent/traders,
**09 "other" = NON-institutional** (4.12.5.1: institutional = 01-08 and
10-13). The NADA DDI's category labels DISAGREE (they label 09 as NBFC and
omit 10) and are WRONG: computed with the DDI mapping the urban institutional
share lands at 84.0 vs the published 87. The questionnaire also encodes the
split in the SERIAL ranges (srl 1-50 institutional, 51-98 non-institutional,
99 total - 4.12.1); in the data the instructions rule and the serial-range
rule agree to the decimal (66.1 rural / 87.1 urban vs published 66/87), so
the extractor uses the instructions mapping. 132 loan rows carry a blank/zero
agency code - treated as non-institutional under every rule.

## Empirical notes from the verified run

- Item-sum vs total-row reconciliation is 1.000 in every asset block except
  livestock (1.843) and non-farm equipment (1.443), which contain internal
  SUBTOTAL item serials like their 2013 counterparts. Harmless: the TOTAL row
  is used wherever present, and only 2 households across those blocks needed
  the item-sum fallback.
- Block 11a is missing its srl-19 total row for 3,556 households; the item-sum
  fallback covers them and the all-India financial AVA still reproduces the
  press note to the rupee.
- Bullion & ornaments memo (11a srl 20, outside AVA): avg Rs 51,409/household
  rural, Rs 81,781 urban, i.e. roughly +3% on AVA - consistent with 2013's
  ~+3.7-3.9%.
- 36 of 116,461 L03 rows have a blank Sample byte; everything else is '1'
  (central sample only, like every NADA/mirror NSS distribution).
- q15 (outstanding as on 30.06.2018) is 0 on every loan flagged paid-off
  (q3==2) - the flag and the amount are mutually consistent, so either works
  as the period filter.

Values are plain Rs with explicit decimal points where applicable; blanks =
not applicable. Kind loans and capital-expenditure levels are not used by
the wealth metrics.
