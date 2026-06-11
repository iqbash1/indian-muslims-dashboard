# Provenance: Household Consumption Expenditure Survey 2022-23

- **Survey idno:** `DDI-IND-MOSPI-NSSO-HCES22-23`  (NADA catalog id 224)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/224
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: MPCE x religion (proven on 2023-24)

## Unit-level data file (kept LOCAL, not committed)
- `Unit level data of HCES 2022-23 round.zip`  (122,631,251 bytes)
- sha256 `bbf2afd03b782e466a9eb4623e98c41bc25d85a1f5f80d35b0798c1e67dbdcde`
- archived at `~/Desktop/nada-work/hces-2022-23/Unit level data of HCES 2022-23 round.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-HCES22-23 ~/Desktop/nada-work/hces-2022-23
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-HCES22-23.xml`
- `Layout_HCES 2022-23 (1).xlsx`
- `Readme_HCES2022 (1).docx`
- `Rider for users of unit level data of HCES (2).pdf`
- `Survey methodology and estimation procedure (1).pdf`
- `tabulation_state_code (2).xlsx`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
