# Provenance: Household Consumer Expenditure, NSS 68th round Type-1, 2011-12

- **Survey idno:** `DDI-IND-MOSPI-NSSO-68Rnd-Sch1.0-July2011-June2012`  (NADA catalog id 1)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/1
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: MPCE x religion

## Unit-level data file (kept LOCAL, not committed)
- `Nss68_1.0_Type1_new format.rar`  (91,308,724 bytes)
- sha256 `8187fe10966cd579394bf40184a109234f55f3d2d7ecfd5261c66bb71272ef34`
- archived at `~/Desktop/nada-work/ces-2011-12-t1/Nss68_1.0_Type1_new format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-68Rnd-Sch1.0-July2011-June2012 ~/Desktop/nada-work/ces-2011-12-t1
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `DDI-IND-MOSPI-NSSO-68Rnd-Sch1.0-July2011-June2012.xml`
- `Estimation Procedure_68.pdf`
- `layout68_1_0_typ1.pdf`
- `nco_2004_CodeStructure.pdf`
- `nic_amendment_2008.pdf`
- `Schedule_68_1.0_type1.pdf`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
