# Modal-view feasibility map (per metric)

Goal: as many modal-tab views per metric as the **source data honestly supports**, each
reproducible by an independent researcher from the cited source table + method.

## How views work
Every tab is auto-generated from a dimension present in `canonical/<id>.csv`:
`By state` ← `geography_level=state` rows; `By sex` ← `sex=male/female` rows;
`By district` ← `geography_level=district`; over-time ← multiple years (rendered as
the card-face trend, not a tab); by-community ← peer-religion rows (on the card face).

**A view is only feasible if the source publishes the _Muslim_ value broken down by that
dimension** (e.g. state x religion, not state-total or national-by-religion).

## Reproducibility standard (applies to every view)
1. Cited source: exact document + table + page, shown in the modal.
2. Stated method: numerator / denominator / filters, shown in the modal.
3. Downloadable data: the view's rows in the published canonical CSV (+ ideally a per-view slice).
4. Open transform: the canonicalise script in the repo (already true).
5. Archived L1: SHA256'd source (already true).
Reproducibility gap (#1/#2 not surfaced per-view) was CLOSED in Commit EH: every view
tab now carries a "Reproduce this view" caption (`_view_provenance`) linking source +
data file + transform code.

---

## Program status (as of 2026-06-09) - the "as many views as possible" sweep is DONE

SHIPPED (Commits EJ-EO):
- **Residence (urban/rural) dimension** added as an auto-rendering tab (`_residence_details`):
  imr, improved-sanitation (EK); lfpr-15plus, wpr-15plus, salaried-share (EJ);
  pop-share, sex-ratio, lit-7plus (EM, Census C-01/C-09/C-15).
- **By state**: prison-rate-per-100k, undertrial-rate-per-100k (EL, NCRB per-state rate =
  NCRB count / Census state population); mpce (EO, new `_state_residence_details` builder,
  per-state Muslim urban/rural from Sachar Appendix 8.2/8.3).
- **mpce "Urban vs rural"** (EO): national Muslim 804/553 vs all 1105/579 from Sachar 8.2/8.3.
- **Over-time**: ger-higher-ed + muslim-higher-ed-enrolment gain a 2020-21 point (EN, AISHE
  Table 15 de-interleaved; fixed 2011 GER denominator).

SKIPPED, with reason (source does not support a worthwhile view):
- **Census by-sex** (urban-share, pop-share): measured DEGENERATE. National-2011 M/F gap is
  <0.6pp for every community (urban-share Muslim 40.1/39.7; pop-share Muslim 14.16/14.29) -
  two near-identical columns, no finding. sex-ratio by-sex is circular; lit-7plus already
  has By sex. Net: no metric gets a by-sex tab beyond lit-7plus.
- **PLFS over-time** (lfpr/wpr/salaried): the 15+ LFPR/WPR-by-religion detail exists ONLY in
  each report's current year (2022-23 Table 32, 2023-24 Table 48); the 2021-22 report
  publishes religion at all-ages only (Statements 37/38). So a *consistent* 15+ trend caps at
  2 points (2022-23 + 2023-24), and the clean 4-year series (2022-23 Statement 20) is
  all-ages, which would corrupt the existing 15+ metric. Thin 2-point value vs high
  multi-layout extraction effort -> not worth it.
- **Census by-age + generic by-district**: needs new `_age_details` builder + an age_group
  schema column (HIGH effort, deferred; not attempted in this sweep).

The tiered roadmap below is the ORIGINAL pre-sweep plan, kept for history; the status block
above supersedes it.

---

## Tiered roadmap (most actionable first)

### Tier 0 - render-only (data already in canonical; pure code fix)
| Metric | View | Why it's free |
|---|---|---|
| **mla-share** | **By state** | 31 state rows already canonical; `_card_timeseries` never passes `details_html` to `_card_shell`, so no tab is emitted. Wire `_state_details` into that one builder. |

### Tier 1 - canonicalise existing L2 (data already extracted; no new source pull)
| Metric | View(s) | Source table | Method |
|---|---|---|---|
| **improved-sanitation** | By residence (urban/rural) | NFHS-5 FR375 Table 2.4 p38 (the one true religion x residence cross) | Muslim-head HH with any toilet, urban vs rural column |
| **imr** | By residence (urban/rural) | NFHS-5 FR375 Table 7.2 pp248-250 | Muslim IMR under urban / rural panels |
| **lfpr-15plus** | By residence (rural/urban) | PLFS 2023-24 Table 48 p397 | LFPR 15+, Muslim x {rural,urban} |
| **wpr-15plus** | By residence (rural/urban) | PLFS 2023-24 Table 48 p397 | WPR 15+, Muslim x {rural,urban} |
| **salaried-share** | By residence (rural/urban) | PLFS 2023-24 Table 49 p401 | regular-wage share, Muslim x {rural,urban} (largest gap: 11.0 rural vs 32.7 urban) |
| **prison-share** | By state (+ per-state trend, 6 yrs) | NCRB PSI Tables 2.10C-2.13C, all years in L2 | Muslim prisoners / religion-reported total, per state |
| **undertrial-share** | By state (+ trend) | NCRB PSI Table 2.11C, all years in L2 | Muslim undertrials / total, per state |
| **urban-share** | By sex; By district (2011); By age (2011) | Census C-01 + C-15 | per existing literacy/pop method, residence=urban / total |
| **sex-ratio** | Urban vs rural; child sex-ratio (by age); By district (2011) | Census C-15 + C-01 state MDDS | females/males x1000 per stratum |
| **lit-7plus** | By sex at state; urban/rural; By age (2011) | Census C-09 | (literate - age-not-stated)/(total - 0-6 - age-not-stated) per stratum |
| **pop-share** | By sex; urban/rural; By age | Census C-01 + C-15 | Muslim share within each stratum (some marginal value) |

Caveats: NCRB by-state has holes (Maharashtra blanks religion for undertrials some years;
2020 state names are Devanagari -> need transliteration). Census by-age is 2011-only (no
2001 C-15); 2001 literacy age bands need re-extraction (source has them, L2 dropped them).

### Tier 2 - new extraction from already-archived sources (real L2->L3 work)
| Metric | View | Source (on disk) | Notes |
|---|---|---|---|
| **muslim-higher-ed-enrolment** | Over-time (2020-21 vs 2021-22), national + state | AISHE 2020-21 Table 15 p136 | cleanest (pure count, no denominator) |
| **ger-higher-ed** | Over-time (2020-21), national + state | AISHE 2020-21 Table 15 p136 + GER 27.3 prose | use same Census-2011 denominator both years |
| **mpce** | By state (urban + rural, separately) | Sachar 2006 Appendix 8.2/8.3 pp364-365 | no combined per-state figure exists |
| **prison-rate-per-100k** | By state | numerator in L2; **denominator** = Census 2011 state x religion population *count* needs extraction | per-state rate is analytically weak (reporting holes) |
| **undertrial-rate-per-100k** | By state | same | Maharashtra undertrial hole bites hardest |
| **lfpr / wpr / salaried** | Over-time (2021-22, 2022-23) | PLFS prior-year reports archived, no L2 yet | read 15+ appendix row, not all-age Statements |

### Tier 3 - NOT feasible (source does not publish the cross)
- **inst-delivery, women-anaemia, stunting-u5**: NFHS publishes religion AND residence/sex/state
  as **separate margins, never crossed** -> no additional Muslim-by-dimension view. (Trend already on card.)
- **imr / all NFHS / all PLFS**: **By state = NOT-IN-SOURCE** (no state x religion table).
- **PLFS**: no district x religion anywhere.
- **ls-share**: religion only as a national per-election journalistic aggregate -> no state/sex view.
- **prison / undertrial**: **By sex = NOT-IN-SOURCE** (PSI never crosses religion x sex).
- **stunting-u5**: NFHS-2/3/4 trend extension is possible (over-time), but that is a card-face series, not a tab.

---

## What this means
- The **single biggest opportunity is the Census family** (urban-share, sex-ratio, lit-7plus,
  pop-share): C-01/C-09/C-15 already in L2 carry religion x state x sex x residence x age, but the
  canonicalisers filter to `residence=total`, `sex=persons`, national-only. Unlocking them is
  canonicalise-only (Tier 1), and yields the most new views.
- **NFHS health metrics are mostly capped** - the honest answer is they cannot get by-state/by-sex
  views (the source doesn't cross religion with them); only sanitation + imr get a urban/rural tab.
- **mla-share By-state** is a true 1-fix quick win.
- The reproducibility standard is a separate, universal rendering change (surface source+method+data
  per view) that should land first so every new view meets it.
