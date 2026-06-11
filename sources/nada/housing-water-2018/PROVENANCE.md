# Provenance: Drinking Water, Sanitation, Hygiene & Housing, NSS 76th round, 2018

- **Survey idno:** `DDI-IND-MOSPI-NSSO-76Rnd-Sch1.2-July2018-December2018`  (NADA catalog id 153)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/153
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: housing/water/sanitation amenities x religion

## Unit-level data file (kept LOCAL, not committed)
- `Round76sch1dot2Data.rar`  (10,182,474 bytes)
- sha256 `3fff25cf97a0f748654e1eaa30b248e8d6458407a142db8ea0b1aac5c120a636`
- archived at `~/Desktop/nada-work/housing-water-2018/Round76sch1dot2Data.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-76Rnd-Sch1.2-July2018-December2018 ~/Desktop/nada-work/housing-water-2018
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Data_Layout_NSS76_120.xlsx`
- `DDI-IND-MOSPI-NSSO-76Rnd-Sch1.2-July2018-December2018.xml`
- `Estimation procedure _NSS 76_15052019.pdf`
- `NSS_76_sch_1.2.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
