"""
L2 -> L3 for the `communal-incidents-civic` metric.

Reads:  India Hate Lab 2023 + 2024 annual reports (sources/civic-databases/)
Writes: canonical/communal-incidents-civic.csv

Headline anti-Muslim hate speech event counts from IHL's annual reports.
Hardcoded from the reports' executive summary numbers (multiply cited
and consistent across multiple secondary sources including The Quint,
CNN, US News, Scroll, CJP).

  2023:    668  hate speech events
  2024:  1,165  hate speech events  (74.4% YoY increase)

IMPORTANT methodology note: IHL counts "hate speech events" (rallies,
political speeches, religious gatherings with hateful rhetoric).
This is fundamentally a different unit than NCRB's "communal rioting
incidents" (police-registered IPC violations). The two should be read
side-by-side as different views of the same underlying phenomenon, not
combined or subtracted.
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPO_ROOT / "canonical" / "communal-incidents-civic.csv"
CANONICALIZER_VERSION = "1.0.0"

# (year, count, source_doc, cite)
ROWS = [
    (2023, 668,
     "sources/civic-databases/ihl-2023-annual-report.pdf",
     "India Hate Lab Report 2023 (executive summary, cross-cited by The Quint, CJP, Vartha Bharati)"),
    (2024, 1165,
     "sources/civic-databases/ihl-2024-annual-report.pdf",
     "India Hate Lab Report 2024 (74.4% YoY increase from 2023; cited by CNN, US News, Scroll, CJP)"),
]


def canonicalize() -> None:
    extraction_run = (
        f"canonicalize-communal-incidents-civic-v{CANONICALIZER_VERSION}-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "metric_id", "geography_level", "geography_code", "year", "religion",
            "value", "denominator", "sample_size", "ci_lower", "ci_upper",
            "source_id", "source_document", "extraction_run",
            "methodology_note", "break_flag",
        ])
        for year, count, src_doc, cite in ROWS:
            w.writerow([
                "communal-incidents-civic", "national", "IN", year, "all",
                count, "hate_speech_events_per_year", "", "", "",
                "civic-incident-databases",
                src_doc,
                extraction_run,
                (f"India Hate Lab Annual Report {year}. {count:,} verified in-person "
                 f"anti-Muslim (and to a lesser extent anti-Christian) hate speech events. "
                 f"{cite}. Methodology: IHL counts hate speech events (rallies, political "
                 f"speeches, religious gatherings with hateful rhetoric) — fundamentally a "
                 f"different unit than NCRB's 'communal rioting incidents' (police-registered "
                 f"IPC violations). Read side-by-side, not combined."),
                "false",
            ])

    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(ROWS)} rows)")
    for year, count, _, _ in ROWS:
        print(f"  {year}: {count:,} events")


if __name__ == "__main__":
    canonicalize()
