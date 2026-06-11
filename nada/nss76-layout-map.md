# NSS 76th round Schedule 1.2 byte map (housing / water / sanitation, Jul-Dec 2018)

Byte positions sufficient to compute household-level housing, drinking-water,
sanitation and electricity indicators by religion of household head, weighted.
Data = nine fixed-width files `R76120L01.TXT` ... `R76120L09.TXT` in
`~/Desktop/nada-work/housing-water-2018-alt/` (provenance + SHA256 there),
downloaded from MoSPI's still-live file store
`https://www.mospi.gov.in/sites/default/files/NSS7612dws/` (server
Last-Modified 23 Nov 2019). The NADA catalog-153 distribution of this survey
carries the data ONLY as a proprietary `.Nesstar` binary inside
`Round76sch1dot2Data.rar` - use the TXT mirror instead; the layout file
`Data_Layout_NSS76_120.xlsx` shipped by NADA describes exactly this TXT
format (NADA copy and live MoSPI copy are byte-identical).

**Verified end-to-end 2026-06-10**: record counts of all nine files match
README76_S120.pdf exactly (106,838 households on L01; 1,321,283 records
total); the weighted all-India estimates reproduce 24 published cells of NSS
Report 584 (Statements 2.1, 5, 6, 7, 12.1, 22, 25) with worst gap 0.24pp
(most cells exact to the printed decimal). Extraction script:
`transform/nss76/extract_housing_2018_by_religion.py` ->
`extracted/nss76/nss76-2018-housing-by-religion.csv`.

## Record structure (all levels)

- 139 characters per record + CRLF (last line unterminated). Bytes below are
  1-based per the layout xlsx; Python slice = `line[start-1:end]`.
- Bytes 1-126 data, 127-129 NSC, 130-139 multiplier (two implied decimals).
- **Weight = MLT/100** and nothing else: this is final-multiplier-posted data,
  the layout has no subsample-FSU (NSS) field, and README76_S120 says to
  aggregate directly after applying the weights. (Unlike PLFS there is NO
  NSS=NSC halving rule here.)
- Levels = blocks of the schedule, one file per level: L01 block 1
  (identification), L02 block 3 (person roster, 466,527 records), L03 block 4
  (household characteristics incl religion), L04 block 4 items 15.1-15.5
  (scheme benefits), L05 block 5 (drinking water + bathroom + latrine +
  handwashing), L06 block 6 (house structure + electricity + micro
  environment), L07 block 7 (dwelling particulars), L08 block 8
  (migration/slum), L09 block 2 (ops metadata).
- L06/L07/L08 exist only for households living in houses (106,804 of
  106,838; tenurial status code 6 "no dwelling" households are absent), so
  published electricity/pucca shares use that smaller universe.

## Household key (join across levels)

FSU serial no. bytes 4-8 + second-stage stratum byte 30 + sample household
no. bytes 31-32 (`line[3:8] + line[29:32]`). Unique on every
household-level file; person file L02 additionally has person serial no.
bytes 38-39. Sector (byte 15: 1 rural, 2 urban) and the weight ride on every
record of every level.

## Fields used (1-based bytes)

| Field | Level | Bytes | Codes that matter |
|---|---|---|---|
| Sector | any | 15 | 1 rural, 2 urban |
| Religion of head | L03 | 42 | 1 Hindu, 2 Islam, 3 Christian, 4 Sikh, 5 Jain, 6 Buddhist, 7 Zoroastrian, 9 other |
| Social group | L03 | 43 | 1 ST, 2 SC, 3 OBC, 9 others |
| Tenurial status | L03 | 96 | 6 = no dwelling (explains the L06-L08 universe) |
| Principal drinking-water source | L05 | 40-41 | improved = 01-08, 10, 11, 12, 14 (Report 584 para 3.4.5); 02 = piped into dwelling |
| Water sufficient all year | L05 | 42 | 1 yes |
| Access to water source | L05 | 55 | 1 exclusive ... |
| Distance to water source | L05 | 56 | 1 within dwelling, 2 within premises; blank for ~600 hh (counted as not-within) |
| Access to bathroom | L05 | 90-91 | 5 = none |
| Access to latrine | L05 | 94 | 1 exclusive, 2 common in building, 3/4 public, 9 other, 5 none |
| Type of latrine | L05 | 95-96 | improved = 01, 02, 03, 04, 06, 07, 10; 11 = not used |
| Electricity for domestic use | L06 | 56 | 1 yes |
| Floor type | L07 | 80 | (1 mud ... 9 others) |
| Wall type | L07 | 81 | pucca = 5-9 (timber, burnt brick/stone, metal sheet, cement/RCC, other pucca) |
| Roof type | L07 | 82 | pucca = 5-9 |

Pucca structure = wall AND roof both pucca (reproduces Statement 22's
76.7 rural / 96.0 urban / 83.3 all exactly).

## Validation anchors (NSS Report 584, all-India R/U/All)

| Indicator | Rural | Urban | All |
|---|---|---|---|
| Improved water source | 94.5 | 97.4 | 95.5 |
| Water within premises | 58.2 | 80.7 | 65.9 |
| Improved water within premises | 56.1 | 78.6 | 63.8 |
| Piped into dwelling | 11.3 | 40.9 | 21.4 |
| Electricity (living in houses) | 93.9 | 99.1 | 95.7 |
| Pucca structure (living in houses) | 76.7 | 96.0 | 83.3 |
| Access to latrine | 71.3 | 96.2 | 79.8 |
| Exclusive access to latrine | 63.2 | 77.6 | 68.1 |

"Exclusive access to improved latrine" (the composite served to the
dashboard) has no all-India anchor inside the Report 584 PDF (its
Appendix-A Tables 57.1/57.2 are not part of the file MoSPI serves); both
components are anchored above instead.

## Gotchas

- mospi.gov.in drops long transfers: download with resume (`curl -C -`) and
  verify byte counts (139+2 per record) before trusting a file.
- Blank distance-to-water (271 improved-source households) is why the
  within-premises composites sit 0.2pp under the published cells; Report 584
  evidently treated blanks differently. Kept strict here.
- L09 (block 2, ops metadata) has 106,992 records - more than households;
  do not use it as a household frame.
- Religion codes 5-9 are kept in "all" but not extracted separately
  (unweighted households: Jain 285, Buddhist 1,086, Zoroastrian 14,
  other 1,888; vs Hindu 81,825, Muslim 13,790, Christian 6,338, Sikh 1,612).
