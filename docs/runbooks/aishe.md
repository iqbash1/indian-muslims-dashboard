# Runbook: All India Survey on Higher Education (AISHE)

## Source identity

- Manifest entry: `aishe`
- Publisher: Department of Higher Education, Ministry of Education
- Home: https://aishe.gov.in/
- Cadence: annual (reference year typically 18 months prior to publication)

## Phase 1 targets

| target_id | description | status |
|---|---|---|
| report-2021-22 | AISHE 2021-22 Final Report | verified |
| report-2020-21 | AISHE 2020-21 Final Report (for trend / time-series) | verified |

## URL discovery procedure

The AISHE portal was reorganized in 2022 — old URLs under `aishe.gov.in/aishe-final-report/` redirect to the new structure. PDFs are now hosted on `cdnbbsr.s3waas.gov.in/` (AWS-backed government CDN). URLs are stable once published but format is opaque (hash-style paths).

For each new annual release:
1. Visit https://aishe.gov.in/aishe-final-report/
2. Right-click the PDF link for the desired year, copy URL (will be a cdnbbsr.s3waas.gov.in/... path).
3. HEAD-check.
4. Update `manifest/sources.yaml`.

Alternative discovery via Ministry of Education page: https://www.education.gov.in/en/aishe-report-1

## Verified URLs log

| target_id | url | verified_on | verified_by | content_length |
|---|---|---|---|---|
| report-2021-22 | https://cdnbbsr.s3waas.gov.in/s392049debbe566ca5782a3045cf300a3c/uploads/2025/06/2025060466438560.pdf | 2026-05-27 | Iqbal (Claude-assisted) | 9,766,276 |
| report-2020-21 | https://cdnbbsr.s3waas.gov.in/s392049debbe566ca5782a3045cf300a3c/uploads/2025/06/202506041612700081.pdf | 2026-05-27 | Iqbal (Claude-assisted) | 10,285,746 |

## Archived files (first pull)

| target_id | archived path | sha256 (first 12) | pulled_at |
|---|---|---|---|
| report-2021-22 | sources/aishe/aishe-report-2021-22.pdf | c4400273cb2d | 2026-05-27 |
| report-2020-21 | sources/aishe/aishe-report-2020-21.pdf | 4dff9fe0b5ac | 2026-05-27 |

## Where religion crosstabs actually live

AISHE main report has:
- **Chapter on enrolment by social category** — SC/ST/OBC breakdowns by level and discipline
- **Religion enrolment table** — typically one table reporting Hindu / Muslim / Christian / Sikh / Buddhist / Jain / Other / Not Stated enrolment by level (UG/PG/etc.). This is the table for the `ger-higher-ed` metric.
- **Time-series tables** — multi-year totals (useful for trend metric)

For the `ger-higher-ed` metric: need enrolment by religion (numerator) and the corresponding 18-23 population by religion (denominator from Census 2011 + state population projections). Computing religion-specific GER requires combining AISHE (numerator) with Census 2011 C-13 / C-14 age-religion-state cuts (denominator). Pending.

## Known issues

- Smaller religious groups sometimes grouped as "Others" in published tables — note this in canonicalize methodology
- Portal redesign in 2022 broke old URLs; some academic citations point to dead paths
- AISHE reports the religion of *students enrolled*, but the dashboard wants GER (enrolment / population in age band). Denominator integration is non-trivial.

## When AISHE 2022-23 lands

- Expected ~mid-2026 (running ~2 years behind reference year).
- Add `report-2022-23` target. Keep `report-2021-22` and `report-2020-21` for time series.
- Check whether religion category coverage changed.

## Backup access

- Internet Archive Wayback (the ~10 MB reports should be below the Wayback failure threshold but borderline)
- Ministry of Education mirror: https://www.education.gov.in/en/aishe-report-1
- Third-party mirrors (educationforallinindia.com etc.) — avoid as primary source; use only for cross-check
