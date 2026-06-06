# Validate

Checks that run after every pull and every transform to catch drift before it reaches L3 / the dashboard.

## Checks

### Manifest validation  *(implemented)*
- `sources.yaml` validates against `manifest/schema/source-entry.json`
- `metrics.yaml` validates against `manifest/schema/metric-entry.json`
- Every metric's `sources.primary` references a known source ID
- Every source's `archive_dir` and `runbook` paths exist

### L1 integrity
- Every archived file has a `.meta.json` sidecar
- Every sidecar's `sha256` matches the actual file SHA

### L2 schema
- Every L2 CSV column conforms to its declared schema
- Religion values are in the controlled vocabulary
- Geography codes resolve in `transform/geography_codes.py`

### L3 contract  *(schema validation implemented)*
- Every L3 CSV validates against `manifest/schema/canonical.json`
- For every metric, every required (geography × religion × year) cell is present or explicitly marked missing
- `comparison_baselines` religions exist in every metric's data (otherwise the dashboard cannot render the tile correctly)

### Cross-source reconciliation
- For metrics with both `primary` and `cross_check` sources, divergence above a per-metric threshold flags a review item
- E.g. literacy from Census vs PLFS for the same year and geography should agree within ~3pp

### Drift detection on pull
- New value within survey CI of prior pull's value where applicable
- Schema unchanged from prior pull (column order, names, types)

## Implementation

Implemented:
- `validate.py` — manifest validation (sources + metrics against their JSON schemas) and L3 canonical-CSV validation against `manifest/schema/canonical.json`. Run before every build; expects 0 errors.
- `check_refresh.py` — refresh-cadence check (flags sources past `next_expected`, fails CI once a source is more than 60 days overdue). Wired into CI.

Still planned: L1 integrity (sidecar SHA verification), L2 schema checks, the L3 cell-completeness + `comparison_baselines` checks, cross-source reconciliation, and drift detection on pull.
