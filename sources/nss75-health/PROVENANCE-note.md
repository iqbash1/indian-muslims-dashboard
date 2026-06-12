# NSS 75th round Sch 25.0 (Household Social Consumption: Health, 2017-18) - TXT mirror provenance

The current NADA catalog (id 152, idno
`DDI-IND-MOSPI-NSSO-75Rnd-Sch25.0-July2017-June2018`) distributes this
survey's unit data ONLY as a proprietary `.Nesstar` binary inside
`Round75sch250Data.rar` (banked as the catalog-channel L1 in
`sources/nada/health-2017-18/`, which also carries the layout
`datalay75_250.xls`, `README75_25.pdf` and the schedule `Sch_25.pdf`).

The ORIGINAL fixed-width TXT distribution survives in an unlinked but live
directory on mospi.gov.in, the same Drupal-era file store that hosts the
published key-indicators report:

    https://www.mospi.gov.in/sites/default/files/NSS75250H/

Files pulled 2026-06-11 (server Last-Modified 23 Nov 2019), kept LOCAL at
`~/Desktop/nada-work/health-2017-18-alt/` (~180 MB; provenance-only, not
committed). All 13 level files reproduce the README75_250 record counts
byte-exactly at records x (142+2) - 2:

| File | Records |
|---|---|
| R75250L01.TXT | 113,823 |
| R75250L02.TXT | 113,823 |
| R75250L03.TXT | 555,352 |
| R75250L04.TXT | 2,537 |
| R75250L05.TXT | 93,925 |
| R75250L06.TXT | 93,925 |
| R75250L07.TXT | 93,925 |
| R75250L08.TXT | 43,240 |
| R75250L09.TXT | 43,240 |
| R75250L10.TXT | 43,240 |
| R75250L11.TXT | 42,762 |
| R75250L12.TXT | 70,258 |
| R75250L13.TXT | 32,257 |

Total 1,342,307 records. URL pattern:
`https://www.mospi.gov.in/sites/default/files/NSS75250H/R75250L01.TXT` ...
`R75250L13.TXT`. SHA256 of every file: `SHA256SUMS.txt` in this directory.

`KI_Health_75th_Final.pdf` (NSS Report 586 key indicators, 4,996,088 bytes,
committed here via LFS) is the validation-anchor document, fetched from the
same directory: the extractor gates on its Statement 3.15 (average medical
expenditure per hospitalisation case by hospital type, nine cells) and
Statement 3.19 (reimbursement share of medical expenditure).

Byte map and extraction gotchas: `nada/health-layout-map.md`. Extractor:
`transform/health/extract_health_2017_by_religion.py`. Runbook:
`docs/runbooks/nss-health.md`.

Download with resume (`curl -C -`) - mospi.gov.in drops long transfers -
and verify byte counts before trusting a file.
