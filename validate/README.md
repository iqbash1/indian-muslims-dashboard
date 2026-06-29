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

### Prose-number consistency  *(implemented)*
- Every hardcoded figure in authored prose (narratives.yaml Bottom line / status note, build.py literals) still matches the canonical value the charts/heroes/tables render
- The same figure quoted in several files (e.g. ger-higher-ed across narratives, metrics, CLAUDE.md and two runbooks) stays in sync
- Derived literals recompute from canonical (ls-share parity seats, the school-edu-spend INR-100 ratio)
- Registry: `manifest/prose_checks.yaml`

## Implementation

Implemented:
- `validate.py` — manifest validation (sources + metrics against their JSON schemas) and L3 canonical-CSV validation against `manifest/schema/canonical.json`. Run before every build; expects 0 errors.
- `audit_consistency.py` — doc-vs-data drift: hardcoded metric counts (README), definition year-span advisory, and the share-link bijection (tab ↔ stub ↔ OG image). Wired into CI.
- `audit_accuracy.py` — value plausibility (range-by-unit, CI ordering, duplicate keys), provenance SHA256 vs archive, and the `extraction_run` stamp-shape column-swap tripwire. Wired into CI.
- `audit_prose_numbers.py` — prose-number consistency (anchored figure match, cross-surface agreement, internal-math) driven by `manifest/prose_checks.yaml`. Wired into CI.
- `check_refresh.py` — refresh-cadence check (flags sources past `next_expected`, fails CI once a source is more than 60 days overdue). Wired into CI.

Still planned: L1 integrity (sidecar SHA verification), L2 schema checks, the L3 cell-completeness + `comparison_baselines` checks, cross-source reconciliation, and drift detection on pull.
