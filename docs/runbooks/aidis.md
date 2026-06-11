# Runbook: AIDIS unit-level microdata (Debt & Investment, NSS 70th round 2013)

## Source identity

- Manifest entry: `aidis-2013` (manifest/sources.yaml)
- Survey: All-India Debt & Investment Survey, NSS 70th round Schedule 18.2,
  Visit 1, fielded January-December 2013; assets/debt as on **30.06.2012**
  (hence year=2012 on canonical rows). 1,10,800 households.
- Catalog: id 130 / idno `DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec20131`.
- Feeds: **`household-net-worth`** and **`institutional-credit-share`** - both
  computed; NSS KI(70/18.2) publishes wealth by state and social group, never
  by religion.

## What we publish from it

Per household, by religion of head (as on 30.06.2012):
- Net worth (assets minus outstanding cash debt): Muslim Rs 9.16 lakh vs Hindu
  Rs 13.69 lakh vs all-India Rs 13.95 lakh. Urban Muslim households hold 51%
  of urban Hindu net worth (Rs 11.5 vs 22.5 lakh); rural 83%.
- Institutional share of outstanding debt: Muslim 68.3% vs Hindu 72.4%
  (urban: 72.7 vs 85.4). Context: Muslims borrow least (IOI 23.8% vs 29.0%).

## How to refresh / recompute

The 41 MB CSV zip is archived locally (`~/Desktop/nada-work/aidis-2013-v1/`)
with SHA256 + re-fetch recipe committed in `sources/nada/aidis-2013-v1/`.

```bash
# L1 -> L2 (validates against published KI(70/18.2) before writing)
.venv/bin/python transform/aidis/extract_wealth_2013_by_religion.py
# L2 -> L3
.venv/bin/python transform/canonicalize/household_net_worth.py
.venv/bin/python transform/canonicalize/institutional_credit_share.py
```

Validation: average debt and incidence of indebtedness reproduce the published
all-India figures EXACTLY (AOD Rs 32,522 rural / 84,625 urban; IOI 31.44 /
22.37); institutional shares exactly (56.0 / 84.5); average assets within
0.75% - the residual is MoSPI's own CSV conversion shipping block 10
(non-farm business equipment) with an empty value column, worth exactly that
block's published 0.25-0.76% share of assets.

Layout map + gotchas (misnamed block files, the agency-code-09 trap, serial
subtotal rows): `nada/aidis-layout-map.md`.

## Caveats (NSO unit-data rider + survey design)

Religion is self-reported and unverified; the survey is stratified for states,
not religions - the split is indicative, no sub-state estimates. Gold and
ornaments sit OUTSIDE the published asset concept (about +4% if included;
household durables were not collected at all). Land (94% of rural assets) is
valued at normative/guideline rates, not market prices, so levels understate
market wealth for everyone; the comparison across communities is the signal.
Institutional-share cells ride on indebted households only (~1,700 rural
Muslim), so sub-cuts are indicative.

## The 2019 round (future trend point)

AIDIS 2018-19 (NSS 77th, catalog id 156) is distributed on NADA ONLY as a
proprietary `.Nesstar` binary (no open parser; banked locally regardless).
Published all-India anchors for whenever it becomes parseable (recorded in
`nada/aidis-layout-map.md`): AVA Rs 15,92,379 rural / 27,17,081 urban; AOD
Rs 59,748 / 1,20,336; IOI 35.0 / 22.4.
