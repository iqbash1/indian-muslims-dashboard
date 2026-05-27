# Runbook: Census of India 2011

## Source identity

- Manifest entry: `census-india-2011`
- Publisher: Office of the Registrar General & Census Commissioner, MoHA
- Home: https://censusindia.gov.in/
- Cadence: 10-year (2021 round indefinitely delayed as of 2026-05)

## Phase 1 targets

| target_id | description | status |
|---|---|---|
| c01-population-by-religion | C-1 Population by Religious Community (MDDS — all geography levels) | verified |
| c09-education-by-religion | C-9 Educational Level by Religious Community and Sex (age 7+) | verified |
| c15-religion-by-age-sex | C-15 Religious Community by Age Group and Sex | verified |

**Correction (2026-05-27):** The original draft listed `C-8` for education by religion. C-8 is by age/sex only; the correct table for education crossed with religion is **C-9**. Target ID and description updated.

**Housing & amenities deferred:** HH-series tables (drinking water, latrine, cooking fuel by religion) are not cleanly cross-tabulated with religion at the all-India level in Census 2011 published tables. NFHS-5 covers these metrics with religion crosstabs more cleanly and is the primary source for `pucca-housing`, `improved-sanitation`, `clean-cooking-fuel`, etc. (see `manifest/metrics.yaml`). The cross-check entry on those metrics will use Census 2011 HH-series as a sense-check if the maintainer chooses to add it later, but it is not blocking for Phase 1.

## URL discovery procedure

censusindia.gov.in has been redesigned multiple times; URLs in academic papers and old archives often 404. Procedure:

1. Start from https://censusindia.gov.in/census.website/data/census-tables.
2. For each target, navigate to the C-series or HH-series listing, filter to year 2011, locate the table by code (C-1, C-8, HH-4, HH-7).
3. Confirm the file is the All-India release (national + state crosstab). Some tables also have separate state-specific downloads — defer those to a later target ID.
4. Right-click the download link, copy the direct URL.
5. Open the URL in a new browser tab to confirm it serves the file directly (some links go through an interstitial wrapper).
6. Open the file and verify it contains a Religious Community dimension on the expected sheet/page.

For each verified URL:
- Update `manifest/sources.yaml` target entry: set `url:` and `status: verified`.
- Append a row to the verified-URLs log below.
- Run `python ingest/pull.py --source census-india-2011 --target <target_id> --dry-run`.
- Run without `--dry-run` to archive.

## Verified URLs log

| target_id | url | verified_on | verified_by | content_length | http_status |
|---|---|---|---|---|---|
| c01-population-by-religion | https://censusindia.gov.in/nada/index.php/catalog/11361/download/14474/DDW00C-01%20MDDS.XLS | 2026-05-27 | Iqbal (Claude-assisted) | 52,736 | 200 |
| c09-education-by-religion | https://censusindia.gov.in/nada/index.php/catalog/2493/download/5570/DDW-0000C-09.xlsx | 2026-05-27 | Iqbal (Claude-assisted) | 4,066,590 | 200 |
| c15-religion-by-age-sex | https://censusindia.gov.in/nada/index.php/catalog/11400/download/14513/DDW-0000C-15.XLSX | 2026-05-27 | Iqbal (Claude-assisted) | 423,733 | 200 |

## Archived files (first pull)

| target_id | archived path | sha256 (first 16) | pulled_at |
|---|---|---|---|
| c01-population-by-religion | sources/census-2011/c-series/c01-population-by-religion.xls | c3fee2bb235f4ef5 | 2026-05-27T17:46:53Z |
| c09-education-by-religion | sources/census-2011/c-series/c09-education-by-religion.xlsx | 48a5ba102279f6c1 | 2026-05-27T17:47:08Z |
| c15-religion-by-age-sex | sources/census-2011/c-series/c15-religion-by-age-sex.xlsx | ad1d2aa830ee6841 | 2026-05-27T17:47:15Z |

## Operational notes from first pull (2026-05-27)

- censusindia.gov.in serves a cert chain that Python's bundled CAs reject (works fine in curl/browser). Fix: `truststore` package delegates to the system trust store. Added to `requirements.txt` and patched into `ingest/pull.py`. This is the macOS-corporate-proxy case; on other machines the original cert path will work and truststore is harmless.
- File extensions vary: C-1 is `.XLS` (legacy), C-9 and C-15 are `.XLSX`. Sidecar `content_type` is `application/octet-stream` (server doesn't differentiate); the file's actual format will need detection in the extractor.

## Known issues

- Some C-series Excel files contain multi-sheet workbooks with merged-cell headers; L2 extraction will need per-table parsing logic.
- District-level tables for small religious groups have suppressed cells.
- The portal occasionally serves files as `.xls` despite a `.xlsx` link — check magic bytes after download.

## When the 2021 release lands

- Create a new manifest entry `census-india-2021` (do not overwrite the 2011 entry).
- Mirror target structure.
- Mark `break_flag: true` on canonical metric rows that span 2011 → 2021 if methodology changed.

## Backup access if censusindia.gov.in goes down

- Internet Archive Wayback Machine snapshots of censusindia.gov.in
- ICPSR (Inter-university Consortium for Political and Social Research)
- Harvard Dataverse (some C-tables mirrored)
- DataMeet community repository
