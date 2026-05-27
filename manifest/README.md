# Manifests

This directory is the source-of-truth for what the dashboard tracks and where the data comes from. Pull and transform scripts read these files; editing happens here, not in code.

## Files

- `sources.yaml` — registry of every external data source. Schema: `schema/source-entry.json`.
- `metrics.yaml` — definition of every metric on the dashboard. Schema: `schema/metric-entry.json`.
- `schema/canonical.json` — JSON Schema for L3 canonical observations (the dashboard's data contract).
- `pulls.log.jsonl` — append-only log written by `ingest/pull.py`. Each line records a pull attempt with source, target, URL, timestamp, status, and SHA256.

## Editing rules

1. **Never delete a source or metric** — set `status: deprecated` instead. Historical data depends on the ID.
2. **Never change an `id` field** — IDs are referenced from canonical rows and runbooks. Add a new entry instead.
3. **Always update `runbook:` and `archive_dir:`** when adding a source so the operational trail is intact.
4. **URLs go in `targets:`**, not in the source root. Multiple targets per source is normal.
5. **Set `status: verified` only after opening the URL in a browser and confirming the file is what the description says.**
