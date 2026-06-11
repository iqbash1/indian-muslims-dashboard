# Provenance: Household Consumer Expenditure, NSS 66th round, 2009-10

- **Survey idno:** `DDI-IND-NSSO-66-SCHEDULE-1.0T2`  (NADA catalog id 123)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/123
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: MPCE x religion

## Unit-level data file (kept LOCAL, not committed)
- `Nss66_1.0-type2_new format.rar`  (56,944,207 bytes)
- sha256 `47839089d2b26be59ac3c3dc643e09fc81147528c102ff44684d9158446a3c63`
- archived at `~/Desktop/nada-work/ces-2009-10/Nss66_1.0-type2_new format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-NSSO-66-SCHEDULE-1.0T2 ~/Desktop/nada-work/ces-2009-10
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-NSSO-66-SCHEDULE-1.0T2.xml`
- `Estimation procedure66.pdf`
- `Schedule 1.0 66 Type 2.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
