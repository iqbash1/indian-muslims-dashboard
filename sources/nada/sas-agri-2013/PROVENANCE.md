# Provenance: Situation Assessment of Agricultural Households, NSS 70th round, 2013

- **Survey idno:** `DDI-IND-MOSPI-NSSO-70Rnd-Sch33-visit2-Jan-Dec2013`  (NADA catalog id 134)
- **Catalog page:** https://microdata.gov.in/NADA/index.php/catalog/134
- **Pulled:** 2026-06-11 via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** SAFE: agri-household income x religion (agricultural households only)

## Unit-level data file (kept LOCAL, not committed)
- `Nss70_33_visit1_new format.rar`  (20,534,498 bytes)
- sha256 `6ee8733c36b90fa85ac68c24e47ee7720ee4d42ae60d254d1703eaf346bec6a6`
- archived at `~/Desktop/nada-work/sas-agri-2013/Nss70_33_visit1_new format.rar`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget DDI-IND-MOSPI-NSSO-70Rnd-Sch33-visit2-Jan-Dec2013 ~/Desktop/nada-work/sas-agri-2013
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
- `nic_amendment_2008.pdf`
- `schedule_0.0v1.doc`
- `schedule_0.0v2.doc`
- `schedule_33_v1.doc`
- `schedule_33_v2.doc`
- `State_code.doc`

## Permitted use
NSO unit-level Rider: religion is self-reported and unverified; State/UT is the finest stratum (NO district/sub-state estimates); a target-indicator x religion cross-tab is the intended use, demographic indicators (population share, sex ratio, literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.
