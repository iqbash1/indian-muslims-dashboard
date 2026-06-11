# Provenance: Housing Condition Survey, NSS 65th round, 2008-09

- **Survey idno:** `DDI-IND-MOSPI-NSSO-65Rnd-Sch1dot2-2008-09`  (NADA catalog id 120)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/120
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: housing amenities x religion

## Unit-level data file (kept LOCAL, not committed)
- `Nss65_1.2_new format.rar`  (15,614,568 bytes)
- sha256 `c92c62d92c861c099eabf7cd5f770c26222eb4891f8f9cac759ba22ef8d88f20`
- archived at `~/Desktop/nada-work/housing-2008-09/Nss65_1.2_new format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-65Rnd-Sch1dot2-2008-09 ~/Desktop/nada-work/housing-2008-09
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `Schedule_NSS 65-Sch 1.2.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
