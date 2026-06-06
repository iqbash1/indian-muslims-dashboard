# Audit log

Annual ritual: sample 10 randomly chosen dashboard metrics and trace L4 → L3 → L2 → L1 source file. Drift between layers is a bug.

## Procedure

1. Pick 10 metrics at random from `manifest/metrics.yaml` (status: live or data-loaded).
2. For each:
   - Pull a single (geography, year, religion) row from the L4 dashboard cache.
   - Confirm the value matches `canonical/<metric>.csv` for the same key.
   - Open the L2 extraction file referenced in `source_document`.
   - Open the L1 raw file and locate the cell/page that produced the L2 value.
   - Verify the L1 file's SHA256 matches the `.meta.json` sidecar.
3. Record the sample and result below.
4. Any miss = open an issue and halt new metric onboarding until resolved.

## Annual audits

### 2026-06-05 — Full deep fact-check (all displayed values)

Scope: instead of the 10-metric random sample, every displayed value was
checked — all 21 card heroes, the headline-finding numbers, and the
district-concentration figures — across four layers: (1) arithmetic
re-derivation, (2) L4 dashboard vs L3 canonical, (3) L3 vs L2 extraction,
(4) L2/L3 vs the L1 primary source document, plus external cross-checks.

**Result: no incorrect values found.** Every value traces correctly to its
primary source. Issues are limited to caveats already disclosed on the site.

Cross-cutting:
- Arithmetic re-derivation: 21/21 exact (weighted averages, rate-per-100k,
  district sum/share/top-10, ratios, deltas, comparison medians).
- L4 vs L3: 21/21 heroes match.
- L3 vs L2: exact on every table-sourced metric.

Confirmed against the L1 source document (quoted figures):
- pop-share 14.2%, urban 39.9%/31.1% — Census c01 XLS (Muslim 172,245,158 /
  1,210,854,977; Muslim urban 68,740,419).
- sex-ratio 951 / all 943 — Census c15 XLS (Muslim 83,971,213 F / 88,273,945 M).
- district concentration 58.5% — all 640 districts present across 35 states;
  top-100 = 100,853,681; #1 Murshidabad 4,707,573; districts sum to exactly
  the national Muslim total.
- anaemia 55.6% (all 57.0%) — NFHS-5 p468; institutional delivery 84.3% —
  p324; toilet 90.3% — p74; IMR urban 27.8/rural 36.5 — p284.
- stunting 36.8% — NFHS-5 Table 10.1 p424 (180-degree-rotated); weights to the
  published national 35.5%.
- incarceration 63.3 / undertrial 48.8 — NCRB PSI-2022 Muslim totals 108,968 /
  83,968 over Census 2011 population.
- communal incidents 272 (2023) — NCRB CII-2023 p35 ("23.1 Communal/Religious
  378 0.0 272 0.0 272 0.0"; 2022 and 2023 are genuinely both 272 in the source).
- anti-Muslim hate speech 1,165 (2024) — India Hate Lab report p4 ("668 in
  2023 to 1,165 in 2024").
- Muslim higher-ed enrolment 2,108,033 — AISHE All-India row; externally
  confirmed (4.87% of 43,268,181).
- LFPR 55.0 / WPR 53.2 / salaried 18.0 — PLFS 2023-24 Table 48/49 (L2 vs L3
  exact; national LFPR 60.1% matches published).

Externally confirmed:
- Lok Sabha 24 of 543 = 4.42% (FACTLY; 18th Lok Sabha).
- Literacy national 73.0% / Muslim 68.5% (published Census 2011).

Two values that looked wrong but were verified faithful:
- Communal incidents 2022 = 2023 = 272 (identical) — confirmed: NCRB itself
  reports 272 for both years.
- AISHE state-row sum (~1.77 M) not equal to shown 2,108,033 — the shown value
  is the published All-India total (correct); the auditor's first sum had
  double-counted the All-India row.

Caveats (all disclosed on the relevant tiles):
- Higher-ed GER (9.8%) is a computed proxy using a Census-2011 denominator; it
  runs a few points above the officially published GERs (national 27-28%;
  published Muslim Minority GER ~9%). The Muslim-vs-national gap is the robust
  story; the absolute is a computation.
- MLA share (6%) is a manual journalistic aggregate, inherently approximate.
- IMR by religion is reconstructed from NFHS-5 urban/rural splits (no
  published total-residence-by-religion column).
- Prison/undertrial: Maharashtra under-reported religion for ~33k undertrials
  in 2022 (numerator excludes them).
- NCRB communal counts are deflated post-2017 (states stopped recording the
  sub-category).

Not fully re-derived from L1 (noted for next audit):
- Literacy (c09): confirmed vs published national 73.0% and arithmetic, but the
  full education-level recomputation from the raw XLSX was not run.
- PLFS and stunting raw cells sit in 180-degree-rotated tables; confirmed via
  L3 vs L2 (exact) + external anchors rather than pixel-level PDF
  reconstruction. Every portrait NFHS table read directly matched exactly.

Fix applied this audit: corrected a stale provenance note for `ger-higher-ed`
(canonicalizer + manifest) that described the Muslim enrolment as a "sum of
state-level rows" — it is actually the published All-India "Muslim Minority"
total (the code already used the All-India row; only the note wording was
wrong). Also corrected the manifest's "~12% published Muslim GER" to ~9% per
this check.

### 2027 (planned)

_Resume the 10-metric random-sample ritual, or repeat the full sweep._
