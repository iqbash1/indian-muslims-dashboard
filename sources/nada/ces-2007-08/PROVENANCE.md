# Provenance: Household Consumer Expenditure, NSS 64th round, 2007-08

- **Survey idno:** `IND-NSSO-HCES-2007-v1`  (NADA catalog id 116)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/116
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: MPCE x religion

## Unit-level data file (kept LOCAL, not committed)
- `Nss64_1.0_new format.rar`  (30,191,131 bytes)
- sha256 `97bde40d50e64a8562c54b385b1003bda42f62d2ddcd2458b5b3506d3178c7cb`
- archived at `~/Desktop/nada-work/ces-2007-08/Nss64_1.0_new format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget IND-NSSO-HCES-2007-v1 ~/Desktop/nada-work/ces-2007-08
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Estimation Procedure_64.pdf`
- `IND-NSSO-HCES-2007-v1.xml`
- `Schedule_64_1.0.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
