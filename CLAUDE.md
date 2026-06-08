# muslimdata.in — working notes for Claude

Static, source-traceable dashboard of living-conditions indicators for India's
Muslims (Hindu + all-India baselines). Live at https://muslimdata.in/. The full
running state lives in auto-memory ([[dashboard-build-state]]); this file is the
always-in-context short version of the must-knows.

## Build & deploy
- Build the site: `.venv/bin/python dashboard/build.py` (writes `docs/`)
- Validate: `.venv/bin/python validate/validate.py` (expect `0 errors`). CI also
  runs `audit_consistency.py`, `check_refresh.py`, and Playwright browser smoke
  tests (`tests/smoke.py` via `.github/workflows/smoke.yml`; run locally after
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
- Every value traces to a primary source with a SHA256-archived L1 file.
- **Per-metric views are MODAL TABS** (by state/sex/district), each with its own
  shareable `/m/{id}/{view}/` URL + OG image and a share popover; the card face
  shows only the main chart + a "More views" hint. Don't move drill-downs back
  onto the card face, and respect `prefers-reduced-motion`.

## Editing gotchas
- Card prose lives in **3 places** — keep in sync: `manifest/metrics.yaml`
  (`definition` + `methodology_notes`), the `PLAIN_DEFINITION` dict in
  `dashboard/build.py`, and hand-written `docs/runbooks/*.md`. A wording/count
  fix must hit all three.
- In metrics.yaml, `religions` / `comparison_baselines` / `break_notes` /
  `cross_check` are declarative metadata — NOT rendered. Only `definition` +
  `methodology_notes` show (in the modal).
- `docs/m/<id>/` is a FULL indexable landing page (hero, data tables, sources,
  JSON-LD); the per-view `docs/m/<id>/<view>/` are thin redirect stubs (OG meta +
  a relative `/#<id>/<view>` redirect). Both regenerate from canonical, so they
  change on most rebuilds — partial-looking diffs there are expected.
- 21 carded metrics. sex-ratio + pop-share are primary RGI census 1961-2011;
  Sachar Committee feeds the `mpce` metric (not sex-ratio anymore).
