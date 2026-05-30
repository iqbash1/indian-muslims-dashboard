# Runbook: NCRB Prison Statistics India (PSI)

## Source identity

- Manifest entry: `ncrb-prison`
- Publisher: National Crime Records Bureau, Ministry of Home Affairs.
- Role: feeds the justice-cluster metrics `prison-share` and `undertrial-share`
  (Muslim share of the prison / undertrial population), now a **multi-year
  trend 2018–2023**. Also feeds `prison-rate-per-100k` / `undertrial-rate-per-100k`
  (2022 only — retained as canonical data but no longer carded; see below).

## Targets

| target_id | year | url | archived | sha256 (first 12) |
|---|---|---|---|---|
| psi-2018 | 2018 | Wayback `20230528012455` of `ncrb.gov.in/sites/default/files/PSI-2018.pdf` | sources/ncrb-prison/psi-2018.pdf | 7658b44cc01b |
| psi-2019 | 2019 | Wayback `20211105235151` of `ncrb.gov.in/sites/default/files/PSI-2019-27-08-2020.pdf` | sources/ncrb-prison/psi-2019.pdf | d5cd4e1c497d |
| psi-2020-hindi-ch2 | 2020 | Wayback `20220802054142` of `ncrb.gov.in/sites/default/files/PSI2020HChapter-2.pdf` (Hindi edition Chapter 2 — English unavailable) | sources/ncrb-prison/psi-2020-hindi-ch2.pdf | 01e3c6fcfb79 |
| psi-2021 | 2021 | ncrb.gov.in/uploads/nationalcrimerecordsbureau/post/1679316772PSI2021ason31-12-2021.pdf | sources/ncrb-prison/psi-2021.pdf | acf3d55eabb7 |
| psi-2022 | 2022 | ncrb.gov.in/uploads/nationalcrimerecordsbureau/custom/psiyearwise2022/1701613297PSI2022ason01122023.pdf | sources/ncrb-prison/psi-2022.pdf | 304b92eb2bf1 |
| psi-2023 | 2023 | ncrb.gov.in/uploads/files/PSI-2023.pdf | sources/ncrb-prison/psi-2023.pdf | 460382a982f4 |

**Provenance note:** 2021/2022/2023 are live on ncrb.gov.in. NCRB reorganised
its site and the **2018 and 2019** consolidated reports now 404 on the live
domain — they are served from the Wayback Machine raw-bytes (`id_`) endpoint,
which works with our ingest user-agent. The original dead NCRB URL is recorded
in each target's manifest description. (Wayback re-submit of the live 2021/2023
URLs failed at pull time — non-blocking.)

## Religion tables (verified via pdfplumber)

Each year carries four State/UT × religion tables, identical column order
`State/UT | Hindu | Muslim | Sikh | Christian | Others | Total` ("-" = the state
did not report that cell):

| table_id | category | 2018/2019 page | 2021/2022/2023 page |
|---|---|---|---|
| 2.10C | convicts | 105 | 103 |
| 2.11C | undertrials | 109 | 107 |
| 2.12C | detenues | 113 | 111 |
| 2.13C | other prisoners | 117 | 115 |

Page numbers drift year to year, so the extractor **locates each table by its
"Religion of <Category>" caption** and requires ≥1 `TOTAL (STATES/UTs)` data row
on the page (the caption alone also appears on the list-of-tables / executive-
summary pages, which carry no data and must be skipped). In 2021–2023 the
convicts (2.10C) ALL-INDIA row is split across lines and isn't captured — that's
fine, we use the STATES + UTs subtotals.

Extractor: `transform/ncrb/extract_prison_religion.py` (multi-year, `YEARS` list).
Writes one L2 per year: `extracted/ncrb-prison/psi-<year>-religion-by-state.csv`.

## Canonicalization — the SHARE method

Canonicalizers: `transform/canonicalize/prison_share.py` (all four categories)
and `undertrial_share.py` (category=undertrials). Both glob `psi-*-religion-by-state.csv`.

For each year, **sum the religion COLUMNS across the STATES + UTs subtotals**.
This equals the published ALL-INDIA total by construction, and — because a
non-reporting state's religion cells are blank — it automatically yields the
denominator over *religion-reported* prisoners only. Muslim share = Muslim sum ÷
that total. **Validated:** 2022 reproduces 108,968 / 540,148 = 20.17%.

Resulting series (Muslim share, religion-reported):

| year | prison-share | undertrial-share |
|---|---|---|
| 2018 | 20.24% | 21.45% |
| 2019 | 19.39% | 20.43% |
| 2020 | 20.29% | 21.06% (from Hindi edition Chapter 2 — see below) |
| 2021 | 18.71% | 19.44% |
| 2022 | 20.17% | 20.92% |
| 2023 | 19.08% | 20.05% |

All sit well above the ~14.2% Muslim share of the population (Census 2011), the
reference line on the dashboard cards.

### 2020 COVID-year extraction (Hindi edition)

The English PSI 2020 is unavailable in any primary or Wayback archive. The Hindi
edition survives in Wayback as a per-chapter split; **Chapter 2** (Prison Inmates)
carries the religion tables at pages **33** (2.10C convicts), **37** (2.11C
undertrials), **41** (2.12C detenues), **45** (2.13C other). Column layout is
IDENTICAL to the English editions (`Hindu | Muslim | Sikh | Christian | Others
| Total`); only headers, state names, and subtotal labels are Devanagari. Numbers
are Arabic numerals (language-neutral). The standalone extractor
`transform/ncrb/extract_prison_religion_2020_hindi.py` ignores the Devanagari
text entirely and keys on the numeric row structure (`<serial> <name in
Devanagari> <5 nums> <total>`), then synthesises a single `TOTAL (STATES)`
subtotal row collapsing the STATES vs UTs split (the downstream canonicalizer
sums them anyway, so the result is identical). 2020 Muslim share sits slightly
above 2019 — plausibly attributable to COVID decongestion orders mid-2020 that
released Hindu prisoners disproportionately (Muslims under-represented in the
"first-time minor offence" pool that was prioritised for release).

## Availability wall (why the series is 2018–2023, no gap)

- **2015** — the report has **no** religion-by-state table; religion appears only
  in narrative prose. The series cannot reach before 2016.
- **2016 / 2017** — religion tables were **never archived** by the Wayback Machine
  (2016 has only a truncated 1 MB consolidated stub; 2017 archived only chapters
  8/10 + front-matter), and the live NCRB paths 404. Not recoverable from
  primary/archive sources.
- **2020** — only the **Hindi** edition was archived. Recovered via the Hindi
  Chapter 2 numeric extraction described above; the trend is now gapless.

## Rendering

`dashboard/build.py` → `_card_share_trend()` plots the Muslim + Hindu share lines
over years (`trendChart`, Muslim bold) with a dashed horizontal **Muslim
population (14.23%)** reference line; internal year gaps are filled with null so
the data line breaks visibly. The scorecard row shows latest-year Muslim/Hindu
share and the gap vs 14.23% population. The earlier rate-per-100k cards (2022
snapshot) were replaced by these trends; the rate metric is kept as canonical
data only (the rate needs a Census-year population denominator, clean only to
2011, so it can't be a trend).

## Caveats (carried on canonical rows)

- **Non-reporting states** (e.g. Maharashtra, which did not report religion for
  undertrials/detenues in several years) are excluded from that year's
  denominator. Shares are "Muslim share among prisoners whose religion was
  reported."
- No methodology break across years (identical 2.10C–2.13C tables), so
  `break_flag=false` throughout.
