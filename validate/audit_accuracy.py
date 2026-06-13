"""
Data-ACCURACY audit — the value/provenance layer the other gates don't cover.

validate.py checks schema/types/vocabulary; audit_consistency.py checks
doc-vs-data drift; check_refresh.py checks cadence. NONE of them check whether a
value is plausible, whether the L1 file it cites still exists with the archived
checksum, or whether the columns mean what their header says. This gate does:

  PROVENANCE (hard)
    - every source_id used in canonical exists in sources.yaml
    - every referenced source_document resolves to one of the sanctioned
      provenance shapes, and any COMMITTED file's SHA256 still matches its
      archive (catches silent source drift / tampering / unsmudged LFS)

  VALUE PLAUSIBILITY (hard)
    - value present & numeric; in range for its unit (percent in [0,100], rate/
      currency/count >= 0, sex-ratio not impossible); ci_lower <= value <= ci_upper
    - no duplicate natural key (geo x year x religion x sex x residence)
    - extraction_run looks like a run-stamp, NOT note text. This is the column-
      swap tripwire: the 2026-06 audit found 32 sex-ratio/lit-7plus rows with
      extraction_run <-> methodology_note transposed, which schema validation
      (both are strings) sailed past. Don't let that class regress.

  CROSS-SERIES (advisory)
    - pop-share national religion breakdown sums to ~100

By-design provenance shapes are recognised, not flagged: the `MANUAL:` sentinel
(ls-share/mla-share ECI affidavit compilation), `<state>` glob templates (census
MDDS district rows), `.meta.json` sidecar pointers, and local-only microdata
ZIPs that are hash-manifested via a dir SHA256SUMS.txt. They print as DIAG.

Exit non-zero on any ERROR. Run:  python validate/audit_accuracy.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import sys
from collections import defaultdict

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
CANON = REPO / "canonical"

STAMP_RE = re.compile(r"(canonicalize|manual-ext|extract)\S*v?\d|\d{8}T\d{6}Z|\d{4}-\d{2}-\d{2}")
GEO_RE = re.compile(r"^(IN|IN-S\d{2}(?:_\d{2})?|IN-S\d{2}-D\d{3})$")
NM_RE = re.compile(r"(\d+)\s*/\s*(\d+)")
# Local-only microdata: raw ZIP kept off-repo (~/Desktop/nada-work/), provenance
# via a committed dir SHA256SUMS.txt + .meta.json sidecar.
LOCAL_ONLY_RE = re.compile(r"^sources/(nada|hces-|nss)\S*\.zip$")

errors: list[str] = []
warns: list[str] = []
diag: dict[str, int] = defaultdict(int)


def err(m: str) -> None:
    errors.append(m)


def warn(m: str) -> None:
    warns.append(m)


# ---- provenance helpers ---------------------------------------------------
_sha_cache: dict[str, str] = {}
_sums_cache: dict[str, dict[str, str]] = {}


def file_sha(p: pathlib.Path) -> str:
    k = str(p)
    if k not in _sha_cache:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _sha_cache[k] = h.hexdigest()
    return _sha_cache[k]


def is_lfs_pointer(p: pathlib.Path) -> bool:
    try:
        with p.open("rb") as f:
            return f.read(40).startswith(b"version https://git-lfs")
    except OSError:
        return False


def dir_sums(d: pathlib.Path) -> dict[str, str]:
    key = str(d)
    if key in _sums_cache:
        return _sums_cache[key]
    out: dict[str, str] = {}
    f = d / "SHA256SUMS.txt"
    if f.exists():
        for line in f.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
                out[parts[1]] = parts[0].lower()
    _sums_cache[key] = out
    return out


def recorded_sha(p: pathlib.Path) -> str | None:
    side = pathlib.Path(str(p) + ".meta.json")
    if side.exists():
        try:
            s = json.loads(side.read_text()).get("sha256")
            if s:
                return s.lower()
        except (OSError, ValueError):
            pass
    return dir_sums(p.parent).get(p.name)


def check_provenance(sd: str, users: list[str]) -> None:
    """Classify a source_document into a sanctioned shape or an error."""
    if sd.startswith("MANUAL"):
        diag["MANUAL sentinel (ls/mla, no archived L1)"] += 1
        return
    if "<" in sd:  # census MDDS state glob; concrete files exist per-district
        diag["<glob> template path"] += 1
        return
    p = REPO / sd
    if sd.endswith(".meta.json"):
        if p.exists() and (json.loads(p.read_text()).get("sha256") if p.suffix == ".json" else None):
            diag[".meta.json sidecar pointer (sha inside)"] += 1
        else:
            err(f"source_document is a .meta.json with no sha256: {sd}")
        return
    if pathlib.Path(sd).name.upper().startswith("PROVENANCE"):
        # Human provenance note for a local-only TXT-mirror source; the actual
        # data files are hash-manifested in the dir's SHA256SUMS.txt.
        if (p.parent / "SHA256SUMS.txt").exists():
            diag["PROVENANCE-note pointer (dir hash-manifested)"] += 1
        else:
            warn(f"PROVENANCE-note source_document but dir not hash-manifested: {sd}")
        return
    if not p.exists():
        if LOCAL_ONLY_RE.match(sd) and recorded_sha(p) is not None:
            diag["local-only microdata ZIP (hash-manifested)"] += 1
        else:
            err(f"source_document missing and not hash-manifested: {sd}  (used by {users})")
        return
    if is_lfs_pointer(p):
        # Content not pulled (CI checks out with lfs:false); can't hash what
        # isn't here. Locally, LFS is smudged so this branch doesn't fire and
        # the SHA256 is verified for real.
        diag["LFS pointer, content not pulled (sha skipped)"] += 1
        return
    rec = recorded_sha(p)
    if rec is None:
        warn(f"committed source_document has no archived SHA256: {sd}")
        return
    if file_sha(p) != rec:
        err(f"SHA256 MISMATCH (file changed since archive): {sd}")
    else:
        diag["committed file, SHA256 verified"] += 1


# ---- value-range kind ------------------------------------------------------
def value_kind(mid: str, unit: str, geo_level: str) -> str:
    if mid == "district-concentration-top100":
        # National row is a concentration %; the top-100 rows are absolute counts.
        return "percent" if geo_level == "national" else "count"
    if mid == "sex-ratio":
        return "ratio"
    u = unit.lower()
    if "percent" in u or u in ("%", "share"):
        return "percent"
    if "inr" in u or "rupee" in u:
        return "currency"
    if "per 1,000" in u or "per 100,000" in u or "per 100k" in u or "rate" in u:
        return "rate"
    return "other"


def check_range(mid: str, kind: str, v: float, rid: str) -> None:
    if kind == "percent":
        if not (-0.01 <= v <= 100.01):
            err(f"{mid} {rid}: percent out of [0,100]: {v}")
    elif kind == "ratio":  # sex-ratio: flag only impossible (parse/scale error)
        if v <= 0 or v > 5000:
            err(f"{mid} {rid}: sex-ratio impossible: {v}")
    elif kind in ("rate", "currency", "count"):
        if v < 0:
            err(f"{mid} {rid}: {kind} negative: {v}")


# ---- main pass -------------------------------------------------------------
def main() -> None:
    sources = yaml.safe_load((REPO / "manifest" / "sources.yaml").read_text())["sources"]
    src_ids = {s["id"] for s in sources}
    metrics = yaml.safe_load((REPO / "manifest" / "metrics.yaml").read_text())["metrics"]
    unit = {m["id"]: (m.get("unit") or "") for m in metrics}

    referenced_docs: dict[str, list[str]] = defaultdict(list)
    n_rows = 0

    for csvp in sorted(CANON.glob("*.csv")):
        mid = csvp.stem
        rows = list(csv.DictReader(csvp.open()))
        if not rows:
            warn(f"{mid}: empty CSV")
            continue
        cols = rows[0].keys()
        keycols = [c for c in ("geography_code", "year", "religion", "sex", "residence") if c in cols]
        seen: dict[tuple, int] = {}
        popshare_groups: dict[tuple, float] = defaultdict(float)

        for i, r in enumerate(rows, start=2):
            n_rows += 1
            rid = f"row{i}"
            raw = r.get("value", "")
            if raw in ("", None):
                err(f"{mid} {rid}: blank value")
                continue
            try:
                v = float(raw)
            except ValueError:
                err(f"{mid} {rid}: non-numeric value {raw!r}")
                continue

            check_range(mid, value_kind(mid, unit.get(mid, ""), r.get("geography_level", "")), v, rid)

            lo, hi = r.get("ci_lower"), r.get("ci_upper")
            try:
                if lo not in ("", None) and float(lo) > v:
                    err(f"{mid} {rid}: ci_lower {lo} > value {v}")
                if hi not in ("", None) and float(hi) < v:
                    err(f"{mid} {rid}: ci_upper {hi} < value {v}")
            except ValueError:
                err(f"{mid} {rid}: non-numeric CI {lo!r}/{hi!r}")

            gc = r.get("geography_code", "")
            if gc and not GEO_RE.match(gc):
                warn(f"{mid} {rid}: geography_code {gc!r} off-pattern")

            key = tuple(r.get(c, "") for c in keycols)
            if key in seen:
                err(f"{mid}: duplicate key {dict(zip(keycols, key))} (rows {seen[key]} & {i})")
            else:
                seen[key] = i

            er = r.get("extraction_run", "") or ""
            if not er:
                err(f"{mid} {rid}: empty extraction_run")
            elif not STAMP_RE.search(er):
                err(f"{mid} {rid}: extraction_run is not a run-stamp (column swap?): {er[:50]!r}")

            sid = r.get("source_id", "")
            if sid and sid not in src_ids:
                err(f"{mid} {rid}: source_id {sid!r} not in sources.yaml")
            sd = r.get("source_document", "")
            if sd:
                if mid not in referenced_docs[sd]:
                    referenced_docs[sd].append(mid)

            if mid == "pop-share" and r.get("geography_level") == "national":
                rel = r.get("religion", "")
                if rel and rel != "all":
                    popshare_groups[(r.get("year", ""), r.get("residence", "all"))] += v

        for grp, total in popshare_groups.items():
            if total and not (97.0 <= total <= 101.5):
                warn(f"pop-share national {grp}: religion shares sum to {total:.1f} (want ~100)")

    for sd, users in sorted(referenced_docs.items()):
        check_provenance(sd, users)

    # ---- report ----
    print(f"Accuracy audit: {n_rows} canonical rows, {len(referenced_docs)} source_document refs")
    for k in sorted(diag):
        print(f"  DIAG  {diag[k]:>4}  {k}")
    if warns:
        print(f"\n  {len(warns)} warning(s):")
        for w in warns:
            print(f"    WARN  {w}")
    if errors:
        print(f"\n  {len(errors)} ERROR(S):")
        for e in errors:
            print(f"    ERROR {e}")
        print(f"\nFAIL: {len(errors)} accuracy error(s).")
        sys.exit(1)
    print(f"\nOK: 0 errors, {len(warns)} warning(s).")


if __name__ == "__main__":
    main()
