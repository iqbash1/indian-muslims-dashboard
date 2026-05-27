# L3 Canonical metric series

The dashboard's data contract. **Regeneratable** from L2 + the canonical mapping scripts in `transform/` — never edit by hand.

## Structure

One CSV per metric (matching `manifest/metrics.yaml`):

```
canonical/
  lit-7plus.csv
  mean-yrs-schooling.csv
  imr.csv
  ...
```

## Schema

Defined by `manifest/schema/canonical.json`. Every row carries:

| column | required | notes |
|---|---|---|
| metric_id | yes | matches `manifest/metrics.yaml` |
| geography_level | yes | national / state / district / sub-district |
| geography_code | yes | single normalized scheme (TODO: pick — ISO 3166-2:IN for state? LGD for district?) |
| year | yes | reference year, not publication year |
| religion | yes | controlled vocabulary |
| value | yes | numeric |
| denominator | no | what the value is a share of, where applicable |
| sample_size | no | populated for survey sources |
| ci_lower / ci_upper | no | populated where survey CIs exist |
| source_id | yes | matches `manifest/sources.yaml` |
| source_document | yes | path to L1 file |
| extraction_run | yes | timestamp + version string of the run that produced this row |
| methodology_note | no | inline note that propagates to dashboard tile |
| break_flag | no | true when this row marks a methodology break from prior years |

## Why L3 is the dashboard's contract

- Stable schema regardless of source format changes
- Stable metric IDs regardless of upstream URL or report restructuring
- Methodology breaks are explicit, not implicit
- Comparison-baseline religions (Hindu / SC-ST / all) are present in every metric where applicable, by construction
- Full provenance: every value traces to `source_document` → L1 file → SHA256 in sidecar
