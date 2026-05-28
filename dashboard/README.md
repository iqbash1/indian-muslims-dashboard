# L4 Dashboard

Single static HTML build from `canonical/*.csv`. Output lives at `docs/index.html` (so GitHub Pages can serve it from `/docs`). Open in any browser — no server required, Chart.js loaded from CDN.

Live URL: https://iqbash1.github.io/indian-muslims-dashboard/

## Build

```bash
python dashboard/build.py
open docs/index.html
```

The builder reads every `canonical/*.csv` and renders one tile per metric with:
- Headline value + comparison-baseline values inline
- Sortable per-state table
- Bar chart (Chart.js)
- Per-tile source path, methodology note, and "data current to" badge
- Known-gap disclosures where the source extraction is partial

## Why HTML and not a framework

The dashboard's first priority is **provenance, not interactivity**. A static single-file HTML preview that any clone can open without a build step keeps the focus on data correctness while we add metrics. A richer interactive front-end (filtering, map view, downloads) is a later L4 iteration once the canonical layer is comprehensive.

## Regenerate after canonical changes

```bash
python dashboard/build.py
```

Idempotent; rebuilds `preview/index.html` from current `canonical/` state.
