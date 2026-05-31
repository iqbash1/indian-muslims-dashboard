"""
L2 -> L3 for the `mla-share` metric (Muslim share of state legislative
assembly members).

Like ls-share, this is a manual-entry metric: religion is not tabulated
in any single official publication. The underlying data is candidate
affidavits classified post-election by journalists and researchers.

Cross-source-verified values from journalistic compilations (Maktoob,
Clarion India, The India Forum, The Wire, Deccan Herald, FACTLY, Outlook,
Radiance Weekly, Free Press Journal, ummid.com, thenewzradar):

  National aggregate (~2023-24 vintage):  ~6% of all state MLAs
  Compare against Muslim population share (~14.2% national; higher in
  some states — WB ~27%, Kerala ~27%, UP ~19%, Bihar ~17%, J&K ~68%).

Coverage as of Commit AG: 30 of 31 state/UT assemblies (all 28 states +
Delhi/Puducherry/J&K UTs). Most recent election per assembly tracked.
J&K rejoined the assembly system in 2024 after the 2019 Article 370
reorganisation. The five small-Muslim-pop states (HP, Sikkim, Arunachal,
Mizoram, Nagaland) have never elected a Muslim MLA in their history —
encoded as 0 with a methodology note. Tripura's first-ever Muslim MLA
(Boxanagar bypoll, Sep 2023) is NOT included in the main-election row.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "mla-share.csv"
CANONICALIZER_VERSION = "1.1.0"

# (year, geography_code, geography_level, geography_label, muslim_mlas, total_seats, cite)
ROWS = [
    (2024, "IN",     "national", "India (all-states aggregate)",  None,  None, "Across 28 state assemblies, Muslims ≈6% of seats (India Forum, Clarion India, multiple compilations)"),
    # 2025-2026 cycle
    (2026, "IN-S19", "state",    "West Bengal",                   40,    293,  "The Wire, Deccan Herald (2026 WB assembly)"),
    (2026, "IN-S32", "state",    "Kerala",                        35,    140,  "The Wire (2026 Kerala assembly)"),
    (2025, "IN-S07", "state",    "Delhi",                          4,     70,  "Maktoob, The Print (2025 Delhi assembly)"),
    # 2024 cycle
    (2024, "IN-S01", "state",    "Jammu & Kashmir",               54,     90,  "Clarion India (2024 J&K assembly — first since 2019 Article 370 reorg)"),
    (2024, "IN-S20", "state",    "Jharkhand",                      3,     81,  "oneindia, ZeeNews, Outlook (2024 Jharkhand — Hafizul Hassan JMM, Irfan Ansari INC, Nishant Alam INC)"),
    (2024, "IN-S21", "state",    "Odisha",                         1,    147,  "Deccan Herald, Clarion India (2024 Odisha — Sofia Firdous INC, first Muslim woman MLA in state history)"),
    (2024, "IN-S28", "state",    "Andhra Pradesh",                 3,    175,  "Radiance Weekly (2024 AP — all three from TDP, down from 4 in 2019)"),
    (2024, "IN-S12", "state",    "Arunachal Pradesh",              0,     60,  "Clarion India — no Muslim MLA in state history"),
    (2024, "IN-S11", "state",    "Sikkim",                         0,     32,  "Clarion India — no Muslim MLA in state history"),
    (2024, "IN-S27", "state",    "Maharashtra",                   10,    288,  "LatestLY, Deccan Herald (2024 Maharashtra)"),
    (2024, "IN-S06", "state",    "Haryana",                        5,     90,  "ummid.com (2024 Haryana)"),
    # 2023 cycle
    (2023, "IN-S29", "state",    "Karnataka",                      9,    224,  "The Hindu, Maktoob (2023 Karnataka)"),
    (2023, "IN-S23", "state",    "Madhya Pradesh",                 2,    230,  "TimelineDaily (2023 MP)"),
    (2023, "IN-S08", "state",    "Rajasthan",                      6,    200,  "TimelineDaily (2023 Rajasthan)"),
    (2023, "IN-S36", "state",    "Telangana",                      7,    119,  "TimelineDaily (2023 Telangana)"),
    (2023, "IN-S22", "state",    "Chhattisgarh",                   0,     90,  "TimelineDaily (2023 Chhattisgarh)"),
    (2023, "IN-S16", "state",    "Tripura",                        0,     60,  "Free Press Journal, The Pamphlet (Feb 2023 main election — no Muslim winner; Tafazzul Hossain BJP became state's first-ever Muslim MLA via Boxanagar bypoll Sep 2023, not counted in main-election row)"),
    (2023, "IN-S17", "state",    "Meghalaya",                      0,     60,  "No Muslim MLA winner found in 2023 Meghalaya assembly election (Christian-majority state with ~4.4% Muslim population)"),
    (2023, "IN-S13", "state",    "Nagaland",                       0,     60,  "Clarion India — Christian-majority state, no Muslim MLA winner found in 2023"),
    (2023, "IN-S15", "state",    "Mizoram",                        0,     40,  "Clarion India — no Muslim MLA in state history"),
    # 2022 cycle
    (2022, "IN-S09", "state",    "Uttar Pradesh",                 34,    403,  "The Wire, Maktoob, Indian Express (2022 UP)"),
    (2022, "IN-S24", "state",    "Gujarat",                        3,    182,  "Indian Express, Times of India (2022 Gujarat — historic low after BJP sweep)"),
    (2022, "IN-S05", "state",    "Uttarakhand",                    3,     70,  "ummid.com (2022 Uttarakhand — Shahzad BSP, Sarwat Kareem Ansari BSP, Furkan Ahmad INC)"),
    (2022, "IN-S03", "state",    "Punjab",                         1,    117,  "ummid.com, Maeeshat (2022 Punjab — Jamil ur Rahman AAP from Malerkotla, only Muslim MLA in state)"),
    (2022, "IN-S14", "state",    "Manipur",                        1,     60,  "Clarion India, Meghalaya Monitor (2022 Manipur — 13 Muslim candidates fielded, 1 won)"),
    (2022, "IN-S02", "state",    "Himachal Pradesh",               0,     68,  "thenewzradar.com — no Muslim MLA elected in HP since state formation 1971 (~2.1% Muslim population)"),
    (2022, "IN-S30", "state",    "Goa",                            0,     40,  "No Muslim MLA winner identified in 2022 Goa assembly election (~8.4% Muslim population, but representation has been historically negligible)"),
    # 2021 cycle
    (2021, "IN-S18", "state",    "Assam",                         31,    126,  "Maktoob, The Hindu (2021 Assam — Muslims ~34% of population, ~25% of MLAs)"),
    (2021, "IN-S33", "state",    "Tamil Nadu",                     5,    234,  "The Wire, The Hindu (2021 Tamil Nadu)"),
    (2021, "IN-S34", "state",    "Puducherry",                     1,     30,  "Clarion India (2021 Puducherry — held flat with 1 Muslim MLA in 30-member assembly)"),
    # 2020 cycle
    (2020, "IN-S10", "state",    "Bihar",                         19,    243,  "Maktoob, The Wire (2020 Bihar — Muslims ~17% of population)"),
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
                 f"affidavits; manual entry with cross-source verification."),
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
