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

  C. SHARE-LINK BIJECTION (hard, blocks CI). Every modal tab must have a unique
     share link with OG, in BOTH directions: each rendered tab (a <details
     data-view-id> inside a card section of docs/index.html) must ship a per-view
     stub at docs/m/{mid}/{vid}/ whose og:image points at /og/{mid}-{vid}.png,
     with that PNG present (and each carded metric its landing page + base OG);
     conversely no stub directory or OG image may outlive its tab. Catches the
     EW regression class, where lfpr's "Working vs looking" tab silently vanished
     while its share stub + OG image kept shipping.

Exit code is non-zero on Check A or Check C failures; Check B prints a review
list and never blocks (a value-judgement call, like check_refresh.py). Run:
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
DOCS = REPO / "docs"
SITE = "https://muslimdata.in"

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


def check_share_links() -> list[str]:
    """Check C — every rendered modal tab has its own share stub + OG image,
    and no stub/OG outlives its tab. Built docs are the SSOT (deploy ships the
    committed docs/), so this reads docs/index.html, not build.py internals."""
    idx = DOCS / "index.html"
    if not idx.exists():
        return ["docs/index.html missing — run dashboard/build.py before auditing"]
    html_text = idx.read_text()
    live_cards: set[str] = set()
    live_views: set[tuple[str, str]] = set()
    for sec in re.findall(r'<section class="card" data-metric-id="[^"]+".*?</section>',
                          html_text, re.S):
        mid = re.search(r'data-metric-id="([^"]+)"', sec).group(1)
        live_cards.add(mid)
        for vid in re.findall(r'<details data-view-id="([^"]+)"', sec):
            live_views.add((mid, vid))
    errors: list[str] = []
    # Forward: every card -> landing + base OG; every tab -> stub + og meta + PNG.
    for mid in sorted(live_cards):
        if not (DOCS / "m" / mid / "index.html").exists():
            errors.append(f"{mid}: landing page docs/m/{mid}/index.html missing")
        if not (DOCS / "og" / f"{mid}.png").exists():
            errors.append(f"{mid}: base OG image docs/og/{mid}.png missing")
    for mid, vid in sorted(live_views):
        stub = DOCS / "m" / mid / vid / "index.html"
        png = DOCS / "og" / f"{mid}-{vid}.png"
        if not stub.exists():
            errors.append(f"{mid}/{vid}: tab renders but share stub docs/m/{mid}/{vid}/ is missing")
            continue
        if not png.exists():
            errors.append(f"{mid}/{vid}: tab renders but OG image docs/og/{mid}-{vid}.png is missing")
        if f"{SITE}/og/{mid}-{vid}.png" not in stub.read_text():
            errors.append(f"{mid}/{vid}: stub og:image does not point at /og/{mid}-{vid}.png")
    # Reverse: stub dirs and OG PNGs must map to a rendered card/tab.
    for d in sorted((DOCS / "m").glob("*/")):
        mid = d.name
        if mid not in live_cards:
            errors.append(f"docs/m/{mid}/ exists but no card renders for it (decarded? git rm it)")
            continue
        for sub in sorted(d.glob("*/")):
            if (mid, sub.name) not in live_views:
                errors.append(f"docs/m/{mid}/{sub.name}/ exists but the card has no '{sub.name}' tab (stale stub)")
    expected_pngs = ({f"{mid}.png" for mid in live_cards}
                     | {f"{m}-{v}.png" for m, v in live_views}
                     | {"default.png"})
    for p in sorted((DOCS / "og").glob("*.png")):
        if p.name not in expected_pngs:
            errors.append(f"docs/og/{p.name} maps to no rendered card or tab (stale OG)")
    return errors


def main() -> None:
    data = yaml.safe_load(METRICS.read_text())
    print("Consistency audit (doc vs data):")
    errors = check_counts(data)
    warns = check_spans(data)
    share_errors = check_share_links()
    if not share_errors:
        print("  share links: every modal tab has its own stub + OG, no stale stubs ✓")

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
    if share_errors:
        print("\n  SHARE-LINK ERRORS (blocking):")
        for e in share_errors:
            print(f"    ERROR  {e}")
    if errors or share_errors:
        print(f"\nFAIL: {len(errors) + len(share_errors)} mismatch(es) — update the docs or the data.")
        sys.exit(1)

    print(f"\nOK: counts consistent; share links bijective; {len(warns)} advisory span warning(s).")


if __name__ == "__main__":
    main()
