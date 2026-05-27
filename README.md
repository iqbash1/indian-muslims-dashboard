# Indian Muslims Living Conditions Dashboard

Long-horizon data project tracking living-conditions indicators for India's Muslim population, with Hindu / SC-ST / national comparison baselines on every metric.

## Architecture

Four-layer data flow:

| Layer | Path | Mutability |
|---|---|---|
| L1 Raw archive | `sources/` | Immutable; every external file ever pulled |
| L2 Structured extraction | `extracted/` | Regeneratable from L1 |
| L3 Canonical metric series | `canonical/` | Regeneratable from L2 |
| L4 Dashboard cache | (separate build) | Rebuildable from L3 |

The dashboard never reads from L1 or L2 directly, never queries an external source live. Every number is traceable: L4 → L3 → L2 → L1 source file with SHA256.

## Layout

```
sources/      L1 raw archive (Git-LFS)
extracted/    L2 structured tables
canonical/    L3 canonical series (the dashboard contract)
manifest/     sources.yaml, metrics.yaml, JSON schemas
ingest/       pull scripts (manifest-driven)
transform/    L1 to L2 and L2 to L3 mappings
validate/     range checks, cross-source recon
docs/         per-metric methodology, runbooks, audit log
```

## Operational principles

1. Manifest-driven: edit `manifest/sources.yaml` and `manifest/metrics.yaml`, not scripts.
2. Every pull writes to L1 with sidecar metadata + Wayback submission.
3. Every dashboard tile shows a comparison baseline (Hindu / SC-ST / national).
4. Contested sources (civic incident databases) are shown separately and never aggregated with government data.
5. Methodology breaks (e.g., NFHS-5 vs NFHS-6 definition changes) are recorded as `break_flag` on canonical rows; charts render breaks as visible discontinuities.

## Quick start

```bash
pip install -r requirements.txt
python ingest/pull.py --list
python ingest/pull.py --source census-india-2011 --dry-run
python ingest/pull.py --source census-india-2011
```

## Status

Scaffold in progress. Phase 1 (materialist anchors) source registry defined; URL discovery and first pulls pending. See `docs/runbooks/census-india-2011.md` for the immediate next task.
