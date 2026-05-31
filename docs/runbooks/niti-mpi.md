# Runbook: NITI Aayog Multidimensional Poverty Index (MPI)

## Source identity

- Manifest entry: `niti-mpi`
- Publisher: NITI Aayog, Government of India. Underlying data: OPHI
  Multidimensional Poverty Index methodology applied to NFHS rounds.
- Role: would feed the income-cluster metric **`mpi-headcount`** (Muslim
  share of multidimensionally-poor population, or Muslim MPI headcount
  rate).
- **Status: pre-registered, not yet pulled.** Hardest-tier metric per the
  project roadmap — religion disaggregation isn't in NITI's main report.

## Why this is stub-only

NITI Aayog's "National Multidimensional Poverty Index — A Progress Review
2023" reports state-level MPI headcounts based on NFHS-5 (2019–21), but the
published report does NOT disaggregate by religion. State-level data is the
finest cut available in the public report.

To derive a Muslim MPI headcount nationally, two paths exist:

1. **OPHI India MPI dataset** — the Oxford Poverty and Human Development
   Initiative publishes the source MPI calculations including per-community
   breakdowns, but the religion breakdown is published only in academic
   research papers (e.g. Alkire-Foster type compilations from NFHS unit
   records), not in OPHI's main "Global MPI" dashboard.
2. **Direct calculation from NFHS-5 unit records** — apply the OPHI
   methodology (10 indicators across health, education, living standards)
   to NFHS-5 individual + household recodes (IAHR7DFL.zip + IAIR7DFL.zip
   on dhsprogram.com) filtered by religion. This is the same data-access
   path as the 4 other deferred NFHS unit-record metrics (clean-cooking-
   fuel, pucca-housing, bank-account, mean-yrs-schooling).

## Unblocking

Path 2 is cleanest. Requires:
1. Free user account at dhsprogram.com
2. Project application (~1-3 day approval for academic / journalistic use)
3. Download India 2019-21 recodes
4. Implement the 10-indicator MPI calculation + weighted aggregation by religion

When unblocked: register target(s), write extractor (likely consuming the
same NFHS-5 recodes as the other deferred metrics), write canonicalizer,
update this runbook.

## Caveats (when implemented)

- NFHS-5's coverage doesn't match the Census of India 2011 weights exactly;
  the headcount denominator should be NFHS-5's surveyed-population, not
  Census 2011 totals.
- NITI's published MPI uses 12 indicators (slightly different from OPHI's
  10); decide which methodology to apply and document on the canonical
  row's methodology_note.
