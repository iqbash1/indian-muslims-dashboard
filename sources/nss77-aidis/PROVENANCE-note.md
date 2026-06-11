# NSS 77th round Schedule 18.2 (All-India Debt & Investment Survey, January-December 2019) - plain fixed-width TXT unit-level data

Fetched: 2026-06-11 (Pacific), by direct HTTPS download.

## Source

MoSPI's own file store for this survey's release page, still live (the files
are no longer linked from the React-era site, but the directory serves them
with their original August 2021 Last-Modified stamps):

    https://www.mospi.gov.in/sites/default/files/NSS7718/r77182v1L01.TXT
    ... through ...
    https://www.mospi.gov.in/sites/default/files/NSS7718/r77182v1L17.TXT   (Visit 1)
    https://www.mospi.gov.in/sites/default/files/NSS7718/r77182v2L01.TXT
    + L14, L15, L16, L17, L18                                              (Visit 2)

Case matters: lowercase stem, UPPERCASE `.TXT` (the README prints the names
in lowercase).

- Server `Last-Modified`: 16 Aug 2021 07:14-07:16 GMT for all seventeen
  Visit-1 files, i.e. the original August 2021 data-release vintage (the
  AIDIS press note is dated 24.08.2021).
- The owning (now deleted) Drupal page was
  `unit-level-data-report-nss-77-th-round-schedule-182-january-2019-–-december-2019-debt-and-investment`,
  found via its Wayback-archived mospi.NIC.in twin (single capture,
  2021-11-17). The page links the same directory's README77182_v1m.pdf /
  README77182_v2m.pdf ("README 77th Round Schedule-18.2 (Download Data
  Layout & Unit Level Data)"), instructions volumes, estimation procedure
  and the final tabulation plan.
- Same-directory documentation fetched live and stored here or hash-recorded:
  README77182_v1m.pdf + README77182_v2m.pdf (record counts + record format +
  multiplier rule), NSS_77th_Layout_Sch_18.2_mult_post.xls (byte layout, the
  authority for every offset in nada/aidis-layout-map.md),
  Final_Tabulation_Plan_NSS77R_Sch18.2.pdf (the official AVA/AOD recipe:
  fetched from `Final Tabulation Plan _NSS 77th R_Sch.18.2.pdf`, space and
  all), 77th_V_I_Final.pdf (instructions to field staff Vol I: block 11a
  item list, credit-agency codes; 5.8 MB, kept local and hash-recorded).
- Validation anchors come from the AIDIS press note (also stored here):
  https://www.mospi.gov.in/sites/default/files/press_release/press_note-AIDIS-240821.pdf

## Relation to the NADA distribution

The NADA catalog entry for the same survey
(https://microdata.gov.in/NADA/index.php/catalog/156, idno
DDI-IND-MOSPI-NSSO-77Rnd-Sch18.2-January2019-December2019) distributes the
data only as Round77sch18pt2Data.rar containing a proprietary
NSS77_18pt2study.Nesstar binary (banked in ../nada/aidis-2018-19/). These TXT
files are the same survey's original plain-text distribution. The NADA DDI's
per-level caseQnty figures match the README record counts file-for-file -
the two distributions describe identical data.

## Verification against README77182_v1m.pdf

Record length 139 data chars + CRLF (141 bytes/record); bytes 1-126 data,
127-129 NSC, 130-139 multiplier (two implied decimals; final household
weight = MLT/100, no sub-sample halving in this round's posted data).

| file | README record count | downloaded records | bytes (139+CRLF) |
|------|--------------------:|-------------------:|-----------------:|
| r77182v1L01.TXT | 116,461 | 116,461 | 16,421,001 |
| r77182v1L02.TXT | 495,573 | 495,573 | 69,875,793 |
| r77182v1L03.TXT | 116,461 | 116,461 | 16,421,001 |
| r77182v1L04.TXT | 116,461 | 116,461 | 16,421,001 |
| r77182v1L05.TXT | 216,960 | 216,960 | 30,591,360 |
| r77182v1L06.TXT | 67,765 | 67,765 | 9,554,865 |
| r77182v1L07.TXT | 236,873 | 236,873 | 33,399,093 |
| r77182v1L08.TXT | 162,217 | 162,217 | 22,872,597 |
| r77182v1L09.TXT | 186,968 | 186,968 | 26,362,488 |
| r77182v1L10.TXT | 131,885 | 131,885 | 18,595,785 |
| r77182v1L11.TXT | 63,223 | 63,223 | 8,914,443 |
| r77182v1L12.TXT | 504,309 | 504,309 | 71,107,569 |
| r77182v1L13.TXT | 3,333 | 3,333 | 469,953 |
| r77182v1L14.TXT | 178,971 | 178,971 | 25,234,911 |
| r77182v1L15.TXT | 16,656 | 16,656 | 2,348,496 |
| r77182v1L16.TXT | 51,680 | 51,680 | 7,286,880 |
| r77182v1L17.TXT | 51,680 | 51,680 | 7,286,880 |

Total 2,717,476 records - matches the README exactly. 116,461 households
(69,455 rural + 47,006 urban), matching the press note exactly. Visit-2
files (542,364 records per README77182_v2m.pdf) are banked alongside for
future capital-expenditure work; only Visit 1 feeds the wealth metrics.

Estimate validation: transform/aidis/extract_wealth_2018_by_religion.py (in
this repo) reproduces the press-note all-India figures; see the validation
table in that script's output (AVA/AOD/IOI/institutional share + the
physical/financial asset split and AODL as diagnostics).

SHA256 of every file: see SHA256SUMS.txt (verified after download). The
~450 MB of TXT stays local at `~/Desktop/nada-work/aidis-2018-19-alt/`;
this directory commits the two READMEs, the layout xls, the tabulation
plan and the press note.
