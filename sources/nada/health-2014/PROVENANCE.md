# Provenance: Social Consumption: Health, NSS 71st round, Jan-Jun 2014

- **Survey idno:** `DDI-IND-MOSPI-NSSO-71Rnd-Sch25pt0-Jan-June-2014`  (NADA catalog id 135)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/135
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE for OOP health spending x religion; morbidity rate = avoid

## Unit-level data file (kept LOCAL, not committed)
- `CSV_NSS71_Health_Jan_Jun2014.zip`  (13,537,717 bytes)
- sha256 `fe82ee16c3d5219e57571f1d7a95fb6fc1eb91143326a4f512ccc9afbde306b2`
- archived at `~/Desktop/nada-work/health-2014/CSV_NSS71_Health_Jan_Jun2014.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-71Rnd-Sch25pt0-Jan-June-2014 ~/Desktop/nada-work/health-2014
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Estimation_NSS71.pdf`
- `nic_amendment_2008.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
