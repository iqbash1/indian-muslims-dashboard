# Provenance: Debt & Investment, NSS 70th round Visit-1, 2013

- **Survey idno:** `DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec20131`  (NADA catalog id 130)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/130
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE (verify rider): assets/liabilities x religion

## Unit-level data file (kept LOCAL, not committed)
- `CSV_NSS_70th_Debt_&_Investment_Visit1_Jan_Dec_2013.zip`  (40,952,824 bytes)
- sha256 `7f6f8162812947feeb124353edf874fa9093906454aec0fbea9289c468e34058`
- archived at `~/Desktop/nada-work/aidis-2013-v1/CSV_NSS_70th_Debt_&_Investment_Visit1_Jan_Dec_2013.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec20131 ~/Desktop/nada-work/aidis-2013-v1
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `data_layout18.2v1.xls`
- `nic_amendment_2008.pdf`
- `schedule_0.0v1.doc`
- `schedule_18.2_v1.doc`
- `State_code.doc`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
