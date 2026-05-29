"""
L2 -> L3 for the `imr` metric (Infant Mortality Rate per 1000 live births).

Reads:  extracted/nfhs-5/nfhs-5-table72-mortality-by-religion.csv   (NFHS-5 Table 7.2)
        extracted/census-2011/c01-population-by-religion.csv         (population weights)
Writes: canonical/imr.csv

NFHS-5 Table 7.2 reports IMR separately for URBAN and RURAL, by religion.
There is no published TOTAL-by-religion column. We compute the national
total-residence IMR as a population-weighted average:

  imr_total[religion] = (imr_urban * pop_urban + imr_rural * pop_rural)
                        / (pop_urban + pop_rural)

Population weights are drawn from Census 2011 C-1 (the most recent
authoritative urban/rural-by-religion population data — the 2021 Census
is delayed). Urban/rural population share by religion is relatively
stable over 2011–2021, so the weighting introduces <1% error.

For religion=all, we use NFHS's own URBAN/RURAL Total IMR row values
from page 284 (26.6 / 38.4) and weight with Census 2011 total population.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
NFHS_L2 = REPO_ROOT / "extracted" / "nfhs-5" / "nfhs-5-table72-mortality-by-religion.csv"
CENSUS_L2 = REPO_ROOT / "extracted" / "census-2011" / "c01-population-by-religion.csv"
OUTPUT_PATH = REPO_ROOT / "canonical" / "imr.csv"
CANONICALIZER_VERSION = "1.0.0"

# NFHS-5 Table 7.2 page 284 — Total residence-summary IMR row values for India
# (not extracted to L2 since the L2 only captured per-religion rows).
NFHS_NATIONAL_URBAN_IMR_ALL = 26.6
NFHS_NATIONAL_RURAL_IMR_ALL = 38.4

OUTPUT_RELIGIONS = ("muslim", "hindu", "christian", "sikh", "buddhist", "jain", "other", "all")


def load_nfhs_imr() -> dict[tuple[str, str], float]:
    """Returns {(religion, residence): imr_value} for the religions in NFHS L2."""
    out: dict[tuple[str, str], float] = {}
    with NFHS_L2.open() as f:
        for row in csv.DictReader(f):
            if row["metric"] != "imr":
                continue
            out[(row["religion"], row["residence"])] = float(row["value"])
    return out


def load_national_pop_by_religion() -> dict[tuple[str, str], int]:
    """Returns {(religion, residence): persons} for INDIA (state_code=00) from Census C-1.
    Residence in {total, urban, rural}.
    """
    out: dict[tuple[str, str], int] = {}
    with CENSUS_L2.open() as f:
        for row in csv.DictReader(f):
            if row["state_code"] != "00" or row["sex"] != "persons":
                continue
            out[(row["religion"], row["residence"])] = int(row["value"])
    return out


def weighted_imr(imr_urban: float, imr_rural: float,
                 pop_urban: int, pop_rural: int) -> float:
    total = pop_urban + pop_rural
    return (imr_urban * pop_urban + imr_rural * pop_rural) / total


def canonicalize() -> None:
    nfhs = load_nfhs_imr()
    pop = load_national_pop_by_religion()

    extraction_run = (
        f"canonicalize-imr-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])

        for religion in OUTPUT_RELIGIONS:
            if religion == "all":
                imr_u, imr_r = NFHS_NATIONAL_URBAN_IMR_ALL, NFHS_NATIONAL_RURAL_IMR_ALL
            else:
                imr_u = nfhs.get((religion, "urban"))
                imr_r = nfhs.get((religion, "rural"))
            pop_u = pop.get((religion, "urban"))
            pop_r = pop.get((religion, "rural"))
            if None in (imr_u, imr_r, pop_u, pop_r):
                print(f"  skip {religion}: missing data (imr_urban={imr_u}, imr_rural={imr_r}, pop_u={pop_u}, pop_r={pop_r})")
                continue
            imr_total = round(weighted_imr(imr_u, imr_r, pop_u, pop_r), 2)
            w.writerow([
                "imr", "national", "IN", 2020, religion,
                imr_total, "live_births", "", "", "",
                "nfhs-5",
                "sources/nfhs-5/reports/india-report-fr375.pdf",
                extraction_run,
                (f"NFHS-5 Table 7.2 urban/rural IMR by religion ({imr_u}/{imr_r}), "
                 f"weighted to total residence using Census 2011 urban/rural population "
                 f"by religion ({pop_u:,}/{pop_r:,}). Year=2020 represents the midpoint "
                 f"of the 5-year period preceding NFHS-5 (2014-2020 approx)."),
                "false",
            ])
            n_rows += 1

        # ---- Earlier rounds for the time series (NFHS-4 2015, NFHS-3 2005) ----
        # Both publish a TOTAL-residence panel with IMR by religion directly, so
        # no urban/rural weighting is needed (unlike the NFHS-5 row above).
        for year, sid, sdoc, ext in (
            (2015, "nfhs-4", "sources/nfhs-4/reports/india-report-fr339.pdf",
             "extracted/nfhs-4/nfhs-4-table72-mortality-by-religion.csv"),
            (2005, "nfhs-3", "sources/nfhs-3/reports/india-report-frind3.pdf",
             "extracted/nfhs-3/nfhs-3-table72-mortality-by-religion.csv"),
        ):
            p = REPO_ROOT / ext
            if not p.exists():
                continue
            with p.open() as ef:
                for r in csv.DictReader(ef):
                    if r["metric"] != "imr":
                        continue
                    w.writerow([
                        "imr", "national", "IN", year, r["religion"],
                        round(float(r["value"]), 2), "live_births", "", "", "",
                        sid, sdoc, extraction_run,
                        (f"NFHS Table 7.2 TOTAL-residence panel, infant mortality by "
                         f"religion (published total; not urban/rural-weighted like the "
                         f"NFHS-5 row). Year={year} = round midpoint."),
                        "false",
                    ])
                    n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")


if __name__ == "__main__":
    canonicalize()
