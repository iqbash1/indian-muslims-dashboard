# Census of India 1991 — runbook

**Source ID:** `census-india-1991`
**Publisher:** Office of the Registrar General & Census Commissioner, MoHA
**Cadence:** decennial (1991 round)

## What this source gives us

The 1991 Census of India RGI religion data. Two pulls:

1. **C-9 Religion XLSX** (`1991-C09T-0100.xlsx`, NADA catalog 35737, 310 KB)
   Machine-readable cross-tab: religion × residence × sex × area (India / state /
   district). India row is "India Excluding (J&K)" because the 1991 Census was
   not held in J&K. 1,462 data rows. This is the source the canonicalizer
   actually consumes for sex-ratio.

2. **Religion, Paper 1 of 1995, Series-1, India** (`48848_1991_REL.pdf`, NADA
   catalog 32995, 2.1 MB). The companion PDF — same C-9 table as the XLSX
   plus an Introductory Note with state-by-state 1981→1991 population
   comparison tables. Useful for cross-checking but not currently consumed
   by any extractor.

## Naming gotcha

In 1991 census table-numbering, **"C-9" = the Religion population table**.
This was renumbered for 2001/2011 where C-9 = Education by Religion (the
literacy / matriculation / graduate-share table). Do not confuse them.
The 1991 publication does NOT have a literacy-by-religion XLSX on NADA —
educational attainment by religion was published in 1991 only in printed
volumes that aren't in NADA's digitised set.

## Pulling

```
.venv/bin/python ingest/pull.py --source census-india-1991
```

Two targets — the C-9 XLSX (310 KB) + the companion PDF (2.1 MB).

## Extracting

```
.venv/bin/python transform/census-india-1991/extract_c09_religion.py
```

The extractor:
1. Verifies the XLSX SHA256 against its sidecar
2. Opens sheet "C09T" with openpyxl
3. Iterates from row 11 (first data row); column layout: religion blocks
   start at col 6 (all/Total), col 9 (Hindu), col 12 (Muslim), col 15
   (Christian), col 18 (Sikh), col 21 (Buddhist), col 24 (Jain),
   col 27 (Other), col 30 (Not Stated). Each block = 3 consecutive
   columns: Persons / Males / Females.
4. Normalises the area name to a level (national / state / district)
5. Emits long-format CSV: `extracted/census-1991/c09-religion.csv`
   (~39,000 rows = ~1,400 areas × 3 residence × 9 religions × 3 sex)

## Coverage caveats

- **All-India figures exclude Jammu & Kashmir.** The 1991 Census was not held in J&K. The "India Excluding (J&K)" label is preserved verbatim in the L2 area_name.
- Population dimensions only — no educational attainment / occupation / housing in this XLSX.

## Cross-validation

The L2 → L3 sex-ratio derivation cross-checks against Sachar Committee 2006
AT 3.8 at the all-India level:

| Series | Derived from primary | Sachar AT 3.8 |
|---|---|---|
| All | 927 | 927 ✓ |
| Muslim | 930 | 930 ✓ |

Match.

## Not (yet) extracted

- State + district religion population breakdowns are extracted to L2 but
  not currently surfaced in any canonical metric. They could feed a 1991
  state-level pop-share trend if useful.
