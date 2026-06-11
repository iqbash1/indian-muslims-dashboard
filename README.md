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

21 live indicators across six themes (population, health, education,
employment, representation, justice), drawn from 22 primary sources,
grouped into five themed sections on the dashboard. Companion measures
that share a card's source and story render as modal tabs of that card
rather than as cards of their own, keeping the homepage scannable. The authoritative
scorecard
is the live site at https://muslimdata.in/ — it
ships on every push and shows current values, the comparison
pill, the trend chart, the methodology, and a downloadable CSV per metric.
Where the underlying data supports it, opening a card reveals **modal tabs**
for the **by-state**, **by-sex** (male vs female), and **by-district**
breakdowns; each tab has its own shareable URL and social-preview image, and
every metric also has a full landing page at `/m/{id}/` (data tables, sources,
JSON-LD) with a district-level CSV download where available.

Coverage at a glance:
- **Demographics**: population share by religion 1961→2011 (with the
  top-100-district geographic-concentration view in its "By district" tab),
  urban share, sex ratio (6 rounds 1961→2011).
- **Education**: literacy 2001→2011, higher-education enrolment ratio
  (2 AISHE rounds, with Muslim student counts beside the rate in its tabs).
- **Employment**: labour-force participation (with the worker-population
  ratio in its "Working vs looking" tab), unemployment rate, regular-salaried
  share (with salaried pay in its "What it pays" tab), all spanning two
  decades: 3 quinquennial EUS rounds 2004→2012 plus 7 PLFS rounds 2017→2024,
  with the design break flagged at 2017.
- **Income & wealth**: monthly spending per person (Sachar 2004-05 → HCES
  2023-24, with the top-spending-fifth distribution as a tab), household net
  worth (AIDIS 2013, with borrowing sources as a tab).
- **Health**: infant mortality, under-5 stunting, institutional delivery,
  women's anaemia (4 rounds 1998→2020 from NFHS-2/3/4/5).
- **Housing**: toilet access (NFHS-5), clean drinking water at home and
  pucca housing (NSS 76th 2018, with household electricity as a tab).
- **Representation**: Lok Sabha Muslim share 1952→2024 (18 elections) and
  Muslim share of state assemblies (all 31 state and UT assemblies, with a
  per-assembly table tab). Separate cards: the two gaps are distinct stories.
- **Justice**: prison rate per 100k (with the undertrial rate in its
  "Undertrials" tab), communal incidents recorded by police (NCRB 2015→2023
  national, plus a per-state breakdown for 2023). (An India Hate Lab
  anti-Muslim hate-speech metric was retired from display in Commit CR; its
  data is archived for reference.)

## See the dashboard

Open `docs/index.html` in any browser to view the dashboard (charts use a
self-hosted, SRI-pinned Chart.js, no CDN). The per-metric landing pages and
per-tab share URLs use real paths, so they resolve when `docs/` is served over
HTTP rather than opened from the filesystem.

```bash
.venv/bin/python dashboard/build.py
open docs/index.html                      # quick view
python3 -m http.server --directory docs   # full routing (landing pages, share URLs)
```

## Deploy

The site auto-deploys to muslimdata.in on every push to `main`: a GitHub
Actions workflow (`.github/workflows/deploy.yml`) runs `wrangler deploy` to
ship the **committed** `docs/` to Cloudflare Workers (Static Assets). CI does
no rebuild, so `docs/` is built locally and committed. (Cloudflare's own
git auto-build is deliberately disabled: it smudged the Git-LFS `sources/`
archive and blew the LFS bandwidth quota.) Two more workflows run on push:
`validate.yml` (schema + doc/data-consistency + source-refresh gates) and
`smoke.yml` (Playwright browser smoke tests of the rendered site). Build config
lives in `wrangler.jsonc`, security headers + CORS in `docs/_headers`;
end-to-end setup is documented in `docs/runbooks/deploy-setup.md`.

## Architecture

Four-layer data flow. Every dashboard number traces L4 → L3 → L2 → L1 source file with SHA256 sidecar.

| Layer | Path | Mutability | What it is |
|---|---|---|---|
| L1 Raw archive | `sources/` | Immutable | Every external file ever pulled, with SHA256 + pull metadata |
| L2 Structured extraction | `extracted/` | Regenerable | Long-format CSVs parsed from L1 |
| L3 Canonical metric series | `canonical/` | Regenerable | One CSV per metric (rows keyed by geography × year × religion, with an optional `sex` dimension) — the dashboard's data contract |
| L4 Dashboard cache | `docs/` | Regenerable | Static HTML built from L3 |

The dashboard never queries an external source live and never reads L1/L2 directly. Methodology breaks (e.g., NFHS-5 → NFHS-6 definitional changes) are recorded as `break_flag` on canonical rows.

## Sources

22 source-ids feed L3 canonical metrics (29 source-ids registered in `manifest/sources.yaml` total — the remaining 7 are `census-decadal-religion` (superseded by the primary RGI volumes, kept for cross-validation), `civic-incident-databases` (the hate-speech metric was decarded in Commit CR; data archived), and five pre-registered for future metrics: `hces-2022-23`, `mha-parliament-answers`, `niti-mpi`, `rbi-minority-lending`, `rti-public-sector-employment`). `plfs-microdata` (7 PLFS rounds via the NADA API) joined in Commit EW, feeding the employment metrics' 2017-2022 trend rows; `aidis-2019` (the NSS 77th TXT mirror) joined in Commit FM, giving the wealth cards their 2012 -> 2018 trend; `eus-microdata` (the three quinquennial EUS rounds) joined in Commit FN, stretching the employment trends back to 2004.

| Source | What it gives us | Cadence | Status |
|---|---|---|---|
| **Census of India 2011** | Population by religion (state + district), literacy, sex ratio | 10-year (2021 round delayed indefinitely) | 38 files archived (3 core C-series tables + all 35 state/UT district MDDS); district-level pop-share complete for all states |
| **Census of India 2001** | Population, literacy, sex ratio by religion (national + states) — gives the 2001→2011 decennial trend for literacy + the 2-point urban-share trend | 10-year (prior round) | 2 files archived (C-1, C-9) |
| **Census of India 1961 / 1971 / 1981 / 1991** | RGI primary religion volumes (1961 C-VII, 1971 Paper 2 of 1972, 1981 Paper 3 of 1984 HH-15, 1991 C-9) — feed pop-share and sex-ratio 1961-1991 (all six religions, primary) | 10-year | PDFs/XLSX archived; 1981 excludes Assam and 1991 excludes J&K (Census not held there); extractors cross-check derived sex-ratios against Sachar AT 3.8 |
| **Census decadal religion** *(superseded)* | Former manual-entry source for pop-share 1961-1991 | 10-year | superseded by the RGI primary volumes above; kept registered for cross-validation |
| **Sachar Committee 2006** | MPCE (monthly spending per person) by religion, NSS 61st round 2004-05 — feeds the `mpce` metric | one-off (2006) | Full report PDF archived; also a sex-ratio cross-validation reference (AT 3.8) |
| **NFHS-2 / 3 / 4 / 5 (1998-99 → 2019-21)** | IMR, institutional delivery, women's anaemia — by religion, 4 rounds (time series); stunting + sanitation single-round | ~5-year (NFHS-6 in field) | all 4 round reports archived; 5 metrics extracted |
| **PLFS 2023-24** | LFPR, WPR, salaried-share by religion | Annual | 2 reports archived; 3 metrics extracted |
| **AISHE 2021-22** | Higher-education enrolment by religion | Annual | 2 reports archived; 2 metrics extracted (count + GER cross-source) |
| **HCES 2022-23** | Consumption expenditure (MPCE) — by religion needs unit-level | ~5-year | 3 reports archived; metric blocked on unit-level processing (documented in runbook) |
| **NCRB PSI 2018-2023** | Prison + undertrial population by religion — multi-year share trend | Annual (~2y lag) | 6 years archived; rate-per-100k incarceration card (undertrial rate as its tab) + 2 share trend reference series |
| **NCRB CII 2015-2023** | Communal incidents by state | Annual (~2y lag) | per-table + main reports archived; 9-year national series |
| **PRS / ECI affidavits** *(secondary)* | Lok Sabha + state MLA Muslim shares — manual-entry from journalistic compilations | Per-election | 18-point LS series 1952→2024; 31 state/UT assemblies covered |
| **India Hate Lab + civic incident DBs** *(secondary, contested)* | Civic-society counts of communal incidents | Annual | decarded in Commit CR (contested); data archived, not currently rendered |

Each source has a runbook in `docs/runbooks/` documenting URL discovery, archived file inventory, where religion crosstabs live, and known data gaps.

## What this is honest about

- **2021 Census not released.** The latest census point is 2011; population share and district concentration remain 2011-only. Cards show the data year inline.
- **Sex-ratio and population-share decadal series (1961-2011) are now all primary RGI census.** Earlier builds used Sachar Committee 2006 (sex-ratio 1961/1981) and a manual decadal compilation (pop-share 1961-1991) as fallbacks; the original RGI religion volumes were since located on NADA and now feed both directly, with all six religions. 1981 excludes Assam and 1991 excludes Jammu & Kashmir (Census not held there those rounds).
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
tests/        Playwright browser smoke tests (smoke.py)
docs/         Published site: index.html (dashboard), about/, m/{id}/ (per-metric
              landing pages + per-tab share stubs), og/ (social-card images),
              canonical/ (CSV copies), runbooks/ (per-source methodology), audit-log.md
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

31 canonical metrics (21 carded + 10 companion/reference series kept in `canonical/`, most still rendered through a host card's tabs: `prison-share` + `undertrial-share` superseded by the rate-per-100k metrics, `district-concentration-top100` folded into the "By district" tab of the `pop-share` card (Commit DV), `muslim-higher-ed-enrolment` folded into the "By state" and "By sex" tabs of `ger-higher-ed` as a Students column beside the GER rate (Commit EQ), `wpr-15plus` folded into the "Working vs looking" tab of `lfpr-15plus` beside the labour-force rate (Commit ET), and the Commit FE homepage-simplification folds: `top-quintile-share` into `mpce` ("Top spending fifth"), `salaried-earnings` into `salaried-share` ("What it pays"), `institutional-credit-share` into `household-net-worth` ("Borrowing sources"), `household-electricity` into `pucca-house` ("Electricity"), `undertrial-rate-per-100k` into `prison-rate-per-100k` ("Undertrials"); old `/m/{id}/` URLs 301 to the host card via `docs/_redirects`. The FE `mla-share` fold into `ls-share` was reverted in Commit FJ: the Lok Sabha and state-assembly gaps are distinct stories, so each is carded.) The dashboard is a card grid with multi-community benchmarking (rank among religious communities) and multi-round trends spanning up to 60+ years (sex-ratio 1961→2011; population share 1961→2011; Lok Sabha 1952→2024; PLFS employment 2017→2024 from unit-level microdata, incl. the `unemployment-rate-15plus` card that exists only because the microdata carries religion every round; communal incidents 2015→2023; prison/undertrial 2018→2023; NFHS health 1998→2020; Census literacy 2001→2011). The architecture is battle-tested across 5 source shapes: legacy .xls / modern .xlsx spreadsheets, dual-column PDF tables, single-column PDF religion sections, tabular state-row PDFs, and landscape-rotated PDFs (qpdf-pre-rotated at extraction time).

Per-metric depth where the source supports it, shown as **modal tabs** (each with its own shareable `/m/{id}/{view}/` URL + social-preview image) and mirrored on the metric's full `/m/{id}/` landing page: **by-state** tables where the source goes sub-national (population share, sex ratio, literacy, urban share, spending, incarceration, communal incidents, higher-ed); a **by-sex** (male vs female) breakdown where the source has one (labour force, salaried work, literacy, higher-ed), national-level via an optional `sex` dimension added to the canonical schema and defaulted to `all` at the `load_metric` read so existing series are unaffected; **folded companion tabs** (the Commit FE list above) carrying an absorbed card's chart and table; a **by-district** geographic-concentration view (the top-100-district ranking + cumulative-concentration curve, in pop-share's "By district" tab); and a **district-level CSV** download (pop-share, all 640 districts with names).

See `docs/audit-log.md` for the planned annual audit ritual and `docs/refresh-schedule.md` for the per-source cadence.

## License and citation

Data sources are publicly published government documents; their licenses apply (Census of India, NCRB, NSO/MoSPI, IIPS-NFHS, AISHE/MoE, Sachar Committee Report). This project's code and canonical CSVs are free to use, fork, and extend. If you cite this dashboard in research or reporting, please name it as the source and link back to the canonical CSV.
