# Provenance: Periodic Labour Force Survey 2019-20

- **Survey idno:** `DDI-IND-CSO-PLFS-2019-20`  (NADA catalog id 217)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/217
- **Pulled:** 2026-06-10 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `CSV_PLFS_19_20.zip`  (19,212,621 bytes)
- sha256 `dcd56e240a50fedaaa0878a658e50c64cd5675add89327dd5a0eca2809211b23`
- archived at `~/Desktop/nada-work/plfs-2019-20/CSV_PLFS_19_20.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-CSO-PLFS-2019-20 ~/Desktop/nada-work/plfs-2019-20
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Data_Layout_PLFS.xlsx`
- `District_codes_PLFS_Panel_2_201920_202021.xlsx`
- `Estimation_Procedure_PLFS.pdf`
- `README.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
