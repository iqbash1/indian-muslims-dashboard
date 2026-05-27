# L2 Structured extraction

Parsed tables, one per source-document. **Regeneratable** from L1 + the scripts in `transform/` — never edit by hand.

## Structure

```
extracted/
  census-2011/
    c01-population-by-religion.csv
    c08-education-by-religion.csv
  nfhs-5/
    india-report-tables/...
  ...
```

## Schema (per CSV)

Each L2 table preserves the source's native structure as closely as possible, with these conventions:
- One row per observed cell (long format), not wide tables.
- Column headers are lowercase snake_case.
- Religion values normalized to the controlled vocabulary defined in `manifest/schema/canonical.json` (muslim, hindu, sc, st, christian, sikh, buddhist, jain, other, not_stated, all).
- A column `source_document` records the L1 path that produced the row.

## Why L2 exists separately from L3

L2 is loyal to the source — it preserves the source's geography codes, categorical labels, footnote indicators, etc. L3 is loyal to the dashboard contract — it normalizes geography codes to a single scheme, drops source-specific quirks, and adds methodology notes. Keeping them separate means re-extraction (L1 → L2) and re-mapping (L2 → L3) are independently re-runnable.

## Adding an extraction script

1. Put the script under `transform/<source-id>/`.
2. Read from `sources/<source-id>/...`.
3. Write to `extracted/<source-id>/...`.
4. Include the L1 `source_document` path on every output row.
5. Make the script idempotent — re-running with the same L1 input produces byte-identical L2 output.
