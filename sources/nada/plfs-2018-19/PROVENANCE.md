# Provenance: Periodic Labour Force Survey 2018-19

- **Survey idno:** `DDI-IND-CSO-PLFS-2018-19`  (NADA catalog id 216)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/216
- **Pulled:** 2026-06-10 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `PLFS_2018_19_CSV.zip`  (18,913,869 bytes)
- sha256 `ef9934440e2258c28ebffaf442bcd89a3af7f36735b91e821e6489479367596d`
- archived at `~/Desktop/nada-work/plfs-2018-19/PLFS_2018_19_CSV.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-CSO-PLFS-2018-19 ~/Desktop/nada-work/plfs-2018-19
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Data_Layout_PLFS.xlsx`
- `District_codes_PLFS_Panel_1_201718_2018_19.xlsx`
- `README_July18_June19.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
