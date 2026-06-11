# Provenance: Household Consumer Expenditure, NSS 61st round, Jul2004-Jun2005 (the Sachar round)

- **Survey idno:** `DDI-IND-MOSPI-NSSO-61Rnd-Sch1-July2004-June2005`  (NADA catalog id 108)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/108
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: MPCE x religion (intended use; reproduces Sachar from microdata)

## Unit-level data file (kept LOCAL, not committed)
- `Household Consumer Expenditure, July 2004 - June 2005_Csv.zip`  (148,594,858 bytes)
- sha256 `5cef196388520b68c6214ec85f3412a26f68e6bd59e8440bb14ac28e11246f91`
- archived at `~/Desktop/nada-work/ces-2004-05/Household Consumer Expenditure, July 2004 - June 2005_Csv.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-61Rnd-Sch1-July2004-June2005 ~/Desktop/nada-work/ces-2004-05
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Estimation_Procedure_61.pdf`
- `ihsn_nsso_61_sch_1pt0_cons_exp.pdf`
- `NCO_1968-2 digit_codes.pdf`
- `NCO_1968-3_digit_codes.pdf`
- `Schedule_1pt0_Consumer_Expenditure.pdf`
- `Schedule_1pt0_NSS_Round_61.pdf`
- `State_Codes_61.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
