"""
L1 -> L2 for NFHS-4 / NFHS-3 women's anaemia by religion.

  NFHS-4 FR339 p366, Table 10.21.1 "Prevalence of anaemia in women" (2015-16)
  NFHS-3 FRIND3 p359, Table 10.24.1 "Prevalence of anaemia in women" (2005-06)

Single total-residence panel. Columns per religion row:
  Mild | Moderate | Severe | Any anaemia (<12.0 g/dl) | Number of women
We take "Any anaemia" = the 4th numeric value.

NOTE: cross-round anaemia comparability is debated (blood-draw method/cut-offs).
The canonicalizer flags NFHS-4->5 (and earlier) anaemia as a methodology break,
consistent with the women-anemia metric note; the trend line is not drawn across
the break.
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
    {"round": "nfhs-4", "year": 2015, "table": "10.21.1", "page": 366,
     "pdf": "sources/nfhs-4/reports/india-report-fr339.pdf",
     "out": "extracted/nfhs-4/nfhs-4-table10211-women-anaemia-by-religion.csv"},
    {"round": "nfhs-3", "year": 2005, "table": "10.24.1", "page": 359,
     "pdf": "sources/nfhs-3/reports/india-report-frind3.pdf",
     "out": "extracted/nfhs-3/nfhs-3-table10241-women-anaemia-by-religion.csv"},
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
            # mild, moderate, severe, any, number  -> any = index 3
            if len(toks) < 5:
                continue
            any_anaemia = float(toks[3])
            out_rows.append({"religion": norm, "value": any_anaemia})
            break

    seen = {r["religion"] for r in out_rows}
    missing = set(RELIGION_NORM.values()) - seen
    if missing:
        print(f"  {cfg['round']} WARN missing: {sorted(missing)}")

    extraction_run = (
        f"nfhs-anaemia-extract-v{EXTRACTOR_VERSION}-"
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
                        cfg["table"], cfg["page"], r["religion"], "any_anaemia_pct", r["value"]])
    vals = ", ".join(f"{r['religion']}={r['value']}" for r in out_rows)
    print(f"wrote {out_path.relative_to(REPO_ROOT)} ({len(out_rows)} religions) {vals}")


if __name__ == "__main__":
    for cfg in ROUNDS:
        extract_round(cfg)
