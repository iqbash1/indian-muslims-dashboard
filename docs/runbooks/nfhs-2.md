# Runbook: National Family Health Survey 2 (1998-99)

## Source identity

- Manifest entry: `nfhs-2`
- Publisher: IIPS / MoHFW; national report hosted by the DHS Program.
- Role: earliest NFHS round used here — extends the health time series back to
  1998-99 (imr, inst-delivery, women-anemia → 4 rounds: 1998/2005/2015/2020).

## Target

| target_id | url | archived | sha256 (first 12) |
|---|---|---|---|
| india-report-frind2 | https://www.dhsprogram.com/pubs/pdf/FRIND2/FRIND2.pdf | sources/nfhs-2/reports/india-report-frind2.pdf | 08c7b5cb1776 |

539-page text PDF (pdfplumber-readable). Wayback save failed (non-blocking).

## Religion tables (verified via pdfplumber)

Religion categories in NFHS-2: Hindu, Muslim, Christian, Sikh, Jain,
Buddhist/Neo-Buddhist, Other, No religion. We extract the 5 named communities
ranked elsewhere (hindu/muslim/christian/sikh/buddhist).

| metric | table | page | how to read |
|---|---|---|---|
| IMR | 6.4 "Infant and child mortality by background characteristics" | **217** (TOTAL panel; p216 is URBAN) | religion row = NN PNN **Infant** Child U5; IMR = 3rd value. Rates for the **10-year period preceding** the survey. |
| institutional delivery | 8.8 "Place of delivery" | **323** | no headline "% in health facility" column; institution = **Public + NGO/trust + Private** (first 3 cols). Births in the **3 years preceding**. |
| women's anaemia | 7.6 "Anaemia among women" | **278** | columns are **any-anaemia | mild | moderate | severe | number** — any-anaemia is **col 0** (NFHS-3/4 put it at col 3). **EVER-MARRIED women only.** |

Extractors: `transform/nfhs/extract_{imr,delivery,anaemia}_trend.py` — NFHS-2 added
as a round with `table`/`page` and per-round handling (`mode="sum3"` for delivery,
`any_index=0` for anaemia). Re-derived values match the printed tables exactly:
IMR Muslim 58.8 / Hindu 77.1; delivery Muslim 31.5 / Hindu 32.9; anaemia
Muslim 49.6 / Hindu 52.4.

## Caveats (carried on canonical rows)

- **Anaemia universe break:** NFHS-2 surveyed only ever-married women; later
  rounds cover all women 15-49. On top of the existing measurement-method break
  → `break_flag=true` (Muslim trend line dashed).
- **Period differences:** IMR is 10-yr-preceding (vs later rounds' panels);
  delivery is 3-yr-preceding (vs 5-yr). Differentials + decline are robust; noted
  in each canonical `methodology_note`.
- NFHS-1 (1992-93) has thinner/!inconsistent religion tabulation — not pulled.
