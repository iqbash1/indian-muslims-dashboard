# Provenance: Employment & Unemployment, NSS 66th round, 2009-10

- **Survey idno:** `DDI-IND-MOSPI-NSSO-66-10-2011`  (NADA catalog id 124)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/124
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: employment x religion

## Unit-level data file (kept LOCAL, not committed)
- `Emp_Unemp_2009_2010_CSV.zip`  (31,522,338 bytes)
- sha256 `51d6778588f925bba8f4a4c10db27cd8c5c229146fe04d55abaee095e49970ef`
- archived at `~/Desktop/nada-work/eus-2009-10/Emp_Unemp_2009_2010_CSV.zip`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-66-10-2011 ~/Desktop/nada-work/eus-2009-10
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-66-10-2011.xml`
- `District_code_66.xls`
- `Estimation Procedure_sch_10_employment_unemployment_nsso_66_round_July2009_June2010.doc`
- `Estimation_Procedure_sch_10_employment_unemployment_nsso_66_round_July2009_June2010.doc`
- `IHSN_REPORT_NSSO_66_SCH_10_EMPLOYMENT_AND_UNEMPLOYMENT_LUD_18March2013.pdf`
- `nco_2004_CodeStructure.pdf`
- `No_FSUs_allotted_surveyed_no_persons_enumerated_nsso_66_sch_10.csv`
- `Schedule_66_10.doc`
- `State_code_66.doc`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
