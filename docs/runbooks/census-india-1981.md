# Census of India 1981 — runbook

**Source ID:** `census-india-1981`
**Publisher:** Office of the Registrar General & Census Commissioner, MoHA
**Cadence:** decennial (1981 round)

## What this source gives us

The full RGI Religion table HH-15 for Census 1981 — Households / Persons /
Males / Females for all six named religions + "Other religions" + "Religion
not stated" at India + states + UTs, Total/Rural/Urban. The publication
explicitly notes "This table corresponds to table C-VII Religion of 1961
and 1971."

**Located on NADA via Commit-AJ targeted search.** Earlier sessions
mistakenly believed 1981 had only Delhi-specific (NADA cat 30864) and
Bihar-specific (NADA cat 30880) HHR papers; the all-India equivalent
(NADA cat 30879, Paper 3 of 1984) is also there.

## Target

| target_id | publication | url | archived | sha256 (first 12) |
|---|---|---|---|---|
| paper-3-of-1984-hh15-religion | "Paper 3 of 1984, Series-1, India — Household Population by Religion of Head of Household" (V.S. Verma RGI, 123pp) | NADA cat 30879 / file 26795_1981_HH.pdf | sources/census-1981/paper-3-of-1984-hh15-religion.pdf | 64fc02ea663d |

## Table HH-15 layout

The INDIA T/R/U block spans 4 facing pages (PDF pp 23-26), each carrying a
different column-group:

| PDF page | religion columns |
|---|---|
| p23 | Total Population + Hindus |
| p24 | Muslims + Christians |
| p25 | Sikhs + Buddhists |
| p26 | Jains + Other religions + Religion not stated |

Each row carries 4 numbers per religion column-group: No. of Households,
Persons, Males, Females. INDIA labels appear on p23 + p25 (with `*` after
INDIA on p23 to flag the Assam exclusion); p24 + p26 are continuation
pages where the India row carries no label — identified by being the first
all-numeric row of 4×n-religions tokens whose first token is >100k (this
filter skips the column-number ruler row "11 12 13 14...").

## Pulling + extracting

```
.venv/bin/python ingest/pull.py --source census-india-1981
.venv/bin/python transform/census-india-1981/extract_hh15_religion.py
```

Emits `extracted/census-1981/hh15-religion.csv` (81 rows = 9 religions × 3
sex levels × 3 residence levels). Cross-validates each derived sex ratio
against Sachar AT 3.8 (Hindu 933 / Muslim 937 / Christian 992 / Sikh 880 /
Buddhist 953 / Jain 941) — fails extraction on any mismatch >±1.

## Resulting INDIA T-row sex ratios

| religion | Persons | Sex Ratio |
|---|---|---|
| Hindu | 549,779,481 | 933 |
| Muslim | 75,512,439 | 937 |
| Christian | 16,165,447 | 992 |
| Sikh | 13,078,146 | 880 |
| Buddhist | 4,719,796 | 953 |
| Jain | 3,206,038 | 941 |
| Other | various | — |
| Total | 665,287,849 | 934 |

All cross-check against Sachar AT 3.8 exactly.

## Caveats

- **1981 Census not held in Assam.** All-India figures EXCLUDE Assam (~22M
  people, ~28% Muslim per 1971). This is the universal RGI/Sachar 1981
  convention; documented on the canonical row methodology_note.
- **Table = "Religion of HEAD of Household"**, not "Religion of all
  persons". For Indian census purposes households are religiously
  homogeneous so this is the canonical population-by-religion tally — the
  publication explicitly notes "This table corresponds to table C-VII
  Religion of 1961 and 1971." Sachar AT 3.8 used this same publication
  as its source.
