# Provenance: Debt & Investment, NSS 59th round, 2003

- **Survey idno:** `DDI-IND-MOSPI-NSSO-59Rnd-Sch18pt2-Jan-Dec2003`  (NADA catalog id 103)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/103
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE (verify rider): assets/liabilities x religion

## Unit-level data file (kept LOCAL, not committed)
- `Nss59_18.2_new format.rar`  (133,350,130 bytes)
- sha256 `826a389679211a1b58a0e5f14d3cd20064ed41093158e047b510944c144e0cc1`
- archived at `~/Desktop/nada-work/aidis-2003/Nss59_18.2_new format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-59Rnd-Sch18pt2-Jan-Dec2003 ~/Desktop/nada-work/aidis-2003
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-59Rnd-Sch18pt2-Jan-Dec2003.xml`
- `Estimation Procedure_59.pdf`
- `Schedule 18.2  Debt and Investment.pdf`
- `Schedule_V1_18.pdf`
- `Schedule_V2_18.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
