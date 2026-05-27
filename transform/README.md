# Transform

Two stages of transformation:

```
L1 (sources/) --[extract]--> L2 (extracted/) --[canonicalize]--> L3 (canonical/)
```

## Structure

```
transform/
  <source-id>/
    extract.py              L1 -> L2 for this source
  canonicalize/
    <metric-id>.py          L2 -> L3 for this metric (when not a simple 1:1)
  geography_codes.py        shared geography normalization
  religion_codes.py         shared religion-label normalization
```

## Rules

1. **Idempotent.** Re-running with the same L1 input produces byte-identical L2; same L2 produces byte-identical L3.
2. **Pure.** No live network calls during transform. All inputs are files on disk.
3. **Explicit.** No magic auto-detection of file formats; each source has an explicit parser.
4. **Logged.** Every transform run writes `extraction_run` (timestamp + version) onto every L3 row it produces.

## Adding a new transform

Each `transform/<source-id>/extract.py` should:
1. Read the L1 file path from its `.meta.json` sidecar (verify SHA256 matches).
2. Parse with explicit per-table logic (no schema-guessing).
3. Normalize religion labels via `religion_codes.py`.
4. Normalize geography codes via `geography_codes.py`.
5. Write a long-format CSV to `extracted/<source-id>/<table-id>.csv`.

## Empty for now

Stubs will land per metric as URL discovery and L1 archival proceeds. Census 2011 is the first planned extractor.
