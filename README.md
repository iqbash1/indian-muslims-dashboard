# muslimdata.in

A long-horizon, source-traceable dashboard of living-conditions indicators
for India's Muslim population, with Hindu and all-India comparison baselines
on every metric.

**Live at https://muslimdata.in/.**

Modelled loosely on the **hawaiidashboard.org** pattern: a scannable card
grid, single authoritative source per metric, stated refresh cadence,
comparison baselines on every applicable card. Each metric ranks the Muslim
outcome among religious communities and, where the source has multiple
survey rounds, plots how it has changed over time. The methodology follows
the Sachar Committee (2006) approach to focused, comparative measurement,
covering population, education, employment, health, representation, and
justice.

## What's on the dashboard

21 live indicators across six themes, drawn from 16 primary sources. The
authoritative scorecard is the live site at https://muslimdata.in/ — it
auto-rebuilds on every push and shows current values, the comparison
pill, the trend chart, the methodology, and a downloadable CSV per metric.

Coverage at a glance:
- **Demographics**: population share by religion 1961→2011, urban share,
  sex ratio (6 rounds 1961→2011), top-100-district concentration.
- **Education**: literacy 2001→2011, higher-education enrolment ratio
  (2021), Muslim higher-ed enrolment count.
- **Employment**: labour-force participation, worker-population ratio,
  regular-salaried share (PLFS 2023-24).
- **Health**: infant mortality, under-5 stunting, institutional delivery,
  women's anaemia (4 rounds 1998→2020 from NFHS-2/3/4/5).
- **Housing**: improved sanitation access.
- **Representation**: Lok Sabha Muslim share 1952→2024 (18 elections),
  state MLA Muslim share aggregated across all 30 state and UT assemblies.
- **Justice**: prison rate per 100k, undertrial rate per 100k, communal
  incidents recorded by police (NCRB 2015→2023), anti-Muslim hate-speech
  events (India Hate Lab 2023+2024).

## See the dashboard

Open `docs/index.html` in any browser. No server required, no build step,
all charts via Chart.js CDN.

```bash
.venv/bin/python dashboard/build.py
open docs/index.html
```

## Deploy

The site auto-deploys to muslimdata.in on every push to `main`. Cloudflare
Workers (Static Assets) runs `npx wrangler deploy` against the connected
GitHub repo and serves `docs/` directly; build config lives in
`wrangler.jsonc`, security headers + CORS in `docs/_headers`. End-to-end
setup is documented in `docs/runbooks/deploy-setup.md`.

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
