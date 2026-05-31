# Runbook: Civic-tech incident databases (India Hate Lab + others)

## Source identity

- Manifest entry: `civic-incident-databases`
- Publisher: Multiple civic-tech / research initiatives. Currently
  in canonical: **India Hate Lab** (a project of the Center for the Study
  of Organized Hate). Pre-registered but not yet pulled: Documentation
  of the Oppressed, Hindutva Watch.
- Role: feeds the civic-cluster metric `communal-incidents-civic`
  (civic-society hate-speech-event counts, shown side-by-side with the
  NCRB government count on the dashboard but **never aggregated** —
  different units, different methodology).

## Targets

| target_id | year | url | archived | sha256 (first 12) |
|---|---|---|---|---|
| ihl-2023-annual | 2023 | csohate.org/wp-content/uploads/2024/07/report-India-Hate-Lab-Report-Final-13.pdf | sources/civic-databases/ihl-2023-annual-report.pdf | f07806811272 |
| ihl-2024-annual | 2024 | csohate.org/wp-content/uploads/2025/02/Hate-Speech-Events-in-India_Report_2024.pdf | sources/civic-databases/ihl-2024-annual-report.pdf | a3d09560ca0a |

## Extraction

No structured extraction — the headline counts are read directly from each
report's executive summary and hardcoded in
`transform/canonicalize/communal_incidents_civic.py`. The numbers are widely
cited and consistent across multiple secondary sources (The Quint, CNN, US
News, Scroll, CJP, etc.), so the headline aggregate is robust.

| year | hate-speech events |
|---|---|
| 2023 | 668 |
| 2024 | 1,165 *(+74.4% YoY)* |

## Why this isn't aggregated with NCRB

This is **the most important methodology note** on the dashboard for this
metric, called out on the card and in the canonical row:

| dimension | NCRB CII (`communal-incidents-govt`) | India Hate Lab (`communal-incidents-civic`) |
|---|---|---|
| unit | police-registered IPC violations | rallies / speeches / gatherings with hateful rhetoric |
| methodology | state-recording-dependent (several states no longer record) | civic-society manual classification of public events |
| count basis | incidents | events |
| time series | 2015→2023, 9 years | 2023, 2024 |
| 2023 figure | 272 | 668 |

These are different views of the same underlying phenomenon. Adding them
double-counts. Subtracting them double-discounts. The dashboard renders them
as **two separate tiles** so readers can hold both views simultaneously.

## Caveats (carried on canonical rows)

- **Methodology varies by source** in the civic-tech space. IHL counts hate-
  speech events; Documentation of the Oppressed and Hindutva Watch use
  different definitions and may double-count events that span multiple
  classification axes.
- **Civic-tech databases are contested.** Always shown as separate dashboard
  tile, **never aggregated with government sources.**
- IHL tracks hate speech events; **not directly comparable to NCRB rioting
  count** (different units).

## When the next release lands

IHL publishes annually around Feb-Mar covering the prior calendar year. Add
a new target row to `manifest/sources.yaml` once the new PDF URL is
verifiable on csohate.org; pull via `ingest/pull.py`; update the hardcoded
year-count map in `transform/canonicalize/communal_incidents_civic.py` after
reading the new executive summary.

Other civic-tech databases (Hindutva Watch, Documentation of the Oppressed)
would expand this source's coverage if/when their data becomes pullable in a
machine-readable form. Currently they publish event lists but no consolidated
annual counts that are directly addressable.
