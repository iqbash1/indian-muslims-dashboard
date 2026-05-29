"""
L1 -> L2 for NFHS-4 and NFHS-3 Table 7.2 (Early childhood mortality by
background characteristics) — the TOTAL-residence panel.

Unlike NFHS-5 (which published only URBAN/RURAL by religion, requiring a
population-weighted total — see extract_table72.py + imr.py), NFHS-4 and NFHS-3
both print a TOTAL panel with mortality-by-religion directly:

  NFHS-4 FR339 p225 (panel "TOTAL")      → Muslim IMR 40.0, Hindu 41.6, Total 40.7
  NFHS-3 FRIND3 p231 (panel "TOTAL")     → Muslim IMR 52.4, Hindu 58.5, Total 57.0

Both panels match the published national IMR (40.7 / 57), confirming the right
panel is read. Each religion row is: <name> NN PNN IMR(1q0) child(4q1) u5(5q0).
We anchor on the standalone "TOTAL" section header, then read the Religion
sub-block (Hindu/Muslim/Christian/Sikh/Buddhist) until the Caste/tribe block.
The religion-block "Other" is skipped (collides with caste "Other"; not a named
community we rank anyway).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXTRACTOR_VERSION = "1.0.0"

ROUNDS = [
    {
        "round": "nfhs-4", "year": 2015, "table": "7.2",
        "pdf": "sources/nfhs-4/reports/india-report-fr339.pdf",
        "page": 225,
        "out": "extracted/nfhs-4/nfhs-4-table72-mortality-by-religion.csv",
    },
    {
        "round": "nfhs-3", "year": 2005, "table": "7.2",
        "pdf": "sources/nfhs-3/reports/india-report-frind3.pdf",
        "page": 231,
        "out": "extracted/nfhs-3/nfhs-3-table72-mortality-by-religion.csv",
    },
    {
        # NFHS-2 Table 6.4, TOTAL panel (p217; URBAN panel is p216). Same column
        # layout (NN PNN Infant Child U5); rates for the 10-year period preceding.
        "round": "nfhs-2", "year": 1998, "table": "6.4",
        "pdf": "sources/nfhs-2/reports/india-report-frind2.pdf",
        "page": 217,
        "out": "extracted/nfhs-2/nfhs-2-table64-mortality-by-religion.csv",
    },
]

RELIGION_NORM = {
    "Hindu": "hindu", "Muslim": "muslim", "Christian": "christian",
    "Sikh": "sikh", "Buddhist/Neo-Buddhist": "buddhist",
}
METRIC_COLS = ["nn", "pnn", "imr", "child_4q1", "u5_5q0"]
NUM = r"\(?-?\d+(?:\.\d+)?\)?"


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


def parse_value(s: str) -> tuple[float, bool]:
    small = s.startswith("(") and s.endswith(")")
    return float(s.strip("()")), small


def extract_round(cfg: dict) -> None:
    pdf_path = REPO_ROOT / cfg["pdf"]
    meta = verify(pdf_path)
    with pdfplumber.open(str(pdf_path)) as pdf:
        text = pdf.pages[cfg["page"] - 1].extract_text() or ""
    lines = [ln.strip() for ln in text.splitlines()]

    # Anchor on the standalone TOTAL section header; read religion rows after it.
    try:
        start = next(i for i, ln in enumerate(lines) if ln == "TOTAL")
    except StopIteration:
        sys.exit(f"{cfg['round']}: no standalone 'TOTAL' panel header on page {cfg['page']}")

    rows: list[dict] = []
    seen: set[str] = set()
    for ln in lines[start + 1:]:
        if ln.startswith("Caste") and seen:
            break  # left the Religion sub-block
        for raw, norm in RELIGION_NORM.items():
            if norm in seen:
                continue
            m = re.match(rf"^{re.escape(raw)}\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})\s+({NUM})$", ln)
            if not m:
                continue
            for col, g in zip(METRIC_COLS, m.groups()):
                val, small = parse_value(g)
                rows.append({"religion": norm, "metric": col, "value": val, "small": small})
            seen.add(norm)
            break

    missing = set(RELIGION_NORM.values()) - seen
    if missing:
        print(f"  {cfg['round']} WARN missing religions: {sorted(missing)}")

    extraction_run = (
        f"nfhs-table72-total-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    out_path = REPO_ROOT / cfg["out"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table", "page", "religion", "residence", "metric", "value", "small_sample",
        ])
        for r in rows:
            w.writerow([
                cfg["round"], cfg["pdf"], meta["sha256"][:16], extraction_run,
                cfg.get("table", "7.2"), cfg["page"], r["religion"], "total", r["metric"], r["value"],
                "true" if r["small"] else "false",
            ])
    imr = {r["religion"]: r["value"] for r in rows if r["metric"] == "imr"}
    print(f"wrote {out_path.relative_to(REPO_ROOT)} ({len(rows)} rows; {len(seen)}/5 religions) "
          f"IMR: " + ", ".join(f"{k}={v}" for k, v in imr.items()))


if __name__ == "__main__":
    for cfg in ROUNDS:
        extract_round(cfg)
