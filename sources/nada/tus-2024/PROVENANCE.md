# Provenance: Time Use Survey, 2024

- **Survey idno:** `DDI-IND-NSO-TUS-2024-24`  (NADA catalog id 236)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/236
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: time-use minutes x religion (niche new metric)

## Unit-level data file (kept LOCAL, not committed)
- `Date of Survey_TUS2024(which has the household level file structure).zip`  (1,050,997 bytes)
- sha256 `8b9f9091a454220816073b7bf9d6072e36f51ac9b151ab3dc51a407be38acf07`
- archived at `~/Desktop/nada-work/tus-2024/Date of Survey_TUS2024(which has the household level file structure).zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-NSO-TUS-2024-24 ~/Desktop/nada-work/tus-2024
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `CODEs for Blocks of Sch 10.6 (2).xlsx`
- `Data_Layout_TUS_2024 (1).xlsx`
- `DDI-IND-NSO-TUS-2024-24.xml`
- `Note_for_data_user (1).docx`
- `README_TUS_2024 (1).docx`
- `SampleDesign_EstimationProcedure_TUS 2024.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
