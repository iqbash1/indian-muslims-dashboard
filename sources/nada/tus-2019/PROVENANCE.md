# Provenance: Time Use Survey, 2019

- **Survey idno:** `DDI-IND-CSO-TUS-2019-19`  (NADA catalog id 223)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/223
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: time-use minutes x religion (niche new metric)

## Unit-level data file (kept LOCAL, not committed)
- `Unit level data of TUS 2019.zip`  (23,259,826 bytes)
- sha256 `e00ee09d15d7d38efe913484c141ba5f558999cfe4eb00950cfa6a5819a6783e`
- archived at `~/Desktop/nada-work/tus-2019/Unit level data of TUS 2019.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-CSO-TUS-2019-19 ~/Desktop/nada-work/tus-2019
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Data_Layout_TUS106.xls`
- `DDI-IND-CSO-TUS-2019-19.xml`
- `Estimation procedure_TUS.pdf`
- `README_TUS106.pdf`
- `State_District_List_TUS.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
