# Provenance: Household Social Consumption: Health, NSS 80th round 2025

- **Survey idno:** `DDI-IND-NSO-HSCHealth80R-Jan2025-Dec2025`  (NADA catalog id 290)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/290
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE for OOP health spending x religion; morbidity rate = avoid

## Unit-level data file (kept LOCAL, not committed)
- `CSV_data_household_social_consumption_heaith_Jan_Dec25.zip`  (16,241,961 bytes)
- sha256 `ee86814cb807017d042f4f649654d7cd485ea3c49d1ca5838571036b1930b68a`
- archived at `~/Desktop/nada-work/health-2025/CSV_data_household_social_consumption_heaith_Jan_Dec25.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-NSO-HSCHealth80R-Jan2025-Dec2025 ~/Desktop/nada-work/health-2025
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Datalayout_250_80R.xlsx`
- `Note_for_data_user.pdf`
- `README_HEALTH_25pt0.docx`
- `SampleDesign_EstimationProcedure_Health.pdf`
- `Schedule_ 0pt0_NSS80.pdf`
- `Schedule_25pt0_80R.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
