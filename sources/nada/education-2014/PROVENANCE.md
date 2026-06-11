# Provenance: Social Consumption: Education, NSS 71st round, 2014

- **Survey idno:** `IND-NSSO-SCES-2014-v1.0`  (NADA catalog id 136)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/136
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE for education spending x religion; literacy/GER = off-limits

## Unit-level data file (kept LOCAL, not committed)
- `CSV_Education_71_2014.zip`  (10,866,529 bytes)
- sha256 `59aa80327136dff926a4ac710d3bf4b6c99b4a541eaa571abc23c9f3d6b87d67`
- archived at `~/Desktop/nada-work/education-2014/CSV_Education_71_2014.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget IND-NSSO-SCES-2014-v1.0 ~/Desktop/nada-work/education-2014
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `nic_amendment_2008.pdf`
- `NSS71_Estimation_procedure.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
