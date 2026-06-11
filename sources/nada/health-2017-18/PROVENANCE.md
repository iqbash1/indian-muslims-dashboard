# Provenance: Household Social Consumption: Health, NSS 75th round 2017-18 (Sch 25.0)

- **Survey idno:** `DDI-IND-MOSPI-NSSO-75Rnd-Sch25.0-July2017-June2018`  (NADA catalog id 152)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/152
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE for OOP health spending x religion; morbidity rate = avoid

## Unit-level data file (kept LOCAL, not committed)
- `Round75sch250Data.rar`  (14,887,767 bytes)
- sha256 `0399625ef40fe2c3badaefa088fd5e5110e30ed0b62c9a45791e8ad31c28ff2d`
- archived at `~/Desktop/nada-work/health-2017-18/Round75sch250Data.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-75Rnd-Sch25.0-July2017-June2018 ~/Desktop/nada-work/health-2017-18
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `datalay75_250.xls`
- `DDI-IND-MOSPI-NSSO-75Rnd-Sch25.0-July2017-June2018.xml`
- `Estimation_Procedure_NSS_751602843187634.pdf`
- `nic_amendment_20081602843187059.pdf`
- `README75_25.pdf`
- `Sch_25.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
