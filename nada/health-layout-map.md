# NSS health surveys byte/column map (Sch 25.0: 75th round 2017-18 TXT, 80th round 2025 CSV)

Positions sufficient to compute out-of-pocket medical expenditure (OOPME)
per hospitalisation case by religion of household head, weighted. Feeds
`hospital-oop-spend`.

**Verified end-to-end 2026-06-11**: the 2017-18 estimator reproduces all
nine cells of NSS Report 586 Statement 3.15 (gross medical expenditure per
case by hospital type x sector) within 0.01% and the Statement 3.19
reimbursement shares (rural 4.4% / urban 16.8%) exactly; the 2025 estimator
reproduces all six press-note OOPME cells (April 2026) within 0.01%.
Extractors: `transform/health/extract_health_201{7,2025}_by_religion.py` ->
`extracted/health/health-{2017,2025}-oopme-by-religion.csv`.

## The construct (identical in both rounds)

OOPME per case = SUM w x (medical expenditure - reimbursement) / SUM w over
hospitalisation cases of the last 365 days whose nature-of-ailment code is
NOT childbirth (codes 87 normal / 88 caesarean / 89 other delivery - same
trio in both rounds). Medical expenditure = package component + doctor's/
surgeon's fee + medicines + diagnostics + bed charges + other medical
(attendant charges, physiotherapy, appliances, blood, oxygen); transport,
food and other non-medical expenses EXCLUDED. Reimbursement = amount
reimbursed by medical insurance company or employer. Type of medical
institution: 1 govt/public, 2 charitable/trust/NGO, 3 private (the 2025
press note folds govt-empanelled private hospitals into 3).

## 75th round (R75250L01..L13.TXT, record = 142 chars + CRLF)

13 levels = schedule blocks: L01 blocks 1-2 (identification), L02 block 3
(household incl religion), L03 block 4 (person roster), L04 block 5
(deaths), L05 block 6 (hospitalisation case particulars), L06 block 7 items
1-14 (case expenditure), L07 block 7 items 15-20 (reimbursement, finance),
L08 block 8 (15-day ailment roster), L09 block 9 items 1-18 (outpatient
expenditure), L10 block 9 items 19-23 (outpatient reimbursement), L11 block
10a (women 15-49: childbirth), L12 block 10b (immunisation), L13 block 11
(aged). Bytes 1-126 data, 127-129 NSS, 130-132 NSC, 133-142 MLT (two
implied decimals).

- **Weight = MLT/100 if NSS == NSC else MLT/200** (sub-sample-combined
  rule, README75_250). UNLIKE NSS 76th Sch 1.2 (flat MLT/100), this round
  HAS the halving - the published cells confirm it.
- Household key = FSU bytes 4-8 + segment 31 + second-stage stratum 32 +
  household no. 33-34 (`line[3:8] + line[30:34]`). Case key adds
  hospitalisation case serial bytes 38-39 (`line[37:39]`), which joins
  L05 <-> L06 <-> L07 1:1:1 (93,925 each).

| Field | Level | Bytes (1-based) | Notes |
|---|---|---|---|
| Sector | any | 15 | 1 rural, 2 urban |
| Religion of head | L02 | 54 | 1 Hindu, 2 Islam, 3 Christian, 4 Sikh, 5 Jain, 6 Buddhist, 7 Zoroastrian, 9 other |
| Nature of ailment | L05 | 45-46 | childbirth = 87/88/89 |
| Type of medical institution | L05 | 48 | 1 public, 2 charitable, 3 private |
| Medical expenditure: total | L06 | 94-101 | block 7 item 11 (= items 5-10) |
| Expenditure total incl transport | L06 | 118-125 | item 14 - NOT used (anchor excludes transport) |
| Amount reimbursed | L07 | 45-52 | item 15 |
| Major source of finance | L07 | 53 | item 16 |

Money fields are whole rupees, blank when not applicable - parse
`int(s.strip() or 0)`.

## 80th round 2025 (hhscsL1..L7.csv, with headers)

7 levels: L1 blocks 1+2+5 (identification + household; 139,732), L2 block 3
(persons; 651,732), L3 block 4 (deaths; 3,936), L4 blocks 6+7
(hospitalisation case + expenditure in ONE file; 121,584), L5 blocks 8+9
(outpatient; 96,277), L6 block 10 (childbirth/immunisation; 167,051),
L7 block 11 (aged; 37,557).

- **Weight = mult/100 flat** (final multiplier posted; README_HEALTH_25pt0).
  `nst`/`nstj` are FSU counts, NOT the old NSS/NSC - no halving rule.
- Household key = `fsu, sd, sss, hhd` (unique on L1); L4 -> L1 join is m:1.

| Field | File | Column | Notes |
|---|---|---|---|
| Sector | any | `sec` | 1 rural, 2 urban |
| Religion of head | L1 | `b5i2` | same codes as 75th |
| Nature of ailment | L4 | `b6i5` | childbirth = 87/88/89 (b6i4 is infant age-in-days, the item numbering shifted vs 75th) |
| Type of medical institution | L4 | `b6i7` | 1 public, 2 charitable, 3 private |
| Medical expenditure: total | L4 | `b7i12` | block 7 item 12 (renumbered from 75th's item 11) |
| Amount reimbursed | L4 | `b7i16` | item 16 |

## Gotchas

- The two rounds publish DIFFERENT headline constructs: Report 586 prints
  gross medical expenditure (Statement 3.15) and reimbursement shares
  (Statement 3.19) separately; the 2025 press note prints net OOPME. The
  dashboard serves net OOPME in both years - in 2017-18 it is the
  composite of the two gated components.
- Childbirth hospitalisations are a third of all case records (27,686 of
  93,925 in 2017-18; 34,794 of 121,584 in 2025) - forgetting the exclusion
  inflates nothing (childbirth is cheap) but breaks every anchor.
- The 2025 press-note childbirth OOPME (14,775) is per INSTITUTIONAL
  childbirth from block 10, not per block-6/7 hospitalisation case
  (computing it from L4 gives ~15,152, +2.5%) - do not gate on it.
- 75th block-7 item numbering differs from 2025 (item 11 vs 12 for medical
  total) because the 80th inserted "whether any medical service provided
  free" as b7i5 and infant age as b6i4.
- PPRA (morbidity) roughly doubled between rounds - perception-driven
  reporting, the data-user note cautions. Expenditure per case is
  transactional and the press note itself compares rounds directly, so the
  trend carries no break_flag.
