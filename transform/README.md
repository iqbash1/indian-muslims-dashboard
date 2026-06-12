# Transform

Two stages of transformation:

```
L1 (sources/) --[extract]--> L2 (extracted/) --[canonicalize]--> L3 (canonical/)
```

## Structure

```
transform/
  <source-id>/
    extract_<table>.py      L1 -> L2 for each table in this source
  canonicalize/
    <metric-id>.py          L2 -> L3 for this metric
  geography_codes.py        shared geography normalization (Census 2011
                            state-codes + post-2014 splits)
```

Religion-label normalization happens inline in each extractor — the L3
controlled vocabulary is just 8 lowercase tokens (`muslim, hindu, christian,
sikh, buddhist, jain, other, all`); a shared `religion_codes.py` hasn't been
needed.

## Rules

1. **Idempotent.** Re-running with the same L1 input produces byte-identical L2; same L2 produces byte-identical L3.
2. **Pure.** No live network calls during transform. All inputs are files on disk.
3. **Explicit.** No magic auto-detection of file formats; each source has an explicit parser.
4. **Logged.** Every transform run writes `extraction_run` (timestamp + version) onto every L3 row it produces.

## Adding a new transform

Each `transform/<source-id>/extract_<table>.py` should:
1. Read the L1 file path from its `.meta.json` sidecar (verify SHA256 matches).
2. Parse with explicit per-table logic (no schema-guessing).
3. Normalize geography codes via `geography_codes.py`.
4. Where the source carries a derived column (e.g. printed sex-ratio), cross-validate the computed value against it (the 1971 RGI religion extractor errors out if any derived sex-ratio differs by more than ±1 from the printed value).
5. Write a long-format CSV to `extracted/<source-id>/<table-id>.csv`.

Each `transform/canonicalize/<metric-id>.py` should:
1. Read its source L2 CSVs.
2. Combine / aggregate as needed.
3. Emit the canonical schema row format with `source_id`, `source_document`, `extraction_run`, `methodology_note`, and `break_flag` populated.
4. Where a metric blends sources of different tiers (e.g. ls-share / mla-share are manual-entry journalistic per-election compilations), each row's `source_id` flags its tier. (Sex-ratio and pop-share 1961-1991 were once secondary-fallback like this — Sachar and census-decadal-religion respectively — but now use primary RGI census throughout.)

## Active extractors

| Source dir | Extractors |
|---|---|
| `census-india-2011/` | `extract_c01.py`, `extract_c09.py`, `extract_c15.py` |
| `census-2011/` | `extract_c15_national_age.py` (national age × religion, for ger-higher-ed) |
| `census-india-2001/` | `extract_c01.py`, `extract_c09.py` |
| `census-india-1991/` | `extract_c09_religion.py` (XLSX) |
| `census-india-1981/` | `extract_hh15_religion.py` (PDF — HH-15 spans 4 facing pages, parses by token count + sex-ratio cross-check) |
| `census-india-1971/` | `extract_religion_summary.py` (PDF, cross-validates printed Sex Ratio) |
| `census-india-1961/` | `extract_c07_religion.py` (PDF — heavy OCR noise, verifies by anchor numbers + Sachar AT 3.8 cross-check) |
| `nfhs/` | `extract_imr_trend.py`, `extract_delivery_trend.py`, `extract_anaemia_trend.py`, `extract_table24.py` (sanitation), `extract_table72.py`, `extract_table813.py`, `extract_table10231.py`, `extract_table101_stunting.py` (qpdf-rotated landscape page) |
| `plfs/` | `extract_table48.py`, `extract_table49.py` (report PDFs); `extract_microdata_trends.py`, `extract_earnings_by_religion.py` (unit-level, 7 PLFS rounds) |
| `eus/` | `extract_microdata_trends.py` (NSS 61st/66th/68th unit-level, the pre-PLFS employment history) |
| `aishe/` | `extract_table15.py` |
| `ncrb/` | `extract_prison_religion.py` (English, multi-year), `extract_prison_religion_2020_hindi.py` (Hindi-edition fallback for the 2020 COVID-year gap), `extract_communal_crime.py` (multi-year CII Table 1.2 + per-table-PDF) |
| `sachar/` | `extract_mpce_by_state.py` (the 2004-05 mpce benchmark) |
| `hces/` | `extract_mpce_2023_24_by_religion.py`, `extract_mpce_2023_24_by_state.py`, `extract_quintile_2023_24_by_religion.py` (unit-level CSV) |
| `aidis/` | `extract_wealth_2013_by_religion.py` (NADA CSV), `extract_wealth_2018_by_religion.py` (NSS7718 TXT mirror) |
| `nss76/` | `extract_housing_2018_by_religion.py` (NSS7612dws TXT mirror) |
| `health/` | `extract_health_2017_by_religion.py` (NSS75250H TXT mirror), `extract_health_2025_by_religion.py` (NADA CSV) |
| `education/` | `extract_education_2017_by_religion.py` (NSS75252E TXT mirror), `extract_education_2025_by_religion.py` (CMS:E NADA CSV) |

Direct-from-L1 manual-entry (no L2 extractor; the canonicalizer reads hardcoded values that cite the published page/figure): civic-databases (India Hate Lab) + prs-eci-affidavits.

Registered but not feeding L3: census-decadal-religion — retired in Commit AJ once the RGI primary 1961-1991 volumes were located on NADA (pop-share now uses them directly); kept for cross-validation reference. (sachar-committee-2006 was also the sex-ratio 1961/1981 fallback until AJ, but feeds L3 again via the `mpce` metric added in Commit CQ.)

Note: `census-2011/` and `census-india-2011/` are both real directories (the former was added later to hold the C-15 national-age extractor for ger-higher-ed; the latter holds the main C-1/C-9/C-15 religion extractors). Same source from a manifest standpoint (`census-india-2011`).
