# Census of India 1961 — runbook

**Source ID:** `census-india-1961`
**Publisher:** Office of the Registrar General & Census Commissioner, MoHA
**Cadence:** decennial (1961 round)

## What this source gives us

The full RGI Religion table C-VII for Census 1961 — Persons / Males /
Females for all six named religions + "Other religions and persuasions" +
"Religion not stated" at India + 5 zones + states + UTs, Total/Rural/Urban.
This is the same table cited by Sachar Committee 2006 AT 3.8 as "India,
Registrar General (1961)".

**Located on NADA via Commit-AJ targeted search.** Earlier sessions
mistakenly believed only the population-share Paper No. 1 of 1963 (NADA
cat 31326) was on NADA for 1961 religion; the full Social and Cultural
Tables volume (NADA cat 32022) carrying the C-VII table is also there.

## Target

| target_id | publication | url | archived | sha256 (first 12) |
|---|---|---|---|---|
| social-cultural-tables-vol-1-india-c07 | "Social and Cultural Tables, Part II-C(i), Vol-XIII INDIA, Census 1961" (A. Mitra RGI, 574pp, 16MB) | NADA cat 32022 / file 22949_1961_SCT.pdf | sources/census-1961/social-cultural-tables-c07-religion.pdf | 30179b02a44b |

## Table C-VII layout

PDF pp 501-520 (internal pp 488-507) — main table + supplement. The INDIA
T/R/U block spans two facing pages:

- **PDF p501** (internal p488): Total + Buddhists + Christians + Hindus columns
- **PDF p502** (internal p489): Jains + Muslims + Sikhs + Other religions + Religion-not-stated columns

The scan has OCR noise on some numeric tokens (e.g. "1,612,560" was OCR'd
as "1,612,56Q"; "1,053,665" as "i,053,fi65"; "188,755,134" as "188,75a,134").
The extractor handles this by:
1. Verifying the L1 PDF SHA256 against the sidecar (the file is exactly the
   one we hand-inspected).
2. Embedding hand-verified counts from the INDIA Total-residence row.
3. Cross-validating sex ratios against Sachar AT 3.8's published values
   (Muslim 935 / All 941) — ±1 tolerance.
4. Cross-validating sum-of-religions vs the Total Persons count (allowance
   for the ~0.07% gap representing NEFA's 38,705 non-religion-canvassed
   persons per the * footnote on the table).

## Pulling

```
.venv/bin/python ingest/pull.py --source census-india-1961
```

Single target — the 16MB scanned PDF. Slow pull (~30s); Wayback re-submit
fails for this size (non-blocking).

## Extracting

```
.venv/bin/python transform/census-india-1961/extract_c07_religion.py
```

Emits `extracted/census-1961/c07-religion.csv` (27 rows = 9 religions × 3
sex levels at national + total residence). Cross-validation runs at extract
time and errors out on any mismatch.

## Resulting INDIA row sex ratios

| religion | Persons | Sex Ratio |
|---|---|---|
| Hindu | 366,531,846 | 942 |
| Muslim | 46,940,799 | 935 |
| Christian | 10,728,586 | 989 |
| Sikh | 7,845,915 | 849 |
| Buddhist | 3,256,036 | 981 |
| Jain | 2,027,381 | 924 |
| Other | 1,498,895 | 1022 |
| Not Stated | 113,040 | 976 |
| All | 439,234,771 | 941 |

Sachar AT 3.8 cross-check: matches Muslim 935 + All 941 exactly.

## Caveats

- **NEFA (North-East Frontier Agency) ~38,705 persons** in the Total but not
  in the religion-canvassed counts, per the * footnote. Sum-of-religions
  runs ~290k below Total Persons (~0.07% gap).
- The Census 1961 publication also has Rural/Urban breakdowns in the same
  table; only Total is currently extracted.
- State + district religion breakdowns are in the same publication but not
  currently extracted.
