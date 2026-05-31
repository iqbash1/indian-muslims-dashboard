# Runbook: RBI minority lending statistics

## Source identity

- Manifest entry: `rbi-minority-lending`
- Publisher: Reserve Bank of India.
- Role: would feed the finance-cluster metric **`minority-psl-share`** (Muslim
  share of priority sector lending under RBI's minority-community
  classification).
- **Status: pre-registered, not yet pulled.** Hardest-tier metric per the
  project roadmap.

## Why this is stub-only

RBI publishes priority-sector advances by minority community in its Annual
Report and in DBIE database extracts. The challenge:
1. The "minority community" classification aggregates Muslims with Christians,
   Sikhs, Buddhists, Parsis and Jains (per the National Commission for
   Minorities Act). Muslim-specific share is not directly published; it has to
   be derived from RBI's per-community state-wise tables when those are released
   (irregularly, often in special Parliament answers rather than the main
   Annual Report).
2. The DBIE database requires registration and the per-community tables
   change column structure across years, breaking simple extractors.

## Unblocking

Three paths, in increasing reliability:
1. **Parliament answers from MoMA** — when the Ministry of Minority Affairs
   gets asked about Muslim PSL share, the response cites an internal RBI
   table. These are intermittent and PIB doesn't bot-load reliably.
2. **DBIE database extract** — requires registered access. Once obtained,
   pull the per-community state-wise PSL table for at least 3 recent years.
3. **RTI to RBI** — request "Muslim share of priority-sector advances,
   national, FY2021–FY2024". Filing template: see `docs/rti-tracker.md`.

When unblocked: register one or more targets, write an extractor, write a
canonicalizer, then update this runbook with the actual table-locations.

## Caveats (when implemented)

- The aggregate "minority community" figure is published; Muslim-specific is
  rarer and may need cross-validation against MoMA Parliament answers.
- Year-over-year comparability requires checking that the PSL definition
  hasn't shifted (RBI does periodically revise PSL category boundaries).
