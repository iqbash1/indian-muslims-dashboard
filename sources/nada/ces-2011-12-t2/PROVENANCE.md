# Provenance: Household Consumer Expenditure, NSS 68th round Type-2, 2011-12

- **Survey idno:** `DDI-IND-MOSPI-NSSO-68Rnd-Sch2.0-July2011-June2012`  (NADA catalog id 126)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/126
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: MPCE x religion

## Unit-level data file (kept LOCAL, not committed)
- `Nss68_1.0_Type2_new format.rar`  (70,748,801 bytes)
- sha256 `44182e5d991a529c8bba49168c40ae10dcb6fd40361481742d4a7bfbf9c202de`
- archived at `~/Desktop/nada-work/ces-2011-12-t2/Nss68_1.0_Type2_new format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-68Rnd-Sch2.0-July2011-June2012 ~/Desktop/nada-work/ces-2011-12-t2
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-68Rnd-Sch2.0-July2011-June2012.xml`
- `Estimation Procedure_68.pdf`
- `nic_amendment_2008.pdf`
- `Schedule_68_1.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
