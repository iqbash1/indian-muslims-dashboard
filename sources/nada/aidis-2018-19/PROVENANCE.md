# Provenance: All-India Debt & Investment Survey, NSS 77th round 2018-19 (Sch 18.2)

- **Survey idno:** `DDI-IND-MOSPI-NSSO-77Rnd-Sch18.2-January2019-December2019`  (NADA catalog id 156)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/156
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE (verify rider): assets/liabilities x religion

## Unit-level data file (kept LOCAL, not committed)
- `Round77sch18pt2Data.rar`  (21,187,001 bytes)
- sha256 `68408203ee14d0fc058c5343bd57bad26dec42d7472ec90dfbbc052f5822574e`
- archived at `~/Desktop/nada-work/aidis-2018-19/Round77sch18pt2Data.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-77Rnd-Sch18.2-January2019-December2019 ~/Desktop/nada-work/aidis-2018-19
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-77Rnd-Sch18.2-January2019-December2019.xml`
- `Estimation_procedure_NSS77_DPD.pdf`
- `nic_amendment_2008.pdf`
- `State_77.xlsx`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
