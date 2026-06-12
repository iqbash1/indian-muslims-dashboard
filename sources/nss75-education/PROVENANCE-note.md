# NSS 75th round Sch 25.2 (Household Social Consumption: Education, 2017-18) - TXT mirror provenance

The current NADA catalog (id 151, idno
`DDI-IND-MOSPI-NSSO-75Rnd-Sch25.2-July2017-June2018`) distributes this
survey's unit data ONLY as a proprietary `.Nesstar` binary inside
`Round75sch252Data.rar` (banked as the catalog-channel L1 in
`sources/nada/education-2017-18/`, which also carries the layout
`datalay75_252.xls`, `README75.pdf` and the schedule `Sch_25.2.pdf`).

The ORIGINAL fixed-width TXT distribution survives in an unlinked but live
directory on mospi.gov.in, the same Drupal-era file store that hosts the
published key-indicators report:

    https://www.mospi.gov.in/sites/default/files/NSS75252E/

Files pulled 2026-06-11 (server Last-Modified 23 Nov 2019), kept LOCAL at
`~/Desktop/nada-work/education-2017-18-alt/` (~170 MB; provenance-only, not
committed). All 8 level files reproduce the README75_252 record counts
byte-exactly at records x (142+2) - 2:

| File | Records |
|---|---|
| R75252L01.TXT | 113,757 |
| R75252L02.TXT | 113,757 |
| R75252L03.TXT | 3,606 |
| R75252L04.TXT | 513,366 |
| R75252L05.TXT | 152,992 |
| R75252L06.TXT | 152,558 |
| R75252L07.TXT | 133,464 |
| R75252L08.TXT | 6,610 |

Total 1,190,110 records. URL pattern:
`https://www.mospi.gov.in/sites/default/files/NSS75252E/R75252L01.TXT` ...
`R75252L08.TXT`. SHA256 of every file: `SHA256SUMS.txt` in this directory.

`KI_Education_75th_Final.pdf` (NSS Report 585 key indicators, 10,982,166
bytes, committed here via LFS) is the validation-anchor document, fetched
from the same directory: the extractor gates on its Statement 19 (average
basic-course expenditure per student by course type, nine cells) and
Statement 21 (the same by school level for general-course students,
eighteen cells).

Byte map and extraction gotchas: `nada/education-layout-map.md`. Extractor:
`transform/education/extract_education_2017_by_religion.py`. Runbook:
`docs/runbooks/cmse-education.md`.

Download with resume (`curl -C -`) - mospi.gov.in drops long transfers -
and verify byte counts before trusting a file.
