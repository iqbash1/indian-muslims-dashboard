# Provenance: Debt & Investment, NSS 70th round Visit-2, 2013

- **Survey idno:** `DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec2013V2`  (NADA catalog id 132)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/132
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE (verify rider): assets/liabilities x religion

## Unit-level data file (kept LOCAL, not committed)
- `NSS-70-18pt2-visit2_new_format.rar`  (18,131,531 bytes)
- sha256 `a8c1caf51d9eda29676114709decd1425ab291bfa07f91d49b0db27d4a291c97`
- archived at `~/Desktop/nada-work/aidis-2013-v2/NSS-70-18pt2-visit2_new_format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec2013V2 ~/Desktop/nada-work/aidis-2013-v2
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `data_layout18.2v1.xls`
- `data_layout18.2v2.xls`
- `DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec2013.xml`
- `DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec2013V2.xml`
- `nic_amendment_2008.pdf`
- `schedule_0.0v1.doc`
- `schedule_0.0v2.doc`
- `schedule_18.2_v1.doc`
- `schedule_18.2_v2.doc`
- `State_code.doc`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
