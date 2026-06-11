# Runbook: PLFS unit-level microdata (7 rounds, 2017-18 to 2023-24)

## Source identity

- Manifest entry: `plfs-microdata` (manifest/sources.yaml)
- Survey: Periodic Labour Force Survey, NSO / MoSPI. Seven consistent July-June
  rounds: 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24
  (NADA catalog ids 204, 216, 217, 206, 214, 210, 213).
- Feeds: the **over-time (2017-2022) rows** of `lfpr-15plus`, `wpr-15plus` and
  `salaried-share`. The 2023-24 point stays sourced from the published annual
  report tables (`plfs` source) - the microdata reproduces them within 0.2pp,
  so the two sources extend one seamless series.

## Why microdata

The annual-report PDFs publish the 15+ by-religion detail only for their own
year, so a trend was impossible from the PDFs (the old VIEW-FEASIBILITY skip).
The microdata carries household religion in EVERY round.

## What we publish from it

15+ usual-status (ps+ss) LFPR / WPR / regular-wage-salaried share by religion
(muslim, hindu, christian, sikh, all) x sex x residence, national, per round.
Headline finding: Muslim LFPR rose 45.0 (2017-18) to 55.0 (2023-24), but the
salaried share of Muslim workers fell from its 22.2% peak (2018-19) to 18.0%.

## How to refresh

The zips (13-22 MB each) are archived locally at `~/Desktop/nada-work/plfs-<round>/`
with SHA256 + provenance committed in `sources/nada/plfs-<round>/`. Re-fetch any
round with the recipe in its `PROVENANCE.md`:

```bash
NADA_API_KEY=<key> .venv/bin/python nada/bank.py autoget <idno> ~/Desktop/nada-work/plfs-<round>
```

## How to recompute

```bash
# L1 -> L2: all 7 rounds, with two validation gates (published all-India figures
# per round to +-0.1; the 2023-24 by-religion PDF tables to +-0.2)
.venv/bin/python transform/plfs/extract_microdata_trends.py
# L2 -> L3: regenerate the three canonical CSVs (2023 from the PDF L2 + trend from microdata)
.venv/bin/python transform/canonicalize/lfpr_15plus.py
.venv/bin/python transform/canonicalize/wpr_15plus.py
.venv/bin/python transform/canonicalize/salaried_share.py
```

Method (per round): first-visit person file, age 15+; employed = principal OR
subsidiary status in {11,12,21,31,41,51}; unemployed = principal status 81;
salaried = classifying status (ps if ps-employed, else ss) = 31; weight =
MULT/100 (MULT/200 when NSS != NSC) divided by NO_QTR; household religion joined
on (quarter, FSU, b1q13, b1q14, b1q15). Column names differ per round - the
verified per-round map incl. gotchas (era rename at 2020-21, the 2018-19 header
mislabel, 2020-21 temporary visitors) is `nada/plfs-layout-map.md`.

## Caveats (NSO unit-data rider)

Religion is self-reported and unverified; PLFS is designed to estimate
labour-force indicators with State/UT as the basic stratum. Employment rates
cross-classified BY religion are the intended use (NSO prints exactly these in
the annual reports); demographic indicators from these fields are not, and no
sub-state estimates are made. Year=Y in canonical rows is the start of the
Jul-Y to Jun-(Y+1) reference period.
