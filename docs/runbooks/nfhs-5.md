# Runbook: NFHS-5 (2019-21)

## Source identity

- Manifest entry: `nfhs-5`
- Publisher: International Institute for Population Sciences (IIPS), MoHFW
- Home: https://rchiips.org/nfhs/ (note: cert chain has had ALTNAME issues)
- Mirror: https://dhsprogram.com/ (DHS Program is the canonical English mirror)
- Cadence: ~5-year (NFHS-6 fieldwork underway as of 2026)

## Phase 1 targets

| target_id | description | status | size |
|---|---|---|---|
| india-report-fr375 | NFHS-5 India Report (FR375) — main report with religion crosstabs | verified | 10.9 MB |
| india-national-factsheet | NFHS-5 India National Factsheet | verified | 0.9 MB |
| compendium-phase-1 | NFHS-5 Compendium of Factsheets Phase-I (22 states/UTs) | verified | 7.3 MB |
| compendium-phase-2 | NFHS-5 Compendium of Factsheets Phase-II (remaining states/UTs) | verified | 6.2 MB |

## URL discovery procedure

The IIPS home site (rchiips.org/nfhs/) has had intermittent TLS issues (ALTNAME mismatch) and the file paths under `/NFHS-5Reports/` redirect or 404 across redesigns. The reliable source is the DHS Program publications site, which mirrors all IIPS-published NFHS-5 reports.

For each target:
1. Start from https://dhsprogram.com/publications/ → search NFHS-5 India
2. Or browse https://dhsprogram.com/publications/publication-OF43-Other-Fact-Sheets.cfm
3. Right-click PDF link, copy URL.
4. HEAD-check with curl to confirm 200 + content-type=application/pdf.
5. Update `manifest/sources.yaml` target entry and set `status: verified`.

## Verified URLs log

| target_id | url | verified_on | verified_by | content_length |
|---|---|---|---|---|
| india-report-fr375 | https://dhsprogram.com/pubs/pdf/FR375/FR375.pdf | 2026-05-27 | Iqbal (Claude-assisted) | 10,920,570 |
| india-national-factsheet | https://dhsprogram.com/pubs/pdf/OF43/India_National_Fact_Sheet.pdf | 2026-05-27 | Iqbal (Claude-assisted) | 920,595 |
| compendium-phase-1 | https://dhsprogram.com/pubs/pdf/OF43/NFHS-5_India_and_State_Factsheet_Compendium_Phase-I.pdf | 2026-05-27 | Iqbal (Claude-assisted) | 7,313,561 |
| compendium-phase-2 | https://dhsprogram.com/pubs/pdf/OF43/NFHS-5_India_and_State_Factsheet_Compendium_Phase-II.pdf | 2026-05-27 | Iqbal (Claude-assisted) | 6,181,705 |

## Archived files (first pull)

| target_id | archived path | sha256 (first 12) | pulled_at |
|---|---|---|---|
| india-report-fr375 | sources/nfhs-5/reports/india-report-fr375.pdf | ce1fa5e3c93e | 2026-05-27 |
| india-national-factsheet | sources/nfhs-5/reports/india-national-factsheet.pdf | 6feb023a7638 | 2026-05-27 |
| compendium-phase-1 | sources/nfhs-5/reports/compendium-phase-1.pdf | 5bcc2a37b13f | 2026-05-27 |
| compendium-phase-2 | sources/nfhs-5/reports/compendium-phase-2.pdf | 3e8ee12bb4a5 | 2026-05-27 |

## Wayback mirror status

| target_id | wayback status | notes |
|---|---|---|
| india-report-fr375 | failed (Cloudflare 523, retried 2x) | 10.9 MB exceeds Wayback's tolerance for origin response time; rely on local archive |
| india-national-factsheet | mirrored | |
| compendium-phase-1 | mirrored | |
| compendium-phase-2 | mirrored | |

**Pattern across the project:** Wayback's `/save/` endpoint consistently fails with Cloudflare 520/523 on files larger than ~5 MB (also seen on Census C-9 and C-15). Local SHA256-sidecared L1 archive is the authoritative copy; Wayback is supplementary. A future iteration could add archive.today as a fallback for large files.

## Where religion crosstabs actually live

- **India Report (FR375)** — Chapter 2 (Background characteristics) + Appendix tables. Key tables for religion crosstabs include: Table 2.3 (Population by religion), Table 2.x for educational attainment, fertility, anemia, etc. by religion. **This is the primary religion-disaggregated source.**
- **Compendia** — state factsheets do NOT typically include religion crosstabs at the state level (they're aggregate state numbers across all religions). Useful for state benchmarks, not religion comparisons.
- **Unit-level data** — DHS Program recodes (HR, IR, PR, KR, CR, MR files) carry religion as a household variable. Required for district-level religion crosstabs and any cell the published report doesn't tabulate. Free DHS registration needed.

## Known issues

- IIPS rchiips.org cert has intermittent issues; use dhsprogram.com mirror.
- "Volume II" was discussed in some online references but is not a separate published artifact — IIPS released the main India Report + subject reports (women's empowerment, etc.) instead.
- NFHS-6 will revise definitions for stunting, wasting, several maternal indicators. Mark `break_flag` on canonical rows that span NFHS-5 → NFHS-6.

## When NFHS-6 lands

- Create new manifest entry `nfhs-6` (do not overwrite the nfhs-5 entry).
- Replicate target structure.
- Run a methodology delta review across the indicators we use; mark canonical rows accordingly.

## Backup access

- Internet Archive (Wayback) snapshots of dhsprogram.com
- World Bank Microdata Library: https://microdata.worldbank.org/index.php/catalog/4482
- IIPS direct (when accessible): https://iipsindia.ac.in/
