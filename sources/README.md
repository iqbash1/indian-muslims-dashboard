# L1 Raw archive

**Immutable.** Every external file ever pulled lives here, exactly as fetched. Never modified, never deleted.

## Structure

One directory per source ID (matching `manifest/sources.yaml`):

```
sources/
  census-2011/
    c-series/c01-population-by-religion.xlsx
    c-series/c01-population-by-religion.xlsx.meta.json
    hh-series/...
  nfhs-5/
    reports/india-report-volume-1.pdf
    reports/india-report-volume-1.pdf.meta.json
  ...
```

## Sidecar metadata

Every archived file has a `.meta.json` sidecar produced by `ingest/pull.py`. Schema:

```json
{
  "source_id": "...",
  "target_id": "...",
  "url": "https://...",
  "pulled_at": "2026-MM-DDTHH:MM:SS+00:00",
  "status_code": 200,
  "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "content_length": 123456,
  "sha256": "abc...",
  "pull_script_version": "0.1.0"
}
```

## Storage

Tracked by Git-LFS (see `.gitattributes`). Setup once per clone:

```bash
git lfs install
git lfs pull
```

## Adding files

Always via `ingest/pull.py` for URLs we can fetch programmatically. For manual downloads (NFHS unit-level via DHS Program, RTI responses, etc.):

1. Drop the file in the correct `sources/<source-id>/` subdirectory.
2. Compute SHA256: `shasum -a 256 path/to/file`.
3. Write a `.meta.json` sidecar by hand following the schema above, with `pull_script_version: "manual"`.
