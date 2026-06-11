# NSS 76th round Schedule 1.2 (Drinking Water, Sanitation, Hygiene and Housing Condition, July-December 2018) - plain fixed-width TXT unit-level data

Fetched: 2026-06-10 (Pacific) / 2026-06-11 UTC, by direct HTTPS download.

## Source

MoSPI's own file store for this survey's release page, still live (the files
are no longer linked from the React-era site, but the directory serves them):

    https://www.mospi.gov.in/sites/default/files/NSS7612dws/R76120L01.TXT
    ... through ...
    https://www.mospi.gov.in/sites/default/files/NSS7612dws/R76120L09.TXT

- Server `Last-Modified`: 23 Nov 2019 07:01-07:02 GMT for all nine files,
  i.e. the original November 2019 data-release vintage.
- The owning (now Drupal-archived) page was
  `https://mospi.gov.in/unit-level-data-report-nss-76th-round-schedule-12-july-december-2018-drinking-water-sanitation`
  (Wayback snapshots from 2019-12-17 onward), which links the same
  directory's README76_S120.pdf ("README 76 Round Schedule 1.2 (Download
  Data Layout & Unit Level Data)") and Report_584_final.pdf.
- Same-directory documentation fetched live and stored here:
  README76_S120.pdf (record counts + record format + multiplier rule),
  Report_584_final.pdf (NSS Report 584, used for the validation gate),
  Data_Layout_NSS76_120.xlsx (byte layout; copied from the NADA pull in
  ../housing-water-2018/ and its live copy at the same MoSPI URL is
  byte-identical, sha256 8f111d1253b2cf18339003f0aa60700ffdd20d7c1b512e870659a5345055f3d1).

## Relation to the NADA distribution

The NADA catalog entry for the same survey
(https://microdata.gov.in/NADA/index.php/catalog/153, idno
DDI-IND-MOSPI-NSSO-76Rnd-Sch1.2-July2018-December2018) distributes the data
file only as Round76sch1dot2Data.rar containing a proprietary
NSS76CH1dot2DRINKING.Nesstar binary (see ../housing-water-2018/). These TXT
files are the same survey's original plain-text distribution; the
NADA-distributed layout xlsx describes exactly this fixed-width format.

## Verification against README76_S120.pdf

Record length 139 chars + CRLF; bytes 1-126 data, 127-129 NSC, 130-139
multiplier (two implied decimals; final weight = MLT/100).

| file | README record count | downloaded records | bytes (139+CRLF, last line unterminated) |
|------|--------------------:|-------------------:|-------------:|
| R76120L01.TXT | 106,838 | 106,838 | 15,064,156 |
| R76120L02.TXT | 466,527 | 466,527 | 65,780,305 |
| R76120L03.TXT | 106,838 | 106,838 | 15,064,156 |
| R76120L04.TXT | 106,838 | 106,838 | 15,064,156 |
| R76120L05.TXT | 106,838 | 106,838 | 15,064,156 |
| R76120L06.TXT | 106,804 | 106,804 | 15,059,362 |
| R76120L07.TXT | 106,804 | 106,804 | 15,059,362 |
| R76120L08.TXT | 106,804 | 106,804 | 15,059,362 |
| R76120L09.TXT | 106,992 | 106,992 | 15,085,870 |

Total 1,321,283 records - matches the README exactly. 106,838 households
(63,736 rural + 43,102 urban), matching NSS Report 584.

Estimate validation: transform/nss76/extract_housing_2018_by_religion.py (in
the Indian-Muslims repo) reproduces 24 published all-India cells of NSS
Report 584 (Statements 2.1, 5, 6, 7, 12.1, 22, 25) with worst gap 0.24
percentage points; most cells match to the printed decimal.

SHA256 of every file: see SHA256SUMS.txt (verified after download).
