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

## AIDIS 2019 (77th round) status

The wealth card's second point should be AIDIS 2019 (Sch 18.2, Jan-Dec 2019,
reference date 30.06.2018), but NADA currently ships its data files ONLY as
Nesstar `.NSDstat` binaries (no CSV/flat export), so it is unbuildable here
(see nada/PLAN.md backlog). When a usable export appears: the 77th schedule
keeps the same block numbering (3 household characteristics with religion,
5.1/5.2 land, 6 buildings, 7 livestock, 8 transport, 9 agri machinery, 10
non-farm equipment, 11 shares, 12 financial assets, 13 receivable, 14 cash
loans with the same period/agency/outstanding-as-on-30.06.18 columns), and the
published validation anchors (verified 2026-06-10 from MoSPI's AIDIS press note
of 24.08.2021, mospi.gov.in/sites/default/files/press_release/
press_note-AIDIS-240821.pdf) are: AVA rural Rs 15,92,379 / urban Rs 27,17,081,
AOD rural Rs 59,748 / urban Rs 1,20,336, IOI rural 35.0% / urban 22.4%, all as
on 30.06.2018 (the full report is NSS Report No. 588).
