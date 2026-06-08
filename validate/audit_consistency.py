"""
Consistency audit — automates the doc-vs-data drift class we cleaned by hand in
Commits DF/DI (definitions saying "2020-2022" when the data was 2015-2023;
README saying "30 assemblies" when there were 31). Two checks:

  A. METRIC-COUNT CONSISTENCY (hard, blocks CI). Hardcoded counts in README.md
     ("21 live indicators", "23 canonical metrics", "16 source-ids feed L3",
     "16 primary sources") must match the canonical truth — the number of carded
     metrics, canonical CSVs, and L3-feeding source-ids. Catches "added/removed a
     metric but the docs still say the old number".

  B. DEFINITION SPAN vs DATA (soft, advisory punch-list). For each carded metric,
     if its definition/methodology prose names any years, the canonical data must
     not extend beyond them. Fires only when the data is WIDER than every year the
     prose names (data runs later than the latest year mentioned, or earlier than
     the earliest) — the "data advanced, docs lagged" signal. Legitimate
     sub-period mentions (e.g. "the 1980-89 era") don't trip it, because the prose
     still also names the span's endpoints.

Exit code is non-zero ONLY on Check A failures; Check B prints a review list and
never blocks (a value-judgement call, like check_refresh.py). Run:
    python validate/audit_consistency.py
"""
from __future__ import annotations

import csv
import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
CANON = REPO / "canonical"
METRICS = REPO / "manifest" / "metrics.yaml"
README = REPO / "README.md"

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def _carded(data: dict) -> list[dict]:
    return [
        m for m in data["metrics"]
        if (d := m.get("display", {}).get("scorecard")) and d.get("include", True) is not False
    ]


def _prose_years(text: str) -> set[int]:
    """All full years named in prose, expanding abbreviated survey ranges like
    "2019-21" (NFHS), "2023-24" (PLFS), "2004-05" (Sachar) to both endpoints so
    a midpoint-labelled data year inside the round doesn't look like drift."""
    years = {int(y) for y in YEAR_RE.findall(text)}
    for m in re.finditer(r"\b(19\d{2}|20\d{2})\s*[-/–]\s*(\d{2})\b", text):
        start, suf = int(m.group(1)), int(m.group(2))
        end = (start // 100) * 100 + suf
        if end < start:
            end += 100
        years.add(start)
        years.add(end)
    return years


def _canonical_years(mid: str) -> list[int]:
    p = CANON / f"{mid}.csv"
    if not p.exists():
        return []
    with p.open() as f:
        return sorted({
            int(r["year"]) for r in csv.DictReader(f)
            if str(r.get("year", "")).strip().isdigit()
        })


def check_counts(data: dict) -> list[str]:
    """Check A — hardcoded README counts vs canonical truth. Returns errors."""
    n_carded = len(_carded(data))
    n_canon = len(list(CANON.glob("*.csv")))
    feeding: set[str] = set()
    for p in CANON.glob("*.csv"):
        with p.open() as f:
            for row in csv.DictReader(f):
                if row.get("source_id"):
                    feeding.add(row["source_id"])
    n_sources = len(feeding)
    print(f"  truth: carded={n_carded}, canonical CSVs={n_canon}, L3-feeding sources={n_sources}")

    # Negative lookbehind keeps "L3 canonical metric" (the layer notation) from
    # matching as "3 canonical metrics".
    rules = [
        ("carded metrics", n_carded, [r"(?<![A-Za-z0-9])(\d+)\s+carded", r"(?<![A-Za-z0-9])(\d+)\s+live indicators?"]),
        ("canonical CSVs", n_canon, [r"(?<![A-Za-z0-9])(\d+)\s+canonical (?:metrics|CSVs)"]),
        ("L3-feeding sources", n_sources, [r"(?<![A-Za-z0-9])(\d+)\s+source-ids feed", r"(?<![A-Za-z0-9])(\d+)\s+primary sources"]),
    ]
    text = README.read_text() if README.exists() else ""
    errors: list[str] = []
    for label, val, patterns in rules:
        for pat in patterns:
            for m in re.finditer(pat, text):
                got = int(m.group(1))
                if got != val:
                    errors.append(f"README says \"{m.group(0)}\" but actual {label} = {val}")
    return errors


def check_spans(data: dict) -> list[str]:
    """Check B — prose year coverage vs canonical span. Returns advisory warns."""
    warns: list[str] = []
    for m in _carded(data):
        mid = m["id"]
        years = _canonical_years(mid)
        if not years:
            continue
        dmin, dmax = years[0], years[-1]
        prose = (m.get("definition") or "") + " " + (m.get("methodology_notes") or "")
        pyears = _prose_years(prose)
        if not pyears:
            continue
        if dmax > max(pyears):
            warns.append(f"{mid}: data runs to {dmax} but prose's latest year is {max(pyears)} (docs may lag)")
        if dmin < min(pyears):
            warns.append(f"{mid}: data starts {dmin} but prose's earliest year is {min(pyears)} (prose understates history)")
    return warns


def main() -> None:
    data = yaml.safe_load(METRICS.read_text())
    print("Consistency audit (doc vs data):")
    errors = check_counts(data)
    warns = check_spans(data)

    if warns:
        print("\n  Span punch-list (ADVISORY — review; some may be legitimate sub-periods):")
        for w in warns:
            print(f"    WARN  {w}")
    else:
        print("  spans: every carded metric's prose covers its data range ✓")

    if errors:
        print("\n  COUNT ERRORS (blocking):")
        for e in errors:
            print(f"    ERROR  {e}")
        print(f"\nFAIL: {len(errors)} count mismatch(es) — update the docs or the data.")
        sys.exit(1)

    print(f"\nOK: counts consistent; {len(warns)} advisory span warning(s).")


if __name__ == "__main__":
    main()
