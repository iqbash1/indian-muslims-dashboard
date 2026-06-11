# Provenance: Periodic Labour Force Survey 2017-18 (NSS, Jul2017-Jun2018)

- **Survey idno:** `DDI-IND-CSO-PLFS-2017-18`  (NADA catalog id 204)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/204
- **Pulled:** 2026-06-10 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion is the intended cross-tab

## Unit-level data file (kept LOCAL, not committed)
- `CSV_PLFS_July2017_June2018.zip`  (13,751,616 bytes)
- sha256 `b9622692d7995e1f22e77f720da63eefef616a97a3760481413503ec41d807f5`
- archived at `~/Desktop/nada-work/plfs-2017-18/CSV_PLFS_July2017_June2018.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-CSO-PLFS-2017-18 ~/Desktop/nada-work/plfs-2017-18
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Data_LayoutPLFS_(1).xlsx`
- `District_codes_PLFS_Panel_1_201718_201819.xlsx`
- `Estimation_Procedure_PLFS_(1).doc`
- `README.doc`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
