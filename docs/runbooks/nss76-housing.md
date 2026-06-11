# Runbook: NSS 76th round Sch 1.2 - housing & basic services (2018)

## Source identity

- Manifest entry: `nss76-housing` (manifest/sources.yaml)
- Survey: Drinking Water, Sanitation, Hygiene and Housing Condition, NSS 76th
  round Schedule 1.2, July-December 2018; 1,06,838 households (63,736 rural +
  43,102 urban). Published as NSS Report 584.
- Feeds: **`improved-water-premises`**, **`household-electricity`**,
  **`pucca-house`** - the housing & basic-services cards, computed by religion
  of household head (Report 584 stops at state and social group).

## The two distribution channels (why this source is special)

The current NADA catalog (id 153) ships this survey ONLY as a proprietary
`.Nesstar` binary (no open parser; that rar is banked as the catalog-channel
L1 in sources/nada/housing-water-2018/). The ORIGINAL fixed-width TXT
distribution survives in an unlinked directory on mospi.gov.in
(`sites/default/files/NSS7612dws/`, located via the Wayback snapshot of the
deleted Drupal page): 9 files `R76120L01.TXT`..`L09`, record length 139,
served with their 2019 Last-Modified stamps. All 9 reproduce the README's
record counts exactly (13,21,283 records). URLs + sha256 of every file:
`sources/nss76/PROVENANCE-note.md`; the 187 MB stays local at
`~/Desktop/nada-work/housing-water-2018-alt/`.

## How to recompute

```bash
# L1 -> L2 (validation gate: 24 published Report-584 cells, aborts above 1pp;
# actual worst gap 0.24pp, 18 cells exact)
.venv/bin/python transform/nss76/extract_housing_2018_by_religion.py
# L2 -> L3 (writes all three canonical CSVs)
.venv/bin/python transform/canonicalize/nss76_housing.py
```

Weight = MLT/100 (final multiplier, no NSS/NSC halving - confirmed by the
README and by the exact published matches). Byte map, codes and gotchas:
`nada/nss76-layout-map.md`.

## What we publish (all-India, by religion of head, 2018)

| indicator | Muslim | Hindu | all |
|---|---|---|---|
| improved water within premises | 69.3 | 62.5 | 63.6 |
| electricity | 96.6 | 95.4 | 95.7 |
| pucca structure | 83.6 | 83.3 | 83.3 |

The pattern INVERTS the consumption/labour gaps: Muslim households sit at or
above Hindu households on basic amenities, driven by rural advantage (and the
community's higher urban share); urban Muslims trail urban Hindus on piped
water into dwelling (36.5 vs 41.4, in the L2). The L2 also carries the
latrine indicators (access 86.9 Muslim vs 78.1 Hindu) - NOT carded, because
the NFHS-5 toilet-access card already covers sanitation and Report 584 itself
cautions about respondent bias on latrine reporting (scheme-benefit questions
preceded it in the questionnaire).

## Caveats (NSO unit-data rider)

Religion is self-reported and unverified; the survey is stratified for
states, not religions - the split is indicative, no sub-state estimates.
Prior comparable rounds (69th 2012, 65th 2008-09) are banked locally for a
possible future trend; their formats are the older "new format" rars.
