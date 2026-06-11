# Provenance: Morbidity & Health Care, NSS 60th round, Jan-Jun 2004

- **Survey idno:** `IND-NSSO-SMHC-2004-v1.0`  (NADA catalog id 107)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/107
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE for OOP health spending x religion; morbidity rate = avoid

## Unit-level data file (kept LOCAL, not committed)
- `Data_CSV.zip`  (18,814,173 bytes)
- sha256 `0ea82b28d1293acce74736dd892cd8972d2cb369b4d1079166076e6e3596c1cc`
- archived at `~/Desktop/nada-work/morbidity-2004/Data_CSV.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget IND-NSSO-SMHC-2004-v1.0 ~/Desktop/nada-work/morbidity-2004
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `IHSN Study Report-NSS60R-Schedule 25.0-Morbidity-Healthcare.pdf`
- `Schedule_60_25.0.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
