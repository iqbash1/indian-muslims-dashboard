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

Pages land as metrics move from `stub` → `defined` → `data-loaded` → `live` in `manifest/metrics.yaml`. First page expected: `lit-7plus.md` once Census 2011 C-8 is archived and extracted.
