# Ingest

Manifest-driven pull scripts. Reads `manifest/sources.yaml`, writes to `sources/`, logs to `manifest/pulls.log.jsonl`.

## Usage

```bash
python ingest/pull.py --list
python ingest/pull.py --source census-india-2011 --dry-run
python ingest/pull.py --source census-india-2011
python ingest/pull.py --source census-india-2011 --target c01-population-by-religion
python ingest/pull.py --source census-india-2011 --no-wayback
```

## What it does per pull

1. Confirms `status: verified` and that a URL is set.
2. Downloads to a `.tmp` path, computes SHA256.
3. If `target_path` already exists with the same SHA → no-op, log `unchanged`.
4. If it exists with different content → write to dated alt path (`name.YYYY-MM-DD.sha12.ext`), never overwrite the original. Log `changed_archived_as_dated`.
5. If new → write to `target_path`. Log `new`.
6. Write `.meta.json` sidecar (source, URL, timestamp, SHA256, content type, status code, script version).
7. Submit URL to Wayback Machine (skip with `--no-wayback`).
8. Append JSONL entry to `manifest/pulls.log.jsonl`.

## What it does NOT do

- Does not modify `manifest/sources.yaml` (manifest is human-edited).
- Does not extract or transform — that's the job of `transform/`.
- Does not validate content shape — that's `validate/`.
- Does not handle authentication for sources that need it (DHS Program for NFHS unit-level, etc.) — those are manual downloads, archived using the same naming convention.

## Adding a new source

1. Add an entry to `manifest/sources.yaml`. Use existing entries as a template.
2. Create `docs/runbooks/<source-id>.md` and document URL discovery.
3. Discover and verify each target URL. Set `status: verified` and the `url:`.
4. Run `python ingest/pull.py --source <source-id> --dry-run` first.
5. Run without `--dry-run`. Inspect `manifest/pulls.log.jsonl`.

## Dependencies

```
pip install -r requirements-dev.txt
```

Ingest needs `requests` + `truststore`; `validate/` also needs `jsonschema`.
These live in `requirements-dev.txt` (root `requirements.txt` is the minimal
deploy set — PyYAML only — so the Cloudflare build stays reliable).
