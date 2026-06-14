# muslimdata.in — working notes for Claude

Static, source-traceable dashboard of living-conditions indicators for India's
Muslims (Hindu + all-India baselines). Live at https://muslimdata.in/. The full
running state lives in auto-memory ([[dashboard-build-state]]); this file is the
always-in-context short version of the must-knows.

## Build & deploy
- Build the site: `.venv/bin/python dashboard/build.py` (writes `docs/`)
- Validate: `.venv/bin/python validate/validate.py` (expect `0 errors`). CI also
  runs `audit_consistency.py`, `audit_accuracy.py` (value ranges, provenance
  SHA256 vs archive, and the extraction_run stamp-shape check that catches
  column transposition - the GF audit found 32 such rows), `check_refresh.py`,
  and Playwright browser smoke tests (`tests/smoke.py` via
  `.github/workflows/smoke.yml`; run locally after
  `python -m playwright install chromium`).
- Deploy = push to `main`. GitHub Actions (`.github/workflows/deploy.yml`) ships
  the **committed** `docs/` to Cloudflare. So: build `docs/` LOCALLY, commit it,
  then push. CI does NO rebuild.
- A pure refactor must leave `docs/index.html` BYTE-IDENTICAL after a rebuild —
  use that as the no-op check.
- Just commit verified work without asking. **Pushing is the live deploy —
  confirm before pushing.**

## Architecture (4 layers, regenerable downward)
`sources/` (L1, immutable, Git-LFS) → `extracted/` (L2) → `canonical/*.csv`
(L3, the data contract) → `docs/` (L4 = build.py output). Edit the manifests,
not ad-hoc scripts: metric metadata in `manifest/metrics.yaml`, sources in
`manifest/sources.yaml`. Never query a source live; never invent numbers or URLs.

## Never break these
- **Colour contract:** maroon `#7b1d22` = the Muslim data series + card hero
  value ONLY; slate-blue `#2c5f8a` = all UI chrome; green/red = polarity. Never
  use maroon for chrome.
- **No em dashes or en dashes** in user-visible text — commas/colons/hyphens only.
- **Indian English** (anaemia, labour). Charts never force a zero baseline.
- **Indian money (Commit FC):** currency is `INR`, never `Rs`; one lakh and up
  display as `INR 9.2 lakh` / `INR 1.4 crore` (`_inr_str` in build.py + JS
  `_inNum`); below that, Indian digit grouping (`3,26,819`, `_in_group`).
  Chart tooltips/bar labels flow through JS `_fmtVal` (UNIT_JS's "INR" is a
  format token, not a literal suffix), so a value reads identically on the
  hero, the pills, the axis and the tooltip (FR).
- **Minimal card faces (FC):** the plain-English definition paragraph is hidden
  on the grid (`.cards .card-plain{display:none}`) and shows only as the modal
  lead; faces are label + hero + chart + pills. Cards stretch to equal height.
  Hero captions ADD to the title (denominator, age band, plain gloss), never
  restate it (FG; convention on the CAPTION dict in build.py). Pills carry ONE
  headline number (FS): label names the comparator, value line = the gap, the
  comparator's own figure rides the small verdict line ("behind · 91.7%").
  In the modal, Definition stays visible and the long methodology + sources
  collapse behind "Full methodology & sources" (a details WITHOUT
  data-view-id, so audit Check C ignores it; landing pages stay fully
  expanded). Page chrome is exactly: section jump-chips (sticky on mobile)
  + a back-to-top button - don't add more.
- **Time series from 2 rounds up (FD):** the card-face chart plots over time
  whenever canonical has 2+ years (break_flag renders the line dashed);
  single-round cards show the community snapshot. Jargon stays out of
  `definition` blocks (methodology_notes carry the survey mechanics).
- **Chart & table grammar (FH/FI/FO/FP):** by-state tables with magnitude
  bars use `.state-bar-table` (label column hugs the names, the bar carries
  its value at its end) and default to polarity-aware worst-first sort;
  trend charts measure their end-label padding (never truncate) and label
  every line including the dashed all-India reference. Y gridlines are
  WHOLE round numbers, EVENLY spaced (`_axisBounds`: smallest 1/2/5-pattern
  step needing <=7 ticks; bounds rounded OUTWARD to the nearest step
  multiple, so at most one step of expansion per side and the floor is
  always labelled), formatted by `_fmtTick` (Indian money, locale-pinned).
  The axis still hugs the data: sex-ratio lives in its 800-1050 band; a 0
  floor appears only when the data sits within one step of it (mpce's
  635-of-4958 floor IS an honest labelled 0) - never as a forced anchor.
  History: FI banned Chart.js's wild tick-bound blowout (9-31 data on a
  0-40 axis); FO pinned edge ticks at raw data extremes, which fixed the
  unlabelled-floor-reads-as-zero problem but produced ragged uneven labels
  (12.8|20|23.8); FP is the synthesis - user's call: "ticks need to be nice
  whole numbers and evenly separated". Don't reintroduce fixed paddings,
  anonymous reference lines, raw-data-value edge ticks, or unlabelled axis
  edges.
- **Representation reads in people, against population (FW/FX/FY):**
  ls-share displays ABSOLUTE MPs (hero "24 of 543", parity pill converts
  14.2% pop share to 77 seats; counts parse from the canonical denominator
  N-of-M records via `_ls_seats`, the share stays in `value`). mla-share
  pairs two bars per state (`hbarPair` + the table's `.tbar-duo`): maroon
  seat share over GREY population share (Census 2011; grey is sanctioned
  for the context series - don't "fix" it to maroon, and don't reintroduce
  the FW floating tick marks FX replaced). Telangana's 2011 share is a
  SYNTHESIZED canonical pop-share row (GB: ten undivided-AP districts
  aggregated in pop_share.py - keep it through any census refresh). The
  duo bar is FIXED-width (a %-width duo overflows the table = phantom
  horizontal scroll), and scroll-contained tall charts carry
  `.chartwrap-scrolled` so the modal's 440px chart override skips them
  (GA: they keep their per-row height and scroll - don't squash). User
  copy stays in plain words (FY): no compressed analytic phrasing
  ("reads against presence"); the INR-100-vs-71 ratio device beats
  percentages in definitions.
- Every value traces to a primary source with a SHA256-archived L1 file.
- **Per-metric views are MODAL TABS** (by state/sex/district), each with its own
  shareable `/m/{id}/{view}/` URL + OG image and a share popover; the card face
  shows only the main chart + a "More views" hint. Don't move drill-downs back
  onto the card face, and respect `prefers-reduced-motion`. Overview shares
  copy `/m/{id}/?open=1` and the landing bounces those visitors into the
  modal (GD, user call: share recipients expect the app; the landing's
  tables duplicate the modal tabs) - the bare `/m/{id}/` stays the static,
  indexable landing, so don't strip the param or auto-redirect the landing.
- **Every modal tab has a unique share link with OG, both directions** (user
  rule, Commit FF): tab ↔ `/m/{id}/{view}/` stub ↔ `/og/{id}-{view}.png` must
  stay bijective; no tab without a stub+OG, no stub/OG outliving its tab.
  `audit_consistency.py` Check C enforces this in CI (it would have caught EW
  silently dropping lfpr's "Working vs looking" tab while its stub kept
  shipping).

## Editing gotchas
- Card prose lives in **3 places** — keep in sync: `manifest/metrics.yaml`
  (`definition` + `methodology_notes`), the `PLAIN_DEFINITION` dict in
  `dashboard/build.py`, and hand-written `docs/runbooks/*.md`. A wording/count
  fix must hit all three.
- In metrics.yaml, `religions` / `comparison_baselines` / `break_notes` /
  `cross_check` are declarative metadata — NOT rendered. Only `definition` +
  `methodology_notes` show (in the modal). EXCEPTION (Commit GL):
  `sources.secondary` (a list of source-ids) IS rendered — appended as extra
  "Reproduce this view" source links after the primary, for the Census
  denominator/weight in the cross-source metrics `imr`, `ger-higher-ed`,
  `prison-rate-per-100k`, `undertrial-rate-per-100k` (moved there from
  `cross_check`; the stub `pucca-housing` keeps its unrendered `cross_check`).
- `docs/m/<id>/` is a FULL indexable landing page (hero, data tables, sources,
  JSON-LD); the per-view `docs/m/<id>/<view>/` are thin redirect stubs (OG meta +
  a relative `/#<id>/<view>` redirect). Both regenerate from canonical, so they
  change on most rebuilds — partial-looking diffs there are expected.
- 23 carded metrics. `pop-share` absorbed the old `district-concentration-top100`
  card (Commit DV): it is now pop-share's "By district" tab (curve + top-100
  table), reading the still-present `district-concentration-top100.csv`. Likewise
  `muslim-higher-ed-enrolment` (student counts) is decarded and folded into
  `ger-higher-ed`'s "By state" + "By sex" tabs, shown as a Students column beside
  the GER rate (Commit EQ merged the old separate rate/count tabs). Likewise
  `wpr-15plus` (worker population ratio) is decarded and folded into
  `lfpr-15plus`'s "Working vs looking" tab, beside the labour-force rate (the two
  PLFS measures differ only by unemployment).
- **Commit FE folded six more companions into host-card tabs** (rule: same
  primary source + same story; the folded tab leads the host's tab order):
  `top-quintile-share` → `mpce` ("Top spending fifth"), `salaried-earnings` →
  `salaried-share` ("What it pays"), `institutional-credit-share` →
  `household-net-worth` ("Borrowing sources"), `household-electricity` →
  `pucca-house` ("Electricity"), `undertrial-rate-per-100k` →
  `prison-rate-per-100k` ("Undertrials"). Decarded ids keep their canonical
  CSVs (the tabs read them; machinery: `FOLDED_VIEW_METRIC` + `_folded_view`
  in build.py, wired into `_og_view_data` + `_landing_breakdowns`); old
  `/m/<id>/` URLs 301 via `docs/_redirects`. The sixth FE fold (`mla-share` →
  `ls-share`) was REVERTED in Commit FJ at the user's call: Lok Sabha and
  state assemblies stay separate cards (the two gaps are distinct stories);
  the per-assembly table is mla-share's own "By assembly" tab.
- The employment cards are two-decade trends: 3 quinquennial EUS rounds
  (2004/2009/2011, Commit FN; the 64th round is excluded - no published
  by-religion anchors) + 7 PLFS rounds (2017-18 to 2023-24, Commit EW), with
  break_flag=true on the 2017 rows (EUS->PLFS design break, dashes the
  line). Recipes: docs/runbooks/plfs-microdata.md + nada/plfs-layout-map.md
  + nada/eus-layout-map.md. `unemployment-rate-15plus` (Commit EX) and
  `salaried-earnings` (EZ) are microdata in ALL years (the report PDFs never
  publish UR or earnings by religion; salaried-earnings stays PLFS-only).
  mpce's By-state tab is HCES 2023-24 microdata (Commit EV). Raw zips stay
  LOCAL at ~/Desktop/nada-work/ (sha256 + docs committed in sources/nada/).
- The microdata-sprint metrics (EY-FB, all single-source computed-by-religion
  with hard validation gates vs published figures): `top-quintile-share` (HCES
  quintile distribution), `household-net-worth` + `institutional-credit-share`
  (AIDIS 2013 -> 2019 trends since Commit FM: the 2019 round's NADA copy is a
  Nesstar binary but MoSPI's original TXT survives at
  mospi.gov.in/sites/default/files/NSS7718/, provenance in
  sources/nss77-aidis/), and the housing pillar `improved-water-premises` /
  `household-electricity` / `pucca-house` (NSS 76th 2018 via the same kind of
  unlinked TXT mirror - see docs/runbooks/nss76-housing.md). The
  mirror-hunt trick (Wayback the deleted Drupal page, mospi.NIC.in twin if
  gov.in was never crawled) also unlocked health/education 75th - now BUILT
  as the FU/FV spending cards: `hospital-oop-spend` (OOPME per
  hospitalisation case excl childbirth 87/88/89, 2017-18 -> 2025; NOTE the
  75th weight rule is MLT/100-if-NSS=NSC-else-/200, unlike nss76's flat
  rule) and `school-edu-spend` (per enrolled school student excl coaching,
  break_flag on 2025 for the CMS:E concept revisions); both neutral
  polarity, gated to 0.01% vs published cells (recipes:
  docs/runbooks/nss-health.md + cmse-education.md +
  nada/{health,education}-layout-map.md). SAS 2019 and disability 76th
  stay banked-unbuilt. Housing findings INVERT the gap pattern (Muslim
  at/above Hindu) - that is the data, keep it.
- sex-ratio + pop-share are primary RGI census 1961-2011; Sachar Committee feeds
  the `mpce` metric (not sex-ratio anymore).
- **Reproducibility plumbing (Commit GL):** every modal view, the card
  methodology disclosure and every `/m/{id}/` landing carry a `REPRO_TIER` pill
  (READ / COMPUTE / MICRODATA / MANUAL; plain words, slate chrome, NEVER maroon)
  from the dict in build.py — keep it covering every canonical id (companions
  included) or the view shows no tag. ls/mla values now trace to archived L1
  tables `sources/prs-eci-affidavits/{ls-muslim-mps-by-election,mla-muslim-mlas-by-assembly}.csv`
  (kept OUT of Git-LFS via a `.gitattributes` override so they stay diffable on
  GitHub; the canonicalisers READ them, not hardcoded lists) — the
  `audit_accuracy.py` MANUAL sentinel is gone. `_source_documents` now resolves a
  `.meta.json` source_document directly (the 2025 NADA CSV releases) and appends
  `secondary` home_urls; the TXT-mirror PROVENANCE notes (nss75/76/77) + EUS
  2011-12 gained `.meta.json` sidecars, so NO view falls back to a bare home page
  (re-check with the resolution diagnostic if you touch source_document wiring).
