"""
L2 -> L3 for the `mla-share` metric (Muslim share of state legislative
assembly members).

Like ls-share, this is a manual-entry metric: religion is not tabulated
in any single official publication. The underlying data is candidate
affidavits classified post-election by journalists and researchers.

Cross-source-verified values from journalistic compilations (Maktoob,
Clarion India, The India Forum, The Wire, Deccan Herald, FACTLY):

  National aggregate (~2023-24 vintage):  ~6% of all state MLAs
  State elections (most recent verified):
    West Bengal 2026:    40 of 293 seats =  13.65%
    Kerala 2026:         35 of 140 seats =  25.00%
    Maharashtra 2024:    10 of 288 seats =   3.47%
    Haryana 2024:         5 of  90 seats =   5.56%
    Madhya Pradesh 2023:  2 of 230 seats =   0.87%
    Rajasthan 2023:       6 of 200 seats =   3.00%
    Telangana 2023:       7 of 119 seats =   5.88%
    Chhattisgarh 2023:    0 of  90 seats =   0.00%

Compare against Muslim population share (~14.2% national; higher in
some states — WB ~27%, Kerala ~27%, UP ~19%, Bihar ~17%, Assam ~34%).

Coverage gap: 19+ more state assemblies (UP, Bihar, Assam, TN, Karnataka,
Gujarat, Punjab, etc.) need their own research to fill in. Documented
manual-entry metric — values are best-effort cross-verification.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "mla-share.csv"
CANONICALIZER_VERSION = "1.0.0"

# (year, geography_code, geography_level, geography_label, muslim_mlas, total_seats, cite)
ROWS = [
    (2024, "IN",     "national", "India (all-states aggregate)",  None,  None, "Across 28 state assemblies, Muslims ≈6% of seats (India Forum, Clarion India, multiple compilations)"),
    (2026, "IN-S19", "state",    "West Bengal",                   40,    293,  "The Wire, Deccan Herald (2026 WB assembly)"),
    (2026, "IN-S32", "state",    "Kerala",                        35,    140,  "The Wire (2026 Kerala assembly)"),
    (2024, "IN-S27", "state",    "Maharashtra",                   10,    288,  "LatestLY, Deccan Herald (2024 Maharashtra)"),
    (2024, "IN-S06", "state",    "Haryana",                        5,     90,  "ummid.com (2024 Haryana)"),
    (2023, "IN-S23", "state",    "Madhya Pradesh",                 2,    230,  "TimelineDaily (2023 MP)"),
    (2023, "IN-S08", "state",    "Rajasthan",                      6,    200,  "TimelineDaily (2023 Rajasthan)"),
    (2023, "IN-S36", "state",    "Telangana",                      7,    119,  "TimelineDaily (2023 Telangana)"),
    (2023, "IN-S22", "state",    "Chhattisgarh",                   0,     90,  "TimelineDaily (2023 Chhattisgarh)"),
]
NATIONAL_AGGREGATE_VALUE = 6.0  # ~6% across all state assemblies


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-mla-share-v{CANONICALIZER_VERSION}-"
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
        for year, code, level, label, m_mlas, total, cite in ROWS:
            if m_mlas is None:
                # National aggregate — use hardcoded value, no count
                share = NATIONAL_AGGREGATE_VALUE
                denom = "all_state_assembly_seats (aggregate ~6% across 28 assemblies)"
            else:
                share = round(m_mlas / total * 100, 2)
                denom = f"assembly_seats ({m_mlas}/{total} Muslim MLAs / total seats)"
            w.writerow([
                "mla-share", level, code, year, "muslim",
                share, denom, "", "", "",
                "prs-eci-affidavits",
                "MANUAL: cross-verified journalistic aggregation of ECI affidavit data",
                extraction_run,
                (f"{label}, {year}. {cite}. Religion is derived from ECI candidate "
                 f"affidavits; manual entry with cross-source verification. Coverage gap: "
                 f"~19 more state assemblies need their own research."),
                "false",
            ])
            n_rows += 1

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({n_rows} rows)")
    for year, code, level, label, m_mlas, total, _ in ROWS:
        share = (m_mlas / total * 100) if m_mlas is not None else NATIONAL_AGGREGATE_VALUE
        suffix = f" ({m_mlas}/{total})" if m_mlas is not None else " (aggregate)"
        print(f"  {year} {label}: {share:.2f}%{suffix}")


if __name__ == "__main__":
    canonicalize()
