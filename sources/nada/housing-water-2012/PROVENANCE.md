# Provenance: Drinking Water, Sanitation, Hygiene & Housing, NSS 69th round, 2012

- **Survey idno:** `DDI-IND-MOSPI-NSSO-69Rnd-Sch1dot2-2012`  (NADA catalog id 129)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/129
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: housing/water/sanitation amenities x religion

## Unit-level data file (kept LOCAL, not committed)
- `Nss69_1.2_new format.rar`  (14,863,700 bytes)
- sha256 `4acc4c72384bed9b75ee81d01f89a44c9ffd66e2cc91e7c24d00ccf8f180975b`
- archived at `~/Desktop/nada-work/housing-water-2012/Nss69_1.2_new format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-69Rnd-Sch1dot2-2012 ~/Desktop/nada-work/housing-water-2012
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-69Rnd-Sch1dot2-2012.xml`
- `Estimation Procedure_69.pdf`
- `IND-NSSO-DWSHHC-2012-v1.xml`
- `Schedule_69_1.pdf`
- `State_69.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
