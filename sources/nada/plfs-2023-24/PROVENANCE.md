# Provenance: Periodic Labour Force Survey 2023-24

- **Survey idno:** `DDI-IND-CSO-PLFS-2023-24`  (NADA catalog id 213)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/213
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `CSV_data_PLFS_2023_2024.zip`  (22,107,995 bytes)
- sha256 `ff896f6cfee80b59a5ab413c2df6b99638b39d850999fd7105c130cde85432ea`
- archived at `~/Desktop/nada-work/plfs-2023-24/CSV_data_PLFS_2023_2024.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-CSO-PLFS-2023-24 ~/Desktop/nada-work/plfs-2023-24
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `1_README.docx`
- `3_1_Estimation_Procedure_PLFS.pdf`
- `Data_LayoutPLFS_2023-24.xlsx`
- `District_codes_PLFS_Panel_4_202324_2024.xlsx`
- `Note_on_Updated_Instruction_for_PLFS_2023-24.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
