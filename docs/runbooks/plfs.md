# Runbook: Periodic Labour Force Survey (PLFS)

## Source identity

- Manifest entry: `plfs`
- Publisher: National Statistical Office (NSO), MoSPI
- Home: https://www.mospi.gov.in/
- Cadence: annual (Jul-Jun reference period; report released ~3 months after period end) + quarterly urban bulletins

## Phase 1 targets

| target_id | description | status |
|---|---|---|
| annual-report-2023-24 | PLFS Annual Report Jul 2023 - Jun 2024 (main report) | verified |
| press-note-2023-24 | PLFS Press Note for Annual Report 2023-24 (summary) | verified |

## URL discovery procedure

MoSPI hosts PDFs under `mospi.gov.in/sites/default/files/publication_reports/` (full reports) and `/press_release/` (press notes). The landing page at `https://www.mospi.gov.in/annual-report-periodic-labour-force-survey-plfs-<year>` is the canonical entry but the page is JS-heavy and WebFetch doesn't always render the file URLs — use Google search with `site:mospi.gov.in filetype:pdf` as the reliable discovery path.

For each new annual release:
1. Search `"PLFS Annual Report <year>" site:mospi.gov.in filetype:pdf` for the main report.
2. Search `Press_note_AR_PLFS_<year>` for the press note.
3. Look for `Additional Tables of PLFS Annual Report <year>` — these often carry the religion crosstabs not in the main report.
4. HEAD-check each URL.
5. Update `manifest/sources.yaml`.

## Verified URLs log

| target_id | url | verified_on | verified_by | content_length |
|---|---|---|---|---|
| annual-report-2023-24 | https://mospi.gov.in/sites/default/files/publication_reports/AnnualReport_PLFS2023-24L2.pdf | 2026-05-27 | Iqbal (Claude-assisted) | 26,917,638 |
| press-note-2023-24 | https://mospi.gov.in/sites/default/files/press_release/Press_note_AR_PLFS_2023_24_22092024.pdf | 2026-05-27 | Iqbal (Claude-assisted) | 446,076 |

## Archived files (first pull)

| target_id | archived path | sha256 (first 12) | pulled_at |
|---|---|---|---|
| annual-report-2023-24 | sources/plfs/annual/plfs-annual-report-2023-24.pdf | ab4ead2cee18 | 2026-05-27 |
| press-note-2023-24 | sources/plfs/annual/plfs-press-note-2023-24.pdf | 969e90c48ace | 2026-05-27 |

## Where religion crosstabs actually live

PLFS Annual Reports typically tabulate by Social Group (SC/ST/OBC/Others) in the main body but religion is a schedule variable that surfaces in:
- **Appendix tables in the Annual Report** — Statement-style tables, look for "Religion" in the table titles.
- **Additional Tables release** — separate PDF for prior years (2022-23 had one) that carries the religion crosstabs not in the main report. Check if a 2023-24 Additional Tables release exists.
- **Unit-level data (NSSO website)** — definitive for any cell not in published tables; need to compute religion crosstabs ourselves.

For 2023-24 the Additional Tables release may not exist yet; if so, defer state-level religion crosstabs to unit-level computation or wait for the supplementary release.

## Known issues

- Religion in PLFS schedule but inconsistently tabulated in main report; expect to compute from unit-level for several metrics
- Sub-state Muslim subsamples thin; CIs widen quickly — set a sample-size floor in canonicalize scripts
- Annual report is large (~25 MB) — Wayback mirror will likely fail (>5 MB pattern)

## When PLFS 2024-25 lands

- Expected release ~Sep 2026 (3 months after Jun 2026 survey close).
- Create new manifest entry or just add new target IDs (`annual-report-2024-25`, `press-note-2024-25`).
- 2025 brings methodology changes per MoSPI's January 2025 announcement — review and mark `break_flag` on canonical rows if definitions change for our metrics.

## Backup access

- Internet Archive Wayback (smaller files like press notes; large report will likely fail)
- DGE (Directorate General of Employment) republishes PLFS summaries
- World Bank Microdata Library mirrors unit-level recodes
- microdata.gov.in NADA catalog: https://microdata.gov.in/NADA/index.php/catalog/PLFS
