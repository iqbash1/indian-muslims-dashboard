# Provenance: Land & Livestock Holding + Situation Assessment of Agricultural Households, NSS 77th round, 2019 (Sch 33.1)

- **Survey idno:** `DDI-IND-MOSPI-NSSO-77Rnd-Sch33.1-January2019-December2019`  (NADA catalog id 157)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/157
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: agri-household income + land holding x religion (agricultural households only)

## Unit-level data file (kept LOCAL, not committed)
- `Round77sch331Data.rar`  (22,359,775 bytes)
- sha256 `cf1736241e3f3bb1ed3552b515016ca9081424ecaeedba1114e154846265923c`
- archived at `~/Desktop/nada-work/sas-agri-2019/Round77sch331Data.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-77Rnd-Sch33.1-January2019-December2019 ~/Desktop/nada-work/sas-agri-2019
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-77Rnd-Sch33.1-January2019-December2019.xml`
- `Estimation_procedure_NSS77_DPD.pdf`
- `nic_amendment_2008.pdf`
- `README77331_V1m.pdf`
- `README77331_V2m.pdf`
- `State_77.xlsx`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
