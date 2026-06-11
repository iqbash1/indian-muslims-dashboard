# Provenance: Periodic Labour Force Survey 2021-22

- **Survey idno:** `DDI-IND-CSO-PLFS-2021-22`  (NADA catalog id 214)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/214
- **Pulled:** 2026-06-10 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `PLFS_Data_2021-22_CSV.zip`  (21,010,019 bytes)
- sha256 `3910ada9382c110f4fe0964fb2a2ddc2d508f43319e575a182eeaed5f9647f75`
- archived at `~/Desktop/nada-work/plfs-2021-22/PLFS_Data_2021-22_CSV.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-CSO-PLFS-2021-22 ~/Desktop/nada-work/plfs-2021-22
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `2_2Schedule10dot4_FIRSTVISIT_28122020.pdf`
- `2_3Schedule10dot4_REVISIT_28122020.pdf`
- `3_1EstimationProcedure_PLFS.pdf`
- `4Data_LayoutPLFS_2021_22.xlsx`
- `District_codes_PLFS_Panel_3_202122_202223.xlsx`
- `README_Final.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
