# Provenance: Employment & Unemployment, NSS 61st round, Jul2004-Jun2005

- **Survey idno:** `DDI-IND-MOSPI-NSSO-61-12-2011`  (NADA catalog id 109)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/109
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion (pre-PLFS, same indicators)

## Unit-level data file (kept LOCAL, not committed)
- `Emp_Unemp_2004_2005_CSV.zip`  (77,866,780 bytes)
- sha256 `6925e9d805966fda3eb0eb061cd766a7b88a4ef379c44e0ff003bae1920b8665`
- archived at `~/Desktop/nada-work/eus-2004-05/Emp_Unemp_2004_2005_CSV.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-61-12-2011 ~/Desktop/nada-work/eus-2004-05
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `District_code_list_nss61_round.xls`
- `Estimation_Procedure_61.doc`
- `IHSN_REPORT_NSSO_61_SCH_10_EMPLOYMENT_AND_UNEMPLOYMENT_LUD_19_January_2012.pdf`
- `nsso_61_round_sch_10_emp_unemp_instruction_to_field_staff.doc`
- `Schedule_61_10.doc`
- `State_Codes_61.doc`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
