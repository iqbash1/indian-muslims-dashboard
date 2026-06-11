# Provenance: Periodic Labour Force Survey 2022-23

- **Survey idno:** `DDI-IND-CSO-PLFS-2022-23`  (NADA catalog id 210)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/210
- **Pulled:** 2026-06-10 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `Data_in_CSV.zip`  (21,663,733 bytes)
- sha256 `071cbaff198a992d821e28556c390faf8209e3c3345f6f48339078c8d01e3532`
- archived at `~/Desktop/nada-work/plfs-2022-23/Data_in_CSV.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-CSO-PLFS-2022-23 ~/Desktop/nada-work/plfs-2022-23
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `2_2_Schedule10pt4_FIRSTVISIT_2022_23.pdf`
- `2_3 Schedule10pt4_REVISIT_2022_23.pdf`
- `3_1_Estimation_Procedure_PLFS.pdf`
- `Data_LayoutPLFS_2022_23.xlsx`
- `District_codes_PLFS_Panel_3_202122_202223.xlsx`
- `Note_on_changes_PLFS_2022_23.pdf`
- `README.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
