"""
Prose-number consistency audit - the layer that keeps HARDCODED numbers in
authored prose matching the COMPUTED canonical values the dashboard renders.

validate.py checks schema; audit_consistency.py checks doc-vs-data drift
(metric counts, year spans, share-link bijection); audit_accuracy.py checks
value plausibility + provenance. NONE of them check whether a figure typed into
a sentence still matches canonical. Every chart, hero, pill, status badge and
by-state/sex/residence table is recomputed from canonical on each build, so
those can't drift; the prose around them can. This gate closes that gap.

Reads manifest/prose_checks.yaml (the declarative registry) and runs three
check classes against canonical:

  ANCHORED (hard)
    A registered canonical cell (metric + religion [+ sex/residence], latest
    year) must have a matching figure in the named authored prose field.
    Percents/rates/ratios match any number within a unit-aware tolerance (so
    "about 69%" satisfies a 68.6 canonical value); INR matches the Indian-money
    string the dashboard renders ("INR 9,249" / "15.0 lakh"); counts match the
    grouped integer. A field whose canonical value has NO nearby number is the
    drift the 2026-06 audit caught (lfpr "36%" women vs canonical 30.2%).

  CROSS_SURFACE (hard)
    A figure hardcoded in several files (e.g. ger-higher-ed "14.5%" across
    narratives.yaml, metrics.yaml, CLAUDE.md and two runbooks) must appear in
    every one - the "keep N places in sync" tripwire.

  INTERNAL_MATH (hard)
    A derived literal recomputed from canonical: ls-share parity seats
    (round(pop_share/100 * house)) and the school-edu-spend INR-100 ratio.

Exit non-zero on any ERROR. Run:  python validate/audit_prose_numbers.py
"""
from __future__ import annotations

import csv
import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
CANON = REPO / "canonical"

NM_RE = re.compile(r"\((\d+)\s*/\s*(\d+)")          # "(24/543" in ls denominators
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")          # 9,249 / 68.6 / 272 / 1,000
MUSLIM_POP_SHARE = 14.23                            # build.py constant (Census 2011)

errors: list[str] = []
warns: list[str] = []


def err(m: str) -> None:
    errors.append(m)


def warn(m: str) -> None:
    warns.append(m)


# ---- formatting helpers (verbatim from build.py, so matches rendered text) ----
def _round_str(v: float, dp: int = 1) -> str:
    from decimal import Decimal, ROUND_HALF_UP
    d = Decimal(str(round(float(v), 9)))
    return str(d.quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP))


def _in_group(n: int) -> str:
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + s


def _inr_str(v: float) -> str:
    a = abs(v); sign = "-" if v < 0 else ""
    if a >= 1e7:
        return f"{sign}INR {a/1e7:.1f} crore"
    if a >= 1e5:
        return f"{sign}INR {a/1e5:.1f} lakh"
    return f"{sign}INR {_in_group(round(a))}"


# ---- manifests ----
_metrics = yaml.safe_load((REPO / "manifest" / "metrics.yaml").read_text())
UNIT = {m["id"]: m.get("unit") for m in _metrics["metrics"]}
_narr_doc = yaml.safe_load((REPO / "manifest" / "narratives.yaml").read_text())
NARR = _narr_doc.get("narratives", _narr_doc)
REG = yaml.safe_load((REPO / "manifest" / "prose_checks.yaml").read_text())
DEF = REG.get("defaults", {})

INR_UNITS = {"inr", "inr_per_month", "inr_per_year"}


# ---- canonical access (same load path as build.py: national, latest year) ----
def _rows(metric: str) -> list[dict]:
    p = CANON / f"{metric}.csv"
    if not p.exists():
        return []
    out = []
    with p.open() as f:
        for r in csv.DictReader(f):
            r["sex"] = r.get("sex") or "all"
            r["residence"] = r.get("residence") or "all"
            out.append(r)
    return out


def value_at(metric: str, religion: str, sex: str = "all", residence: str = "all"):
    """Latest-year national value for a (religion, sex, residence) cell."""
    rows = [r for r in _rows(metric)
            if r["geography_level"] == "national" and r["religion"] == religion
            and r["sex"] == sex and r["residence"] == residence]
    if not rows:
        return None
    latest = max(int(r["year"]) for r in rows)
    for r in rows:
        if int(r["year"]) == latest:
            try:
                return float(r["value"])
            except (TypeError, ValueError):
                return None
    return None


def ls_house() -> int | None:
    seats = []
    for r in _rows("ls-share"):
        if r["geography_level"] != "national":
            continue
        m = NM_RE.search(r.get("denominator") or "")
        if m:
            seats.append((int(r["year"]), int(m.group(2))))
    return max(seats)[1] if seats else None


def nums(text: str) -> list[float]:
    return [float(t.replace(",", "")) for t in NUM_RE.findall(text)]


def field_text(metric: str, field: str) -> str | None:
    n = NARR.get(metric)
    if not isinstance(n, dict):
        return None
    v = n.get(field)
    return v if isinstance(v, str) else None


def tol_for(unit: str) -> float:
    if unit == "percent":
        return DEF.get("tol_percent", 0.6)
    if unit == "females_per_1000_males":
        return DEF.get("tol_ratio", 1.5)
    if unit == "count":
        return DEF.get("tol_count", 0.5)
    return DEF.get("tol_rate", 0.6)        # per_1000_live_births, rate_per_100k, years


# ---- check classes -------------------------------------------------------
def check_anchored() -> None:
    for c in REG.get("anchored", []):
        mid, field = c["metric"], c["field"]
        rel = c["religion"]
        sex, res = c.get("sex", "all"), c.get("residence", "all")
        coord = f"{mid}.{field}[{rel}" + (f",{sex}" if sex != "all" else "") + \
                (f",{res}" if res != "all" else "") + "]"
        val = value_at(mid, rel, sex, res)
        if val is None:
            err(f"ANCHORED {coord}: no canonical row to check against")
            continue
        txt = field_text(mid, field)
        if txt is None:
            err(f"ANCHORED {coord}: narratives.{mid}.{field} missing")
            continue
        unit = UNIT.get(mid, "")
        if unit in INR_UNITS:
            core = _inr_str(val)[4:]               # strip "INR "
            if core not in txt:
                err(f"ANCHORED {coord}: canonical {_inr_str(val)} "
                    f"('{core}') not found in {field}")
        else:
            tol = tol_for(unit)
            if not any(abs(n - val) <= tol for n in nums(txt)):
                shown = _round_str(val, 0 if unit in
                                   ("count", "females_per_1000_males") else 1)
                err(f"ANCHORED {coord}: canonical {shown} (+/-{tol}) "
                    f"not matched by any number in {field}")


def check_cross_surface() -> None:
    for c in REG.get("cross_surface", []):
        label = c["label"]
        texts = {}
        for rel in c["files"]:
            p = REPO / rel
            if not p.exists():
                err(f"CROSS_SURFACE {label}: file {rel} missing")
                continue
            texts[rel] = p.read_text()
        for s in c["strings"]:
            for rel, t in texts.items():
                if s not in t:
                    err(f"CROSS_SURFACE {label}: '{s}' absent from {rel}")


def check_internal_math() -> None:
    for c in REG.get("internal_math", []):
        kind = c["kind"]
        if kind == "ls_parity":
            house = ls_house()
            if not house:
                err(f"INTERNAL_MATH {c['label']}: no ls-share house size in canonical")
                continue
            parity = round(MUSLIM_POP_SHARE / 100 * house)
            pat = re.compile(rf"\b{parity}\b\s*(?:seats|Muslim MPs)")
            for rel in c["expect_in"]:
                t = (REPO / rel).read_text()
                if not pat.search(t):
                    err(f"INTERNAL_MATH {c['label']}: computed parity {parity} seats "
                        f"(={MUSLIM_POP_SHARE}% of {house}) not stated in {rel}")
        elif kind == "ratio_of_latest":
            mid = c["metric"]
            m, h = value_at(mid, "muslim"), value_at(mid, "hindu")
            if not m or not h:
                err(f"INTERNAL_MATH {c['label']}: missing canonical muslim/hindu for {mid}")
                continue
            r = round(m / h * 100)
            for rel in c["expect_in"]:
                t = (REPO / rel).read_text()
                if "INR 100" not in t or f"INR {r}" not in t:
                    err(f"INTERNAL_MATH {c['label']}: expected 'INR 100 ... INR {r}' "
                        f"(ratio {m:.0f}/{h:.0f}) in {rel}")
        else:
            warn(f"INTERNAL_MATH {c.get('label')}: unknown kind '{kind}', skipped")


def main() -> None:
    check_anchored()
    check_cross_surface()
    check_internal_math()

    n_anchored = len(REG.get("anchored", []))
    covered = {c["metric"] for c in REG.get("anchored", [])}
    carded = [m["id"] for m in _metrics["metrics"]
              if m.get("phase") and m.get("status") != "decarded"]
    # advisory: carded metrics with a narrative but no anchored figure check
    uncovered = sorted(m for m in NARR
                       if isinstance(NARR.get(m), dict) and m not in covered)

    print(f"prose-number audit: {n_anchored} anchored, "
          f"{len(REG.get('cross_surface', []))} cross-surface, "
          f"{len(REG.get('internal_math', []))} internal-math checks")
    if uncovered:
        print("  advisory: narratives without an anchored figure check: "
              + ", ".join(uncovered))
    for w in warns:
        print(f"  WARN  {w}")
    if errors:
        print(f"\nFAIL: {len(errors)} prose-number mismatch(es)")
        for e in errors:
            print(f"  ERROR {e}")
        sys.exit(1)
    print("OK: all hardcoded prose figures match canonical")


if __name__ == "__main__":
    main()
