# Provenance: Employment & Unemployment, NSS 68th round, 2011-12 (last pre-PLFS)

- **Survey idno:** `DDI-IND-MOSPI-NSSO-68-10-2013`  (NADA catalog id 127)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/127
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `Nss68_10_new format.zip`  (43,124,832 bytes)
- sha256 `c629c177be3a906bf63aedfd540883bcdfc3690d2d2163e63f4f1ce116808ccf`
- archived at `~/Desktop/nada-work/eus-2011-12/Nss68_10_new format.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-68-10-2013 ~/Desktop/nada-work/eus-2011-12
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-68-10-2013.xml`
- `District_code.txt`
- `Estimation Procedure_68.doc`
- `Estimation_Procedure_68.doc`
- `layout_68_10.xls`
- `nic_amendment_2008.pdf`
- `Schedule_68_10.pdf`
- `State_code_68.doc`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
