# Runbook: NSS Household Social Consumption Health - 75th round (2017-18) + 80th round (2025)

## Source identity

- Manifest entries: `nss75-health` + `health-2025` (manifest/sources.yaml)
- Surveys: Household Social Consumption: Health, Schedule 25.0. NSS 75th
  round July 2017 - June 2018 (1,13,823 households, 93,925 hospitalisation
  cases; published as NSS Report 586) and NSS 80th round January - December
  2025 (1,39,732 households, 1,21,584 cases; published as the PIB press
  note of April 2026). The 2025 release states estimating households'
  out-of-pocket medical expenses as the survey's primary design objective.
- Feeds: **`hospital-oop-spend`** - average out-of-pocket medical
  expenditure (OOPME) per hospitalisation case excluding childbirth, by
  religion of household head (both publications stop at hospital type,
  quintile and state, never religion).

## The two distribution channels

The NADA catalog ships the 75th round ONLY as a proprietary `.Nesstar`
binary (id 152; banked in `sources/nada/health-2017-18/`); the parseable
official channel is MoSPI's original fixed-width TXT distribution, still
served from the unlinked Drupal-era directory
`mospi.gov.in/sites/default/files/NSS75250H/` (13 files
`R75250L01..L13.TXT` + `KI_Health_75th_Final.pdf`, the validation-anchor
report). URLs + sha256: `sources/nss75-health/PROVENANCE-note.md`; the
~180 MB stays local at `~/Desktop/nada-work/health-2017-18-alt/`.

The 80th round is a normal NADA API pull (id 290, CSV distribution with
headers, 7 level files; `sources/nada/health-2025/`; ~148 MB local at
`~/Desktop/nada-work/health-2025/`). The PIB press note carrying the
published OOPME anchors is banked alongside.

## How to recompute

```bash
# L1 -> L2 (gates: 2017 aborts unless all 9 cells of Report 586 Statement
# 3.15 reproduce within 0.5% AND Statement 3.19 reimbursement shares within
# 0.2pp; 2025 aborts unless all 6 press-note OOPME cells reproduce within
# 0.5%. Observed worst gap in both: 0.01%.)
.venv/bin/python transform/health/extract_health_2017_by_religion.py
.venv/bin/python transform/health/extract_health_2025_by_religion.py
# L2 -> L3
.venv/bin/python transform/canonicalize/hospital_oop_spend.py
```

Weights: 2017-18 = MLT/100 if NSS=NSC else MLT/200 (sub-sample-combined);
2025 = mult/100 flat. Byte/column map and gotchas:
`nada/health-layout-map.md`.

## What we publish (all-India, by religion of head, Rs nominal per case)

| religion | 2017-18 | 2025 |
|---|---|---|
| Muslim | 14,827 | 30,104 |
| Hindu | 18,398 | 34,323 |
| all-India | 18,088 | 34,064 |

A Muslim hospital stay costs 12-19% less than the all-India average across
the two rounds, for two reasons: more Muslim patients use government
hospitals (41.5% of Muslim hospitalisation cases in 2025 against 36.4% of
Hindu cases; 47.6% vs 41.8% in 2017-18), where a stay averages about an
eighth of a private one, and Muslim households have less to spend on
private care. The survey cannot tell cheaper care apart from care that was
needed but never bought; the metric carries neutral polarity (neither
direction is "better").

## Caveats (NSO unit-data rider)

Religion is self-reported and unverified; the survey is stratified for
states, not religions - the split is indicative, no sub-state estimates.
Values are nominal rupees of each round (no deflation); health insurance
coverage roughly tripled between rounds, so netted reimbursement matters
more in 2025. Childbirth (ailment codes 87/88/89) is excluded per the
published construct. Morbidity rates (PPRA) are perception-driven and
roughly doubled between rounds - that caution applies to ailment RATES,
not to expenditure per case; the press note itself compares the rounds'
insurance coverage directly, and the expenditure construct is identical,
so the trend carries no break flag. Comparable health rounds 2014 (71st)
and 2004 (60th) are banked locally but Nesstar-locked (the Windows-VM
unlock set).
