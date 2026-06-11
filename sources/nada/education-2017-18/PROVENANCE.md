# Provenance: Household Social Consumption: Education, NSS 75th round 2017-18 (Sch 25.2)

- **Survey idno:** `DDI-IND-MOSPI-NSSO-75Rnd-Sch25.2-July2017-June2018`  (NADA catalog id 151)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/151
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE for education spending x religion; literacy/GER = off-limits

## Unit-level data file (kept LOCAL, not committed)
- `Round75sch252Data.rar`  (14,775,021 bytes)
- sha256 `ec6f551c1020ee7f5ba9ccdbf01758e1d1ee0cbf4af558120949a9e155d690f1`
- archived at `~/Desktop/nada-work/education-2017-18/Round75sch252Data.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-75Rnd-Sch25.2-July2017-June2018 ~/Desktop/nada-work/education-2017-18
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `datalay75_252.xls`
- `DDI-IND-MOSPI-NSSO-75Rnd-Sch25.2-July2017-June2018.xml`
- `Estimation_Procedure_NSS.pdf`
- `nic_amendment_2008.pdf`
- `README75.pdf`
- `Sch_25.2.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
