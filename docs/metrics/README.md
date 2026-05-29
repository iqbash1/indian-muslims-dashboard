# Metric methodology pages

One markdown page per metric (matching `manifest/metrics.yaml`). The dashboard tile for each metric links to its methodology page; this is the transparency surface for researchers and skeptical readers.

## Required sections per page

1. **What it measures** — plain-language definition, not the source's jargon.
2. **Source** — primary source, cross-check sources, links to manifest entries.
3. **Comparison baseline** — which religion(s) the dashboard compares Muslim values against, and why.
4. **Geography** — what levels are available, what aren't, and why.
5. **Last updated** — reference year + pull date.
6. **Known limitations** — sample-size caveats, definitional changes, missing geographies.
7. **Methodology breaks** — list of years where the underlying definition changed.
8. **Download** — link to the L3 CSV for this metric.
9. **Provenance** — pointer to L2 extraction file, which links to L1 source file with SHA256.

## Status

Not yet built — per-metric pages remain a future enhancement. In practice the transparency surface is currently served by: each card's inline methodology note and "data current to" year, the linked canonical L3 CSV (full per-row provenance: `source_id`, `source_document`, `methodology_note`, `break_flag`), and the per-source runbooks in `docs/runbooks/`. When these pages are built, start with `lit-7plus.md` — note its Census 2011 source is **C-9** (education by religious community), not C-8 (see the `census-india-2011` runbook's 2026-05-27 correction).
