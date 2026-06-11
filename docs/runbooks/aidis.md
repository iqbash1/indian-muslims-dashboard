# Runbook: AIDIS unit-level microdata (Debt & Investment, NSS 70th 2013 + 77th 2019)

## Source identity

- Manifest entries: `aidis-2013` and `aidis-2019` (manifest/sources.yaml)
- Survey: All-India Debt & Investment Survey, Schedule 18.2, Visit 1, two
  rounds: NSS 70th fielded January-December 2013 (stocks as on **30.06.2012**,
  so year=2012; 1,10,800 households) and NSS 77th fielded January-December
  2019 (stocks as on **30.06.2018**, so year=2018; 1,16,461 households).
- Channels differ by round: 2013 = NADA API CSV zip (catalog id 130, idno
  `DDI-IND-MOSPI-NSSO-70Rnd-Sch18pt2-Jan-Dec20131`); 2019 = MoSPI's original
  fixed-width TXT distribution surviving in the unlinked directory
  `mospi.gov.in/sites/default/files/NSS7718/` (the NADA copy, catalog id 156,
  is a proprietary .Nesstar binary - the same two-channel story as
  nss76-housing, and found the same way: the Wayback snapshot of the deleted
  Drupal release page, in this case its mospi.NIC.in twin).
- Feeds: **`household-net-worth`** and **`institutional-credit-share`**, both
  now 2-round trends - computed; the published reports stop at state and
  social group, never religion. Since Commit FE the credit share is rendered
  as the net-worth card's "Borrowing sources" tab (one wealth card, two tabs).

## What we publish from it

Per household, by religion of head:
- Net worth (assets minus outstanding cash debt), nominal Rs per round:
  Muslim Rs 9.16 lakh (2012) -> 15.0 lakh (2018) vs Hindu Rs 13.69 -> 18.8
  lakh. The gap NARROWED: urban Muslim households moved from 51% to 67% of
  urban Hindu net worth; rural from 83% to 87%.
- Institutional share of outstanding debt: Muslim 68.3% -> 68.7% (stood
  still) vs Hindu 72.4% -> 77.1% (formalised); the urban gap widened from 13
  to 17 points (71.3 vs 88.4 in 2018). Context: Muslims borrow least (IOI
  26.8% vs Hindu 31.4% in 2018).

## How to refresh / recompute

2013: the 41 MB CSV zip is archived locally (`~/Desktop/nada-work/aidis-2013-v1/`)
with SHA256 + re-fetch recipe committed in `sources/nada/aidis-2013-v1/`.
2019: the ~450 MB of TXT (visits 1 and 2) is archived locally
(`~/Desktop/nada-work/aidis-2018-19-alt/`) with SHA256s + URLs committed in
`sources/nss77-aidis/` (READMEs, layout xls, tabulation plan and press note
committed there too).

```bash
# L1 -> L2 (each validates against its round's published figures before writing)
.venv/bin/python transform/aidis/extract_wealth_2013_by_religion.py
.venv/bin/python transform/aidis/extract_wealth_2018_by_religion.py
# L2 -> L3 (each merges both rounds into one canonical CSV)
.venv/bin/python transform/canonicalize/household_net_worth.py
.venv/bin/python transform/canonicalize/institutional_credit_share.py
```

Validation, 2013 round (vs NSS KI(70/18.2)): AOD and IOI reproduce EXACTLY
(Rs 32,522 rural / 84,625 urban; 31.44 / 22.37); institutional shares exactly
(56.0 / 84.5); AVA within 0.75% - the residual is MoSPI's own CSV conversion
shipping block 10 (non-farm equipment) with an empty value column.

Validation, 2019 round (vs MoSPI press note 24.08.2021): sample counts,
AVA (Rs 15,92,379 rural / 27,17,081 urban), AOD (Rs 59,748 / 1,20,336) and
the physical/financial asset split ALL reproduce EXACTLY to the rupee; IOI
(35.0 / 22.4) and institutional shares (66 / 87) at printed precision. The
TXT distribution has no block-10-style defect.

Layout maps + gotchas (misnamed 2013 block files, the credit-agency-09 trap
in BOTH rounds, the 2019 DDI's wrong agency labels, subtotal serials, the
2019 block renumbering): `nada/aidis-layout-map.md`.

## Caveats (NSO unit-data rider + survey design)

Religion is self-reported and unverified; the survey is stratified for
states, not religions - the split is indicative, no sub-state estimates.
Gold and ornaments sit OUTSIDE the published asset concept in both rounds
(roughly +3-4% if included; 2019 collects them as an explicit no-probe memo
item, srl 20 of block 11a, alongside srl 21 paintings; household durables
are not collected at all). Land (the bulk of rural assets) is valued at
normative/guideline rates, not market prices, so levels understate market
wealth for everyone; the comparison across communities and across rounds is
the signal. Values are NOMINAL per round - the 2012->2018 rise overstates
real growth (no deflation applied; the card is about the gap, not the
level). Institutional-share cells ride on indebted households only (~2,000
indebted rural Muslim households in 2018), so sub-cuts are indicative.
