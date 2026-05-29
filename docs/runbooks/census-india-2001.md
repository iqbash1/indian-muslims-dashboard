# Runbook: Census of India 2001

## Source identity

- Manifest entry: `census-india-2001`
- Publisher: Office of the Registrar General & Census Commissioner, MoHA
- Home: https://censusindia.gov.in/
- Cadence: 10-year (prior decennial round to Census 2011)

## Why this source

Pulled to turn the Census demographic + education metrics into decennial
**2001 → 2011 trends**. Same table codes and definitions as the 2011 round
(C-1 population, C-9 education-by-religion age 7+), so the two rounds form a
clean time series with no methodology break.

| metric | 2001 table | 2011 table | trend |
|---|---|---|---|
| `sex-ratio` | C-01 (persons/males/females) | C-15 (all ages) | 2001 → 2011 |
| `lit-7plus` | C-09 (literate / total, age 7+) | C-09 | 2001 → 2011 |

The all-ages total-residence sex ratio is **table-invariant**: computing the
2011 ratio from C-01 reproduces the C-15 figure exactly (951.3 / 939.1 / 942.7
for Muslim / Hindu / all), so sourcing 2001 from C-01 is directly comparable to
the C-15-sourced 2011 row.

## Phase 1 targets

| target_id | description | status |
|---|---|---|
| c01-population-by-religion | C-1 Population by Religious Community, India 2001 (national + states) | verified |
| c09-education-by-religion | C-9 Educational Level by Religious Community and Sex, age 7+, India 2001 | verified |

## URL discovery procedure

2001 religion tables live in the censusindia.gov.in **NADA** catalog under the
idno prefix `PC01_*` (vs `PC11_*` for 2011). The all-India file uses state code
`00` in the filename (e.g. `PC01_C01_00.xls`); per-state files use the state
code (UP = `PC01_C01_09.xls`).

The NADA web pages are JS-light enough to grep, and there is a JSON search API:

```
# find the catalog id for a table
curl -sk "https://censusindia.gov.in/nada/index.php/api/catalog/search?sk=Educational%20level%20religious%20community%20age%207&ps=30" \
  | python3 -c "import sys,json;[print(r['idno'],r['id'],r['title']) for r in json.load(sys.stdin)['result']['rows']]"

# find the download link on a catalog page
curl -sk "https://censusindia.gov.in/nada/index.php/catalog/<id>" \
  | grep -oE '/nada/index.php/catalog/<id>/download/[0-9]+/[A-Za-z0-9_%.-]+'
```

`-k` (or pull.py's `truststore`) is required — censusindia.gov.in serves a cert
chain Python's bundled CAs reject.

## Verified URLs log

| target_id | url | verified_on | content_length | http_status |
|---|---|---|---|---|
| c01-population-by-religion | https://censusindia.gov.in/nada/index.php/catalog/21462/download/24594/PC01_C01_00.xls | 2026-05-29 | 72,192 | 200 |
| c09-education-by-religion | https://censusindia.gov.in/nada/index.php/catalog/22250/download/25381/PC01_C09_00.xls | 2026-05-29 | 6,852,608 | 200 |

## Archived files (first pull)

| target_id | archived path | sha256 (first 16) | pulled_at |
|---|---|---|---|
| c01-population-by-religion | sources/census-2001/c-series/c01-population-by-religion.xls | b459efe12563a9a1 | 2026-05-29T05:09:51Z |
| c09-education-by-religion | sources/census-2001/c-series/c09-education-by-religion.xls | f321cba7ff4138da | 2026-05-29T05:10:36Z |

Wayback: C-01 mirrored; C-09 (6.5 MB) failed the `/save/` endpoint — the
project's recurring >~5 MB pattern. Local L1 + SHA256 sidecar is authoritative.

## File layout (for extractors)

Both files are legacy **BIFF .xls** — read with `xlrd`, not openpyxl.

- **C-01** sheet `C01T`, data from row 7. Cols: 0 Table, 1 State, 2 Distt,
  3 Tehsil, 4 Town, 5 Area, 6 Total/Rural/Urban, then 9 religion triplets
  (persons/males/females) at cols 7,10,13,…,31 — identical column layout to the
  2011 C-1 MDDS file. National = state `00` / distt `00`; no district rows in
  the all-India file.
- **C-09** sheet `Sheet1`, data from row 7. Cols: 0 Table, 1 State, 2 Distt,
  3 Tehsil, 4 Area, 5 Total/Rural/Urban, 6 Religion, 7 Age-group, then measure
  triplets Total Population (8), Illiterate (11), Literate (14). Religion labels:
  "All Religious Communities", "Hindu", "Muslim", "Christian", "Sikh",
  "Buddhist", "Jain", "Other Religious Communities" (note: 2011 said "Other
  religions and persuasions"). Age groups: Total, 0-6, single ages 7-19, broad
  bands, "Age not stated". The extractor keeps only Total / 0-6 / Age-not-stated
  (the literacy inputs) to avoid a 30 MB L2 of unused age detail.

## Re-derived national values (cross-check vs published Census 2001)

| metric | Muslim | Hindu | all-India | published |
|---|---|---|---|---|
| literacy 7+ | 59.17 | 65.13 | 64.88 | Muslim 59.1, Hindu 65.1, India 64.8 ✓ |
| sex ratio | 936.1 | 930.5 | 932.9 | Muslim 936, Hindu 931, India 933 ✓ |

## Known issues

- Legacy `.xls` (BIFF) — `xlrd` only; openpyxl will not open these.
- "Other Religious Communities" label differs from the 2011 wording; both map
  to canonical `other`.
- All-India 2001 C-1 carries national + states only (no districts); 2011 has
  district rows from C-15. The trend cards use the national series, so this is
  cosmetic for the dashboard.

## If a 1991 round is added later

- 1991 religion tables are poorly digitized and Jammu & Kashmir was not
  enumerated in 1991 — expect gaps. Add as a separate `census-india-1991`
  source if attempted; do not backfill into this entry.
