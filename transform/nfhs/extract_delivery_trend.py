"""
L1 -> L2 for NFHS-4 / NFHS-3 institutional delivery by religion.

  NFHS-4 FR339 p260, Table 8.13 "Place of delivery"     (India, 2015-16)
  NFHS-3 FRIND3 p257, Table 8.12 "Place of delivery"    (India, 2005-06)

Both are a single total-residence panel: a percent distribution across delivery
places, ending in a Total=100.0 column, then the headline
"Percentage delivered in a health facility" column, then Number of births. We
anchor on the literal "100.0" total column; the institutional-delivery % is the
token immediately after it.

Validated vs published national institutional delivery: NFHS-4 Total 78.9,
NFHS-3 Total 38.7.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import sys

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXTRACTOR_VERSION = "1.0.0"

ROUNDS = [
    {"round": "nfhs-4", "year": 2015, "table": "8.13", "page": 260,
     "pdf": "sources/nfhs-4/reports/india-report-fr339.pdf",
     "out": "extracted/nfhs-4/nfhs-4-table813-place-of-delivery-by-religion.csv"},
    {"round": "nfhs-3", "year": 2005, "table": "8.12", "page": 257,
     "pdf": "sources/nfhs-3/reports/india-report-frind3.pdf",
     "out": "extracted/nfhs-3/nfhs-3-table812-place-of-delivery-by-religion.csv"},
]
RELIGION_NORM = {
    "Hindu": "hindu", "Muslim": "muslim", "Christian": "christian",
    "Sikh": "sikh", "Buddhist/Neo-Buddhist": "buddhist",
}


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(path: pathlib.Path) -> dict:
    meta = json.loads(path.with_suffix(path.suffix + ".meta.json").read_text())
    if sha256_of(path) != meta["sha256"]:
        sys.exit(f"sha256 mismatch for {path.name}")
    return meta


def extract_round(cfg: dict) -> None:
    pdf_path = REPO_ROOT / cfg["pdf"]
    meta = verify(pdf_path)
    with pdfplumber.open(str(pdf_path)) as pdf:
        text = pdf.pages[cfg["page"] - 1].extract_text() or ""

    out_rows = []
    for raw, norm in RELIGION_NORM.items():
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith(raw + " "):
                continue
            toks = [t.strip("()") for t in line[len(raw):].split()]
            if "100.0" not in toks:
                continue
            inst = float(toks[toks.index("100.0") + 1])
            out_rows.append({"religion": norm, "value": inst})
            break

    seen = {r["religion"] for r in out_rows}
    missing = set(RELIGION_NORM.values()) - seen
    if missing:
        print(f"  {cfg['round']} WARN missing: {sorted(missing)}")

    extraction_run = (
        f"nfhs-delivery-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    out_path = REPO_ROOT / cfg["out"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "source_document", "source_sha256_prefix",
                    "extraction_run", "table", "page", "religion", "metric", "value"])
        for r in out_rows:
            w.writerow([cfg["round"], cfg["pdf"], meta["sha256"][:16], extraction_run,
                        cfg["table"], cfg["page"], r["religion"],
                        "institutional_delivery_pct", r["value"]])
    vals = ", ".join(f"{r['religion']}={r['value']}" for r in out_rows)
    print(f"wrote {out_path.relative_to(REPO_ROOT)} ({len(out_rows)} religions) {vals}")


if __name__ == "__main__":
    for cfg in ROUNDS:
        extract_round(cfg)
