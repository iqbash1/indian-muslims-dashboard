# Runbook: NCRB Crime in India (CII)

## Source identity

- Manifest entry: `ncrb-crime`
- Publisher: National Crime Records Bureau, Ministry of Home Affairs.
- Role: feeds the civic-cluster metric `communal-incidents-govt`
  — the NCRB-classified count of communal/religious incidents,
  national time series **2015–2023 (9 years, no gaps)**.

## Targets

| target_id | year | url | archived | sha256 (first 12) |
|---|---|---|---|---|
| cii-2017-table-1-2 | 2017 | Wayback `20191203051255id_` of `ncrb.gov.in/StatPublications/CII/CII2017/pdfs/Table%201.2.pdf` | sources/ncrb-crime/cii-2017-table-1-2.pdf | 8649a65bb843 |
| cii-2018-table-1-2 | 2018 | Wayback `20200125083810id_` of `ncrb.gov.in/StatPublications/CII/CII2018/pdfs/Table%201.2.pdf` | sources/ncrb-crime/cii-2018-table-1-2.pdf | 8a1d63b984fc |
| cii-2021-table-1-2 | 2021 | Wayback `20230923181445id_` of `ncrb.gov.in/sites/default/files/CII-2021/TABLE%201.2.pdf` | sources/ncrb-crime/cii-2021-table-1-2.pdf | 3fb3baeb8525 |
| cii-2022-book1 | 2022 | ncrb.gov.in/uploads/nationalcrimerecordsbureau/custom/1701607577CrimeinIndia2022Book1.pdf | sources/ncrb-crime/cii-2022-book1.pdf | 7c5ee3128b0b |
| cii-2023-part1 | 2023 | ncrb.gov.in/uploads/files/1CrimeinIndia2023PartI.pdf | sources/ncrb-crime/cii-2023-part1.pdf | 553ac8b2eadf |

**Provenance note:** the 2017, 2018 and 2021 files are per-table extracted PDFs
(just Table 1.2, the IPC-crimes-by-state summary), pulled from the Wayback
Machine `id_` raw-bytes endpoint after NCRB's site reorg made the originals
404 on the live domain. The 2022 and 2023 files are the full Book-1 / Part-1
volumes (~25 MB) pulled directly from ncrb.gov.in. Wayback re-submit of the
live 2022/2023 URLs failed at pull time (non-blocking — the local SHA256-
sidecared L1 archive is authoritative).

## Religion / communal-incidents tables (verified via pdfplumber)

The relevant row in NCRB's IPC-crimes-by-state table is **23.1 Communal /
Religious** (row labelling stable from CII 2016 onward). For per-table PDFs
(2017/2018/2021) the row sits on the only data page; for the full Book-1
volumes (2022/2023) it's on Table 1.2 around page **35**, with the state-
level disaggregation on Table 1A.4 around page **67**.

The 2015 report cannot reach this metric — pre-2016 reports used a different
table structure with no "23.1 Communal/Religious" row. **Pre-2015 hard wall.**

The extractor (`transform/ncrb/extract_communal_crime.py`) handles
two source kinds:
- `main` — full CII volume; locates Table 1.2 + Table 1A.4 by caption
- `table-1-2` — per-table standalone PDF; scans across pages, no state data

Output: unified `extracted/ncrb-crime/cii-communal-incidents.csv` combining
all year-files (built-in consistency check — overlap years 21/22 must match
exactly across sources, currently 2022 from the per-table file matches the
2022 from Book-1).

## Canonicalization

`transform/canonicalize/communal_incidents_govt.py` emits two views:
- National time series **2015–2023** (9 years, no gaps; dedupes overlap)
- State-level breakdowns for the most recent years (2022, 2023)

## Resulting national series

| year | incidents |
|---|---|
| 2015 | 789 |
| 2016 | 869 *(PEAK)* |
| 2017 | 723 |
| 2018 | 512 |
| 2019 | 438 |
| 2020 | 857 *(CAA-NRC era)* |
| 2021 | 378 |
| 2022 | 272 |
| 2023 | 272 |

Post-2017 drop partly reflects several states ceasing to record "communal" as
a separate crime category (documented on the dashboard caveat). Civic-society
counts run higher — see `civic-incident-databases` runbook for the
side-by-side IHL count.

## Caveats (carried on canonical rows)

- **Several states no longer record communal as a separate crime category** in CII — the post-2017 drop is partly a recording-classification artefact, not necessarily a real decline.
- **Religion of victim / perpetrator is rarely published** in CII — the count is incidents, not communities.
- Civic-society incident databases (India Hate Lab) are shown on a separate dashboard tile, never aggregated with this NCRB count.

## When the next release lands

CII 2024 expected ~Nov 2026. New target should be added to `manifest/sources.yaml`
once the live NCRB URL resolves to a full Book/Part PDF; the extractor's `main`
source-kind path should handle it without modification (Table 1.2 caption is
stable). If only a per-table archive surfaces first, add it as a `table-1-2`
kind target and the canonicalizer's overlap-year check will validate it
against the prior year's Book.
