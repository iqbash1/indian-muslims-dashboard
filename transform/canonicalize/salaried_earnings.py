"""
L2 -> L3 for the `salaried-earnings` metric.

Reads:  extracted/plfs/plfs-earnings-2017-24-by-religion.csv  (all 7 rounds)
Writes: canonical/salaried-earnings.csv

Average gross monthly earnings (preceding calendar month, nominal Rs) of
regular wage/salaried employees age 15+, by religion. The published PLFS
reports never break earnings down by religion, so ALL seven points come from
the unit-level microdata (source plfs-microdata; extraction
transform/plfs/extract_earnings_by_religion.py). That extraction's validation
gates reproduce the published all-ages earnings tables of the 2021-22, 2022-23
and 2023-24 reports across all 27 cells to within 0.03% with exactly matching
sample counts, so the religion split rides on a fully anchored estimator.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

from _plfs_microdata import ZIP

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
L2_PATH = REPO_ROOT / "extracted" / "plfs" / "plfs-earnings-2017-24-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "salaried-earnings.csv"
CANONICALIZER_VERSION = "1.0.0"

COLS = ["metric_id", "geography_level", "geography_code", "year", "religion",
        "sex", "residence", "value", "denominator", "sample_size", "ci_lower",
        "ci_upper", "source_id", "source_document", "extraction_run",
        "methodology_note", "break_flag"]

RELIGIONS = ("muslim", "hindu", "christian", "sikh", "all")
RES_WORD = {"all": "rural+urban", "urban": "urban", "rural": "rural"}
SEX_WORD = {"all": "both sexes", "male": "males", "female": "females"}


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-salaried-earnings-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    rows = []
    with L2_PATH.open() as f:
        for r in csv.DictReader(f):
            if r["religion"] not in RELIGIONS:
                continue
            rnd = r["round"]
            year = int(r["year"])
            note = (
                f"Computed from PLFS {rnd} unit-level microdata: average gross "
                f"earnings during the preceding calendar month from the regular "
                f"salaried/wage activity (schedule block 6 item 9, asked of "
                f"persons with current weekly status 31/71/72), age 15+, "
                f"{RES_WORD[r['residence']]}, {SEX_WORD[r['sex']]}, weighted by "
                f"the official annual first-visit weight; household religion "
                f"joined from the household file. The published reports never "
                f"break earnings down by religion; the same estimator reproduces "
                f"the published all-ages earnings tables (2021-22 to 2023-24 "
                f"reports) across all 27 cells within 0.03% with exactly "
                f"matching sample counts. Nominal rupees (levels reflect "
                f"inflation; the comparable story is the relative gap - Muslim "
                f"earnings run 16-23% below the all-India average in every "
                f"round). NSO unit-data rider: religion is self-reported; no "
                f"sub-state estimates. Pulled via the MoSPI NADA API; zip "
                f"sha256 in sources/nada/plfs-{rnd}/. Year={year} is the start "
                f"of the Jul-{year} to Jun-{year+1} reference period."
            )
            rows.append({
                "metric_id": "salaried-earnings", "geography_level": "national",
                "geography_code": "IN", "year": year, "religion": r["religion"],
                "sex": r["sex"], "residence": r["residence"],
                "value": round(float(r["avg_monthly_earnings_rs"])),
                "denominator": "regular_salaried_employees_15plus",
                "sample_size": r["n_workers"], "ci_lower": "", "ci_upper": "",
                "source_id": "plfs-microdata",
                "source_document": f"sources/nada/plfs-{rnd}/{ZIP[rnd]}",
                "extraction_run": extraction_run,
                "methodology_note": note, "break_flag": "false",
            })
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(rows)} rows)")
    for r in rows:
        if r["sex"] == "all" and r["residence"] == "all" and r["religion"] in ("muslim", "all"):
            print(f"  {r['year']} {r['religion']:7s}: Rs {r['value']:,}")


if __name__ == "__main__":
    canonicalize()
