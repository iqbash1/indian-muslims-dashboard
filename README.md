# Indian Muslims — Living Conditions Dashboard

A long-horizon, source-traceable dashboard of living-conditions indicators for India's Muslim population, with Hindu and all-India comparison baselines on every metric.

Modeled on the **hawaiidashboard.org** pattern: a scannable card grid, single authoritative source per metric, stated refresh cadence, comparison baselines on every card. Like Hawaii's rank-among-50-states, each metric benchmarks the Muslim outcome **among all religious communities** and — where the source has multiple survey rounds — **over time**. The gap between Muslim outcomes and Hindu / national baselines is the story this dashboard is built around — inheriting the Sachar Committee (2006) methodology of focused, comparative measurement.

## The scorecard (current)

21 carded metrics on the dashboard (plus 2 reference rate-per-100k series kept in canonical/ but not rendered). Each renders as a card that ranks the Muslim outcome among religious communities; where a source has multiple rounds the card also draws a trend line — NFHS health 1998→2020 (4 rounds), Census sex-ratio 1961→2011 (6 rounds, RGI primary for 1971/1991/2001/2011 + Sachar secondary for 1961/1981), Census literacy 2001→2011 (2 rounds), population share 1961→2011 (decadal), Lok Sabha 1952→2024 (18 elections), NCRB prison + undertrial share 2018→2023 (6 years), and communal incidents 2015→2023 (9 years). **Live at https://iqbash1.github.io/indian-muslims-dashboard/**.

| Cluster | Metric | Year | Muslim | Hindu | All | Gap vs reference |
|---|---|---|---|---|---|---|
| Demographics | Population share | 2011 | 14.23% | 79.80% | — | baseline |
| Demographics | Urban share | 2011 | 39.91% | 29.20% | 31.14% | +10.71pp (more urban) |
| Demographics | Sex ratio (F/1000M) | 2011 | 951 | 939 | 943 | +12 *(paradox)* |
| Demographics | Top-100 district concentration | 2011 | 58.55% | — | — | — |
| Education | Literacy rate (7+) | 2011 | 68.59% | 73.31% | 73.02% | **−4.72pp** |
| Education | GER higher education | 2021 | 9.83% | — | 31.09% | **−21.26pp** |
| Education | Higher-ed enrolment (count) | 2021 | 2,108,033 | — | — | n/a (no Hindu count in source) |
| Employment | LFPR (15+) | 2023 | 55.00% | 60.90% | 60.10% | **−5.90pp** |
| Employment | WPR (15+) | 2023 | 53.20% | 59.10% | 58.20% | **−5.90pp** |
| Employment | Salaried share | 2023 | 18.00% | 21.90% | 21.70% | **−3.90pp** |
| Health | Infant Mortality Rate | 2020 | 33.0 | 35.4 | 34.7 | −2.4 *(paradox)* |
| Health | Stunting U5 | 2020 | 36.8% | 35.5% | 35.47% | +1.3pp |
| Health | Institutional delivery rate | 2020 | 84.30% | 89.50% | 88.58% | **−5.20pp** |
| Health | Anaemia in women (15-49) | 2020 | 55.60% | 57.40% | 57.00% | −1.8pp *(paradox)* |
| Housing | Toilet facility access | 2020 | 90.30% | 80.70% | 82.50% | +9.60pp *(composition effect)* |
| Representation | Lok Sabha Muslim share | 2024 | **4.42%** | — | — | **−9.81pp vs 14.23% pop** |
| Representation | State MLA Muslim share (agg) | 2024 | **~6%** | — | — | **−8.2pp vs 14.23% pop** |
| Justice | Prison-share Muslim | 2023 | 19.08% | 71.85% | — | **+4.85pp over 14.2% pop** |
| Justice | Undertrial-share Muslim | 2023 | 20.05% | 70.87% | — | **+5.82pp over 14.2% pop** |
| Civic | Communal incidents (NCRB) | 2023 | — | — | 272 nationally | civic-society counts higher |
| Civic | Hate-speech events (IHL) | 2024 | — | — | 1,165 | civic-tech count, contested |

*"Paradox" marks indicators where Muslim outcomes run ahead of Hindu — primarily infant survival, women's anaemia, sex ratio, and (with composition caveat) toilet access. These are well-documented in Indian demography and are not a contradiction of the broader pattern: socioeconomic and civic indicators (literacy, employment, representation, justice exposure) consistently show Muslim disadvantage. The starkest gaps are political representation (~8-10pp under) and prison overrepresentation (Muslims ~14% of population vs 19-20% of prisoners and undertrials).*

## See the dashboard

Open `docs/index.html` in any browser. No server required, no build step, all charts via Chart.js CDN.

```bash
python dashboard/build.py
open docs/index.html
```

If publishing to GitHub Pages, point Pages at `/docs/` on `main`. A `.nojekyll` file is included so the static HTML is served as-is.

## Architecture

Four-layer data flow. Every dashboard number traces L4 → L3 → L2 → L1 source file with SHA256 sidecar.

| Layer | Path | Mutability | What it is |
|---|---|---|---|
| L1 Raw archive | `sources/` | Immutable | Every external file ever pulled, with SHA256 + pull metadata |
| L2 Structured extraction | `extracted/` | Regenerable | Long-format CSVs parsed from L1 |
| L3 Canonical metric series | `canonical/` | Regenerable | One CSV per metric — the dashboard's data contract |
| L4 Dashboard cache | `docs/` | Regenerable | Static HTML built from L3 |

The dashboard never queries an external source live and never reads L1/L2 directly. Methodology breaks (e.g., NFHS-5 → NFHS-6 definitional changes) are recorded as `break_flag` on canonical rows.

## Sources

16 source-ids feed L3 canonical metrics (23 source-ids registered in `manifest/sources.yaml` total — the remaining 7 are either retired-but-archived for cross-validation reference (`sachar-committee-2006`, `census-decadal-religion`) or pre-registered for future metrics (`hces-2022-23`, `mha-parliament-answers`, `niti-mpi`, `rbi-minority-lending`, `rti-public-sector-employment`)).

| Source | What it gives us | Cadence | Status |
|---|---|---|---|
| **Census of India 2011** | Population by religion (state + district), literacy, sex ratio | 10-year (2021 round delayed indefinitely) | 5 files archived; UP + Bihar + Bengal + J&K + Uttarakhand district MDDS imported |
| **Census of India 2001** | Population, literacy, sex ratio by religion (national + states) — gives the 2001→2011 decennial trend for literacy + the 2-point urban-share trend | 10-year (prior round) | 2 files archived (C-1, C-9) |
| **Census of India 1991** *(new in AG)* | C-9 Religion table by residence × sex — feeds sex-ratio 1991 (all 6 religions, primary) | 10-year | XLSX + companion PDF archived; India figure excludes J&K |
| **Census of India 1971** *(new in AG)* | Paper 2 of 1972 Religion summary — feeds sex-ratio 1971 (all 6 religions, primary) | 10-year | PDF archived; extractor cross-checks derived sex-ratio against printed values |
| **Census decadal religion** *(secondary)* | Population share by community 1961-1991 → the pop-share 1961→2011 decadal trend | 10-year | manual-entry secondary (2001/2011 from primary C-1; flagged on card; see runbook) |
| **Sachar Committee 2006** *(new in AG)* | Appendix Table 3.8 — sex-ratio Muslim + All-India 1961 + 1981 (fallback only — RGI religion volumes for those years not on NADA) | one-off (2006) | Full report PDF archived; cross-validated against primary at 1971/1991/2001 |
| **NFHS-2 / 3 / 4 / 5 (1998-99 → 2019-21)** | IMR, institutional delivery, women's anaemia — by religion, 4 rounds (time series); stunting + sanitation single-round | ~5-year (NFHS-6 in field) | all 4 round reports archived; 5 metrics extracted |
| **PLFS 2023-24** | LFPR, WPR, salaried-share by religion | Annual | 2 reports archived; 3 metrics extracted |
| **AISHE 2021-22** | Higher-education enrolment by religion | Annual | 2 reports archived; 2 metrics extracted (count + GER cross-source) |
| **HCES 2022-23** | Consumption expenditure (MPCE) — by religion needs unit-level | ~5-year | 3 reports archived; metric blocked on unit-level processing (documented in runbook) |
| **NCRB PSI 2018-2023** | Prison + undertrial population by religion — multi-year share trend | Annual (~2y lag) | 6 years archived; 2 share metrics + 2 rate-per-100k reference series |
| **NCRB CII 2015-2023** | Communal incidents by state | Annual (~2y lag) | per-table + main reports archived; 9-year national series |
| **PRS / ECI affidavits** *(secondary)* | Lok Sabha + state MLA Muslim shares — manual-entry from journalistic compilations | Per-election | 18-point LS series 1952→2024; 30 state/UT assemblies covered |
| **India Hate Lab + civic incident DBs** *(secondary, contested)* | Civic-society counts of communal incidents | Annual | 2024 IHL count loaded |

Each source has a runbook in `docs/runbooks/` documenting URL discovery, archived file inventory, where religion crosstabs live, and known data gaps.

## What this is honest about

- **2021 Census not released.** The latest census point is 2011; population share and district concentration remain 2011-only. Cards show the data year inline.
- **Sex-ratio decadal 1961-1981 uses Sachar Committee 2006 (secondary) for Muslim + All only.** The underlying RGI religion volumes for 1961 + 1981 aren't on NADA; the 1971 + 1991 + 2001 + 2011 rounds use RGI primary publications with all six religions. Cross-validated at the overlap years.
- **Maharashtra didn't report religion for ~33k undertrials in PSI 2022.** Prison-share is computed over religion-reported subset only; documented on every tile.
- **HCES doesn't publish religion crosstabs.** Religion is a survey variable but not tabulated in the published Report 591. MPCE-by-religion requires unit-level processing from microdata.gov.in.
- **NFHS-5 vs NFHS-4 anaemia methodology break** (capillary vs venous blood). Not comparable across rounds.
- **AISHE classifies "Muslim Minority" separately from "Other Minority"** (Christians, Sikhs, Buddhists, Jains, Parsis); Hindu enrolment is implied as residual, not directly enumerated.
- **Wayback fails on files > ~5 MB** (Cloudflare 520/523 on the origin side). The local SHA256-sidecared L1 archive is the authoritative copy; Wayback is supplementary insurance only for smaller files. **However:** the Wayback `id_` raw-bytes endpoint (`https://web.archive.org/web/<ts>id_/<url>`) works with the ingest UA where the rendered `/web/` view is bot-blocked — used to recover NCRB 2018/2019 prison reports after site reorg.

## Layout

```
sources/      L1 raw archive (Git-LFS tracked)
extracted/    L2 structured tables (regenerated by transform/)
canonical/    L3 canonical series — the dashboard data contract
manifest/     sources.yaml + metrics.yaml + JSON Schemas
ingest/       Manifest-driven pull script
transform/    L1→L2 extractors and L2→L3 canonicalizers
validate/     Schema validation for manifests and canonical CSVs
dashboard/    L4 builder (build.py); outputs to docs/
docs/         Published site: index.html (dashboard), canonical/ (CSV copies),
              runbooks/ (per-source methodology), metrics/, audit-log.md
```

## Quick start

```bash
git clone <repo-url>
cd Indian-Muslims
git lfs pull                      # fetches L1 binaries (~140 MB)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python ingest/pull.py --list
.venv/bin/python validate/validate.py
.venv/bin/python dashboard/build.py
open docs/index.html
```

## Adding a new metric

1. Add an entry to `manifest/metrics.yaml` (set `status: stub`).
2. If the source isn't already registered, add to `manifest/sources.yaml` and write a runbook in `docs/runbooks/`.
3. Discover and verify the source URL (HEAD-check); set `status: verified` on the target.
4. Pull: `python ingest/pull.py --source <id>`.
5. Write an extractor in `transform/<source>/extract_*.py` (study the existing ones for the source's table shape — spreadsheet, dual-column PDF, single-column religion section, landscape-rotated PDF via qpdf, etc.).
6. Write a canonicalizer in `transform/canonicalize/<metric>.py`.
7. Run validate.py, run dashboard/build.py.
8. Spot-check against a published figure if available.

## Adding a new state's district depth (pop-share)

Pure mechanical extension — pattern is proven:

1. Find the state's C-1 catalog page at `censusindia.gov.in/nada/index.php/catalog/<id>`.
2. Add the state's MDDS target to `manifest/sources.yaml` under `census-india-2011`.
3. Pull, then run `python transform/census-india-2011/extract_c01.py <source.xls> <output.csv> --district-only`.
4. Recanonicalize: `python transform/canonicalize/pop_share.py` (it globs all `c01-population-by-religion*.csv` automatically).

## Status

23 canonical metrics (21 carded + 2 reference series kept in `canonical/` but not rendered after Commit V switched justice cards to the share-trend pattern). The dashboard is a card grid with multi-community benchmarking (rank among religious communities) and multi-round trends spanning up to 60+ years (sex-ratio 1961→2011; population share 1961→2011; Lok Sabha 1952→2024; communal incidents 2015→2023; prison/undertrial 2018→2023; NFHS health 1998→2020; Census literacy 2001→2011). The architecture is battle-tested across 5 source shapes: legacy .xls / modern .xlsx spreadsheets, dual-column PDF tables, single-column PDF religion sections, tabular state-row PDFs, and landscape-rotated PDFs (qpdf-pre-rotated at extraction time).

See `docs/audit-log.md` for the planned annual audit ritual and `docs/refresh-schedule.md` for the per-source cadence.

## License and citation

Data sources are publicly published government documents; their licenses apply (Census of India, NCRB, NSO/MoSPI, IIPS-NFHS, AISHE/MoE, Sachar Committee Report). This project's code and canonical CSVs are free to use, fork, and extend. If you cite this dashboard in research or reporting, please name it as the source and link back to the canonical CSV.
