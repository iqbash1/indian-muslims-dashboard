# Provenance: Periodic Labour Force Survey 2020-21

- **Survey idno:** `DDI-IND-CSO-PLFS-2020-21`  (NADA catalog id 206)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/206
- **Pulled:** 2026-06-10 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `CSV_Unit_level_data_PLFS_July2020_June2021.zip`  (21,139,450 bytes)
- sha256 `d8ed360e1e0fd7f468bf01bf04575a4ee0e2238644f5a29110859d558b9c03f7`
- archived at `~/Desktop/nada-work/plfs-2020-21/CSV_Unit_level_data_PLFS_July2020_June2021.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-CSO-PLFS-2020-21 ~/Desktop/nada-work/plfs-2020-21
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Data_LayoutPLFS_2020_21_(3).xlsx`
- `District_codes_PLFS_Panel_2_201920_202021.xlsx`
- `EstimationProcedure_PLFS_(2).pdf`
- `plfsREADMEjuly20_jun21_1_(4).pdf`
- `Schedule10.4_FIRSTVISIT_(4).pdf`
- `Schedule10.4_REVISIT_(4).pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
