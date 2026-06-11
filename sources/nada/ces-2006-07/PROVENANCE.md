# Provenance: Household Consumer Expenditure, NSS 63rd round, 2006-07

- **Survey idno:** `DDI-IND-MOSPI-NSSO-63Rnd-Sch1.0-2006-07`  (NADA catalog id 114)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/114
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: MPCE x religion

## Unit-level data file (kept LOCAL, not committed)
- `Household Consumer Expenditure, NSS 63rd Round July 2006 - June 2007_Csv.zip`  (69,025,236 bytes)
- sha256 `a28e87f48a921fd33fc745254bb76198003d7a941a581c0d63e6319448d387ec`
- archived at `~/Desktop/nada-work/ces-2006-07/Household Consumer Expenditure, NSS 63rd Round July 2006 - June 2007_Csv.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-63Rnd-Sch1.0-2006-07 ~/Desktop/nada-work/ces-2006-07
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Estimation Procedure_63rd Round.pdf`
- `Schedule 0pt0 List Of Households And Non-Agricultural Enterprises.pdf`
- `Schedule 1pt0  Consumer Expenditure.pdf`
- `Schedule_63_1.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
