# Provenance: Employment, Unemployment & Migration, NSS 64th round, 2007-08

- **Survey idno:** `IND-NSSO-EUMS-2007-v1`  (NADA catalog id 117)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/117
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `Emp_Unemp_2007_2008_CSV.zip`  (49,384,022 bytes)
- sha256 `b2f94588fcaf237a4da7798f6482b6ce4a48b30e5d8c274b2dfda45d8e9bbd4f`
- archived at `~/Desktop/nada-work/eus-2007-08/Emp_Unemp_2007_2008_CSV.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget IND-NSSO-EUMS-2007-v1 ~/Desktop/nada-work/eus-2007-08
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Estimation_Procedure_NSS64R.pdf`
- `IHSN_Study_Report_NSS64R_Schedule_10dot2.pdf`
- `NSS64-Schedule-10dot2.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
