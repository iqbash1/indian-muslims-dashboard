# Provenance: Comprehensive Modular Survey: Education, NSS 80th round 2025 (CMSE)

- **Survey idno:** `DDI-IND-MOSPI-NSS-CMSE80-2025`  (NADA catalog id 255)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/255
- **Pulled:** 2026-06-10 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE for education spending x religion; literacy/GER = off-limits

## Unit-level data file (kept LOCAL, not committed)
- `Data in CSV.zip`  (2,998,685 bytes)
- sha256 `3bc9b6831c8a7cffdcb70fd5ffafc224f9ff788e59f238736916722c16d7eb70`
- archived at `~/Desktop/nada-work/education-2025/Data in CSV.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSS-CMSE80-2025 ~/Desktop/nada-work/education-2025
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `CODEs for Blocks of Sch - CMS-Education.xlsx`
- `Data_Layout_CMSE_2025.xlsx`
- `Note_for_data_user - CMS-Education.docx`
- `README_CMSE_2025.docx`
- `Survey methodology and estimation procedure - CMS-Education.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
