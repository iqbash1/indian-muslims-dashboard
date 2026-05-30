"""
L1 -> L2 for NFHS-5 Table 10.1 (Nutritional status of children by background).

Reads:  sources/nfhs-5/reports/india-report-fr375.pdf (PDF page 424)
Writes: extracted/nfhs-5/nfhs-5-table101-stunting-by-religion.csv

The table is printed in LANDSCAPE orientation on a portrait PDF page, so its
text reads bottom-to-top. We rotate just that one page +90° via the system
`qpdf` tool into a temporary PDF, then pdfplumber reads it upright. (qpdf is
the standard PDF-manipulation CLI; pdfplumber's Page has no rotate method.)

Each religion row carries 14 numeric values across three anthropometric
indices — height-for-age (HFA, 4 cols), weight-for-height (WFH, 5 cols), and
weight-for-age (WFA, 5 cols). For STUNTING we want HFA col 2: "Percentage
below -2 SD" of the WHO Child Growth Standards median. The 4th value (number
of children with valid HFA) is the sample size we carry to the canonicalizer.

Row shape: <religion> <pct_below_-3_SD> <stunting%> <mean_z> <N> + 10 more.

Validated: weighted average of religion rows = 35.47% ≈ published all-India
35.5% stunting (NFHS-5). Religion column does NOT include an "Other" row in
NFHS-5 Table 10.1 (6 religions: Hindu, Muslim, Christian, Sikh, Buddhist, Jain).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import pdfplumber

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_PATH = REPO_ROOT / "sources" / "nfhs-5" / "reports" / "india-report-fr375.pdf"
OUTPUT_PATH = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table101-stunting-by-religion.csv"
TABLE_PAGE = 424  # 1-based PDF page
EXTRACTOR_VERSION = "1.0.0"

RELIGIONS = [
    ("Hindu", "hindu"),
    ("Muslim", "muslim"),
    ("Christian", "christian"),
    ("Sikh", "sikh"),
    ("Buddhist/Neo-Buddhist", "buddhist"),
    ("Jain", "jain"),
]

# religion + 14 numbers (mix of percentages with decimals, Z-scores possibly
# negative, and N values with commas).
NUM = r"-?\d+(?:[.,]\d+)?"
RELIGION_ROW = re.compile(
    r"^\s*(Hindu|Muslim|Christian|Sikh|Buddhist/Neo-Buddhist|Jain)\s+"
    + r"\s+".join(f"({NUM})" for _ in range(14))
    + r"\s*$"
)


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source_integrity() -> dict:
    meta = json.loads(SOURCE_PATH.with_suffix(SOURCE_PATH.suffix + ".meta.json").read_text())
    actual = sha256_of(SOURCE_PATH)
    if actual != meta["sha256"]:
        sys.exit(
            f"sha256 mismatch for {SOURCE_PATH.name}: "
            f"archive {actual[:16]} != sidecar {meta['sha256'][:16]}"
        )
    return meta


def rotate_page(src: pathlib.Path, page: int, out: pathlib.Path) -> None:
    """Rotate one page of `src` by +90° via qpdf into `out`. Verifies qpdf exists."""
    if not _has_qpdf():
        sys.exit("qpdf not found on PATH. Install via Homebrew: brew install qpdf")
    subprocess.run(
        ["qpdf", f"--rotate=+90:{page}", str(src), str(out)],
        check=True,
    )


def _has_qpdf() -> bool:
    try:
        subprocess.run(["qpdf", "--version"], check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def num(s: str) -> float:
    return float(s.replace(",", ""))


def extract() -> None:
    meta = verify_source_integrity()
    extraction_run = (
        f"nfhs-5-table101-extract-v{EXTRACTOR_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        rotated_path = pathlib.Path(tmp.name)
    try:
        rotate_page(SOURCE_PATH, TABLE_PAGE, rotated_path)
        with pdfplumber.open(str(rotated_path)) as pdf:
            text = pdf.pages[TABLE_PAGE - 1].extract_text() or ""
    finally:
        rotated_path.unlink(missing_ok=True)

    rows: list[dict] = []
    for line in text.splitlines():
        m = RELIGION_ROW.match(line.strip())
        if not m:
            continue
        display_name = m.group(1)
        canon = dict(RELIGIONS)[display_name]
        vals = [num(m.group(2 + i)) for i in range(14)]
        # HFA: cols 1-4 (below -3 SD, below -2 SD = STUNTING, mean Z, N)
        stunting_pct = vals[1]      # % below -2 SD HFA = stunted
        severe_pct = vals[0]        # % below -3 SD HFA = severely stunted
        mean_hfa_z = vals[2]
        n_children = int(vals[3])   # N with valid HFA
        rows.append({
            "religion": canon, "display_name": display_name,
            "stunting_pct": stunting_pct, "severe_stunting_pct": severe_pct,
            "mean_hfa_z": mean_hfa_z, "n_children": n_children,
        })

    if not rows:
        sys.exit("no religion rows parsed from Table 10.1 — extraction failed")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "source_id", "source_document", "source_sha256_prefix", "extraction_run",
            "table_id", "page", "religion", "display_name",
            "stunting_pct", "severe_stunting_pct", "mean_hfa_z_score", "n_children",
        ])
        for r in rows:
            w.writerow([
                "nfhs-5", str(SOURCE_PATH.relative_to(REPO_ROOT)),
                meta["sha256"][:16], extraction_run,
                "10.1", TABLE_PAGE,
                r["religion"], r["display_name"],
                r["stunting_pct"], r["severe_stunting_pct"],
                r["mean_hfa_z"], r["n_children"],
            ])
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} religions)")
    for r in rows:
        print(f"  {r['religion']:10s} stunting={r['stunting_pct']:5.1f}%  N={r['n_children']:>7,}")


if __name__ == "__main__":
    extract()
