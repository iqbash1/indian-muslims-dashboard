# Audit log

Annual ritual: sample 10 randomly chosen dashboard metrics and trace L4 → L3 → L2 → L1 source file. Drift between layers is a bug.

## Procedure

1. Pick 10 metrics at random from `manifest/metrics.yaml` (status: live or data-loaded).
2. For each:
   - Pull a single (geography, year, religion) row from the L4 dashboard cache.
   - Confirm the value matches `canonical/<metric>.csv` for the same key.
   - Open the L2 extraction file referenced in `source_document`.
   - Open the L1 raw file and locate the cell/page that produced the L2 value.
   - Verify the L1 file's SHA256 matches the `.meta.json` sidecar.
3. Record the sample and result below.
4. Any miss = open an issue and halt new metric onboarding until resolved.

## Annual audits

### 2026 (planned for late Q4)

_Not yet conducted._
