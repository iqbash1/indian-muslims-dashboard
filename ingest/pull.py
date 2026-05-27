"""
Manifest-driven pull script for the Indian Muslims Dashboard.

Reads manifest/sources.yaml. For each target with status=verified, downloads
the URL, archives to target_path with sidecar metadata (SHA256, pull
timestamp, source URL, status code), submits the URL to the Wayback Machine,
and appends a record to manifest/pulls.log.jsonl.

Usage:
  python ingest/pull.py --list
  python ingest/pull.py --source <source-id>
  python ingest/pull.py --source <source-id> --target <target-id>
  python ingest/pull.py --source <source-id> --dry-run
  python ingest/pull.py --source <source-id> --no-wayback

Silent-overwrite protection: if a target_path already exists with different
content than what we just fetched, the new content is written to a dated
sidecar path (e.g. ...2026-05-27.abc123.xlsx) and flagged in the pull log.
The original archived file is never overwritten.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import time
from typing import Any

import truststore
truststore.inject_into_ssl()  # delegate cert validation to the system trust store

import requests
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "manifest" / "sources.yaml"
PULL_LOG = REPO_ROOT / "manifest" / "pulls.log.jsonl"

WAYBACK_SAVE_URL = "https://web.archive.org/save/"
USER_AGENT = "indian-muslims-dashboard-ingest/0.1"
REQUEST_TIMEOUT_SECONDS = 60
POLITE_DELAY_SECONDS = 1
PULL_SCRIPT_VERSION = "0.1.0"


def load_manifest() -> dict[str, Any]:
    with MANIFEST.open() as f:
        return yaml.safe_load(f)


def list_sources(manifest: dict[str, Any]) -> None:
    print(f"{'source_id':<34} {'cadence':<26} {'last_pulled':<22} targets")
    print("-" * 100)
    for src in manifest["sources"]:
        targets = src.get("targets") or []
        n_verified = sum(1 for t in targets if t.get("status") == "verified")
        print(
            f"{src['id']:<34} {src.get('cadence', '?'):<26} "
            f"{str(src.get('last_pulled') or '-'):<22} "
            f"{n_verified}/{len(targets)} verified"
        )


def find_source(manifest: dict[str, Any], source_id: str) -> dict[str, Any]:
    for src in manifest["sources"]:
        if src["id"] == source_id:
            return src
    raise SystemExit(f"source not found: {source_id}")


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_sidecar(target_path: pathlib.Path, payload: dict[str, Any]) -> None:
    sidecar = target_path.with_suffix(target_path.suffix + ".meta.json")
    sidecar.write_text(json.dumps(payload, indent=2))


def append_pull_log(entry: dict[str, Any]) -> None:
    PULL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PULL_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def submit_wayback(url: str) -> str | None:
    try:
        resp = requests.get(
            WAYBACK_SAVE_URL + url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        if resp.ok:
            return resp.url
    except requests.RequestException:
        return None
    return None


def dated_alt_path(target_path: pathlib.Path, sha_prefix: str) -> pathlib.Path:
    today = dt.date.today().isoformat()
    return target_path.with_name(
        f"{target_path.stem}.{today}.{sha_prefix}{target_path.suffix}"
    )


def pull_target(
    source_id: str,
    target: dict[str, Any],
    *,
    dry_run: bool,
    no_wayback: bool,
) -> None:
    target_id = target["target_id"]
    url = target.get("url")
    target_path = REPO_ROOT / target["target_path"]
    status = target.get("status")

    if status != "verified":
        print(f"  skip {target_id}: status={status}")
        return
    if not url:
        print(f"  skip {target_id}: no url set despite status=verified")
        return

    if dry_run:
        print(f"  DRY-RUN {target_id} -> {target_path.relative_to(REPO_ROOT)} from {url}")
        return

    print(f"  pull {target_id} <- {url}")

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
            stream=True,
        )
    except requests.RequestException as e:
        print(f"    FAIL network: {e}")
        append_pull_log({
            "source_id": source_id,
            "target_id": target_id,
            "url": url,
            "pulled_at": now_utc_iso(),
            "result": "network_error",
            "error": str(e),
        })
        return

    if not resp.ok:
        print(f"    FAIL status={resp.status_code}")
        append_pull_log({
            "source_id": source_id,
            "target_id": target_id,
            "url": url,
            "pulled_at": now_utc_iso(),
            "status_code": resp.status_code,
            "result": "http_error",
        })
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
    with tmp_path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)

    new_sha = sha256_of(tmp_path)

    if target_path.exists():
        existing_sha = sha256_of(target_path)
        if existing_sha == new_sha:
            tmp_path.unlink()
            print(f"    unchanged sha256={new_sha[:12]}")
            append_pull_log({
                "source_id": source_id,
                "target_id": target_id,
                "url": url,
                "pulled_at": now_utc_iso(),
                "status_code": resp.status_code,
                "sha256": new_sha,
                "result": "unchanged",
            })
            return
        final_path = dated_alt_path(target_path, new_sha[:12])
        tmp_path.rename(final_path)
        print(f"    CONTENT CHANGED; archived as {final_path.name}")
        result = "changed_archived_as_dated"
    else:
        tmp_path.rename(target_path)
        final_path = target_path
        result = "new"
        print(f"    new sha256={new_sha[:12]} bytes={target_path.stat().st_size}")

    pulled_at = now_utc_iso()
    write_sidecar(final_path, {
        "source_id": source_id,
        "target_id": target_id,
        "url": url,
        "pulled_at": pulled_at,
        "status_code": resp.status_code,
        "content_type": resp.headers.get("Content-Type"),
        "content_length": int(resp.headers.get("Content-Length", "0")) or None,
        "sha256": new_sha,
        "pull_script_version": PULL_SCRIPT_VERSION,
    })

    wayback_url = None
    if not no_wayback:
        wayback_url = submit_wayback(url)
        print(f"    wayback {'ok' if wayback_url else 'failed (non-blocking)'}")

    append_pull_log({
        "source_id": source_id,
        "target_id": target_id,
        "url": url,
        "pulled_at": pulled_at,
        "status_code": resp.status_code,
        "sha256": new_sha,
        "result": result,
        "wayback_url": wayback_url,
        "saved_to": str(final_path.relative_to(REPO_ROOT)),
    })


def pull_source(
    manifest: dict[str, Any],
    source_id: str,
    *,
    target_id: str | None,
    dry_run: bool,
    no_wayback: bool,
) -> None:
    src = find_source(manifest, source_id)
    targets = src.get("targets") or []
    if target_id:
        targets = [t for t in targets if t.get("target_id") == target_id]
        if not targets:
            raise SystemExit(f"target not found in {source_id}: {target_id}")
    print(f"source: {source_id}  ({len(targets)} target(s))")
    for t in targets:
        pull_target(source_id, t, dry_run=dry_run, no_wayback=no_wayback)
        time.sleep(POLITE_DELAY_SECONDS)


def main() -> None:
    p = argparse.ArgumentParser(description="Manifest-driven pull script.")
    p.add_argument("--list", action="store_true", help="List sources and exit")
    p.add_argument("--source", help="Source ID to pull")
    p.add_argument("--target", help="Target ID within source (default: all verified)")
    p.add_argument("--dry-run", action="store_true", help="Print planned actions only")
    p.add_argument("--no-wayback", action="store_true", help="Skip Wayback Machine submission")
    args = p.parse_args()

    manifest = load_manifest()

    if args.list:
        list_sources(manifest)
        return

    if not args.source:
        p.error("--source required (or use --list)")

    pull_source(
        manifest,
        args.source,
        target_id=args.target,
        dry_run=args.dry_run,
        no_wayback=args.no_wayback,
    )


if __name__ == "__main__":
    main()
