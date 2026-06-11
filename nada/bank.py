#!/usr/bin/env python3
"""Bank NSS unit-level microdata from MoSPI's NADA API (provenance-first).

The raw bytes are the irreplaceable asset (the API may be withdrawn or flaky). This
tool lists a survey's files and downloads the ones we keep to a LOCAL archive with a
SHA256, so every metric stays buildable offline. See nada/PLAN.md.

Usage:
  NADA_API_KEY=...  .venv/bin/python nada/bank.py list    <IDNO>
  NADA_API_KEY=...  .venv/bin/python nada/bank.py get     <IDNO> <FILENO> <DESTDIR>
  NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget <IDNO> <DESTDIR>

autoget is RESUMABLE: a survey whose DESTDIR already has MANIFEST.json is skipped;
an incomplete survey (data file missing) writes no MANIFEST, so re-running retries it.

Notes:
  - <IDNO> is the STRING id (e.g. DDI-IND-CSO-PLFS-2023-24), NOT the numeric catalog id.
  - <FILENO> is printed by `list` (the API's per-file handle; = base64 of the filename).
  - Network goes through `curl` (the sandbox does TLS interception that Python's urllib
    rejects but curl trusts), with connect-timeout + retries for the flaky gov server.
    The key is read from $NADA_API_KEY, passed to curl via a stdin config (-K -) so it
    never lands in argv / `ps` / the transcript, and is never written to disk. Keep the
    downloaded zips OUT of git (archive under ~/Desktop/nada-work/); commit only the
    SHA256 + small doc files.
"""
import base64, datetime, hashlib, json, os, re, subprocess, sys

BASE = "https://microdata.gov.in/NADA/index.php/api"
# resilient curl: fail fast on a stalled connect, retry transient errors/timeouts
_RESIL = ["--connect-timeout", "30", "--retry", "5", "--retry-delay", "5",
          "--retry-connrefused", "--retry-all-errors"]


def _key():
    k = (os.environ.get("NADA_API_KEY") or "").strip()
    if not k:
        sys.exit("ERROR: NADA_API_KEY is not set (header-only credential; never commit it).")
    return k


def _cfg(key):
    return f'header = "X-API-KEY: {key}"\n'  # curl reads from stdin via -K - ; key off argv


def _curl_text(url, key, timeout=120):
    cmd = ["curl", "-sS", "--location", "--max-time", str(timeout), *_RESIL,
           "-w", "\n__HTTP__%{http_code}", "-K", "-", url]
    r = subprocess.run(cmd, input=_cfg(key), text=True, capture_output=True)
    out, code = r.stdout, ""
    if "__HTTP__" in out:
        out, code = out.rsplit("__HTTP__", 1)
    if r.returncode != 0 or code.strip() != "200":
        sys.exit(f"HTTP {code.strip() or '?'} (curl rc={r.returncode}) for {url}\n"
                 f"{r.stderr[:300]}\n{out[:600]}")
    return out


def _curl_download(url, key, dest, timeout=14400):
    # Resumable + stall-detecting: -C - continues a partial file (the gov server
    # can drop to ~50KB/s, so a fixed cap is wrong for 100MB+ files); abort only
    # if throughput stays under 1KB/s for 3 minutes, with a 4h hard ceiling.
    cmd = ["curl", "-sS", "--location", "-C", "-",
           "--speed-limit", "1024", "--speed-time", "180",
           "--max-time", str(timeout), *_RESIL,
           "-o", dest, "-w", "%{http_code} %{size_download}", "-K", "-", url]
    r = subprocess.run(cmd, input=_cfg(key), text=True, capture_output=True)
    info = (r.stdout or "").strip().split()
    code = info[0] if info else "?"
    # 206 = resumed range; 416 = "range not satisfiable" i.e. the local file is
    # already complete (curl -C - at EOF) - success, do NOT delete it.
    ok = (r.returncode == 0 and code in ("200", "206")) or (
        code == "416" and os.path.exists(dest) and os.path.getsize(dest) > 0)
    if not ok:
        sys.stderr.write(f"  !! HTTP {code} (curl rc={r.returncode}) {os.path.basename(dest)} "
                         f"{r.stderr[:160].strip()}\n")
        # Keep a mid-transfer partial (code 000/200/206) so the next run resumes;
        # delete only a real HTTP-error body (4xx/5xx page), which must not be
        # resumed into.
        if os.path.exists(dest) and code.isdigit() and code >= "400":
            try:
                os.remove(dest)
            except OSError:
                pass
    return ok


def _find_file_rows(obj):
    """Recursively locate the first list of dicts that look like file entries."""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        keys = {k.lower() for k in obj[0]}
        if keys & {"file_name", "filename", "name", "fileno", "file_id"}:
            return obj
    if isinstance(obj, dict):
        for v in obj.values():
            r = _find_file_rows(v)
            if r:
                return r
    return None


def _bytes(s):
    m = re.match(r'([\d.]+)\s*(KB|MB|GB|TB|B)?', (s or '').strip(), re.I)
    if not m:
        return 0
    return int(float(m.group(1)) * {'B': 1, 'KB': 1024, 'MB': 1024**2,
                                    'GB': 1024**3, 'TB': 1024**4}[(m.group(2) or 'B').upper()])


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for ch in iter(lambda: fh.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest(), os.path.getsize(path)


def _load_fileslist(idno, key):
    p = f"nada/fileslist/{idno}.json"
    if os.path.isfile(p):
        return json.load(open(p))
    data = json.loads(_curl_text(f"{BASE}/datasets/{idno}/fileslist", key))
    os.makedirs("nada/fileslist", exist_ok=True)
    json.dump(data, open(p, "w"), indent=2)
    return data


# classification: data = the unit-level file(s) we keep; skip = redundant statistical
# formats (same data, other software); doc = method / layout / report / codes / DDI / etc.
_SKIPFMT = re.compile(r'(sas|spss|stata|json|text)[^/]*\.zip$', re.I)


def _classify(name, size_str):
    n = name.lower()
    if _SKIPFMT.search(n):
        return 'skip'
    if 'report' in n:                      # a published report packaged as .rar/.zip is a doc
        return 'doc'
    if n.endswith(('.zip', '.rar', '.csv', '.txt', '.dat')) and _bytes(size_str) >= 1_000_000:
        return 'data'                       # the real unit-level file(s); keeps multi-visit too
    return 'doc'                            # xlsx/pdf/doc/docx/xml + tiny code/struct files


# Of the 'doc' files, KEEP (download) the build-critical ones + anything small; the rest
# (bulky KI/full-report PDFs, instruction manuals, duplicates) stay on the MoSPI portal.
_KEEPDOC = re.compile(
    r'(layout|datalay|estimation|sample.?design|readme|note_for_data|note_on|rider|'
    r'schedule|sch_|sch -|_code|district_code|dist_code|state_?code|tabulation_state|'
    r'codes for blocks|\bnic\b|\bnco\b|\.xml$)', re.I)


def _want_doc(name, size_str):
    return bool(_KEEPDOC.search(name)) or _bytes(size_str) < 1_500_000


def cmd_list(idno):
    key = _key()
    raw = _curl_text(f"{BASE}/datasets/{idno}/fileslist", key)
    os.makedirs("nada/fileslist", exist_ok=True)
    raw_path = f"nada/fileslist/{idno}.json"
    try:
        data = json.loads(raw)
    except Exception:
        open(raw_path, "w").write(raw)
        print(f"# {idno}: non-JSON response saved -> {raw_path}\n{raw[:600]}")
        return
    json.dump(data, open(raw_path, "w"), indent=2)
    rows = _find_file_rows(data) or []
    print(f"# {idno}  ({len(rows)} files)   raw -> {raw_path}")
    if not rows:
        print(json.dumps(data, indent=2)[:1500]); return
    print(f"{'FILENO':<46} {'SIZE':>14}  FILENAME")
    for f in rows:
        name = f.get("file_name") or f.get("filename") or f.get("name") or "?"
        fileno = (f.get("FileNo") or f.get("fileno") or f.get("file_id")
                  or base64.b64encode(name.encode()).decode())
        size = f.get("file_size") or f.get("size") or f.get("filesize") or ""
        print(f"{str(fileno):<46} {str(size):>14}  {name}")


def cmd_get(idno, fileno, destdir):
    key = _key()
    os.makedirs(destdir, exist_ok=True)
    try:
        name = base64.b64decode(fileno).decode()
        if "/" in name or not name.strip():
            raise ValueError
    except Exception:
        name = fileno
    dest = os.path.join(destdir, os.path.basename(name))
    if not _curl_download(f"{BASE}/fileslist/download/{idno}/{fileno}", key, dest):
        sys.exit(f"download failed for {idno}/{fileno}")
    sha, total = _sha(dest)
    print(f"OK  {dest}\n    bytes={total}  ({total/1e6:,.1f} MB)\n    sha256={sha}")
    with open(os.path.join(destdir, "SHA256SUMS.txt"), "a") as fh:
        fh.write(f"{sha}  {os.path.basename(dest)}  ({total} bytes, idno={idno}, fileno={fileno})\n")


def cmd_autoget(idno, destdir):
    key = _key()
    manifest_path = os.path.join(destdir, "MANIFEST.json")
    if os.path.isfile(manifest_path):
        print(f"# {idno}: already complete -> skip ({destdir})")
        return
    rows = _find_file_rows(_load_fileslist(idno, key)) or []
    os.makedirs(destdir, exist_ok=True)
    items = []
    for f in rows:
        name = f.get("file_name") or f.get("filename") or f.get("name") or "?"
        fileno = (f.get("FileNo") or f.get("fileno") or f.get("file_id")
                  or base64.b64encode(name.encode()).decode())
        size = f.get("file_size") or f.get("size") or f.get("filesize") or ""
        items.append((name, str(fileno), _classify(name, size), size))
    manifest = {"idno": idno, "base": BASE,
                "pulled_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "files": []}
    data_ok, got_data = True, 0
    for name, fileno, role, size in items:
        if role == 'skip':
            print(f"  skip  {name}"); continue
        if role == 'doc' and not _want_doc(name, size):
            print(f"  -doc  {name}  (bulky; portal-only)"); continue
        dest = os.path.join(destdir, os.path.basename(name))
        url = f"{BASE}/fileslist/download/{idno}/{fileno}"
        if _curl_download(url, key, dest):
            sha, total = _sha(dest)
            manifest["files"].append({"name": os.path.basename(name), "fileno": fileno,
                                      "role": role, "bytes": total, "sha256": sha, "url": url})
            print(f"  {role:4s} {total/1e6:7.1f}MB  {os.path.basename(name)}  {sha[:12]}")
            got_data += (role == 'data')
        else:
            print(f"  FAIL {role}  {name}")
            data_ok = data_ok and role != 'data'
    if not data_ok or got_data == 0:
        print(f"# {idno}: INCOMPLETE (data missing) -> no MANIFEST written; re-run to retry")
        return
    json.dump(manifest, open(manifest_path, "w"), indent=2)
    with open(os.path.join(destdir, "SHA256SUMS.txt"), "w") as fh:
        for f in manifest["files"]:
            fh.write(f"{f['sha256']}  {f['name']}  ({f['bytes']} bytes, {f['role']})\n")
    nd = sum(f['role'] == 'data' for f in manifest["files"])
    print(f"# {idno}: {nd} data + {len(manifest['files'])-nd} docs -> {destdir}")


def main(argv):
    if len(argv) == 3 and argv[1] == "list":
        cmd_list(argv[2])
    elif len(argv) == 5 and argv[1] == "get":
        cmd_get(argv[2], argv[3], argv[4])
    elif len(argv) == 4 and argv[1] == "autoget":
        cmd_autoget(argv[2], argv[3])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
