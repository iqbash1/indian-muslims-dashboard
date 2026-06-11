# Provenance: Debt & Investment, NSS 48th round, 1992

- **Survey idno:** `IND-NSSO-DIS-1992-v1`  (NADA catalog id 70)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/70
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE (verify rider): assets/liabilities x religion

## Unit-level data file (kept LOCAL, not committed)
- `CSV_DATA.zip`  (22,271,182 bytes)
- sha256 `f5587e9c8429c71097d1227a880a45f6a3a35d2afd611de37f67e812b86baa4a`
- archived at `~/Desktop/nada-work/aidis-1992/CSV_DATA.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget IND-NSSO-DIS-1992-v1 ~/Desktop/nada-work/aidis-1992
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)


## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
