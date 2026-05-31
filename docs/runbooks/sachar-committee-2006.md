# Sachar Committee Report (2006) — runbook

**Source ID:** `sachar-committee-2006`
**Publisher:** Cabinet Secretariat, Government of India (Justice Rajinder Sachar, Chair)
**Cadence:** one-off (2006)
**Type:** Secondary compilation — used ONLY for 1961 + 1981 sex-ratio decadal years where the original RGI religion volumes aren't on NADA

## Role in the pipeline

This source is a fallback for the two decadal years (1961 and 1981) where the
original RGI religion volumes aren't accessible to this pipeline. For the
other rounds (1971, 1991, 2001, 2011), the dashboard pulls the RGI volumes
directly:

| Year | Source feeding `sex-ratio` |
|---|---|
| 1961 | **Sachar AT 3.8** (this source) — Muslim + All only |
| 1971 | `census-india-1971` (RGI Paper 2 of 1972) — all 6 religions |
| 1981 | **Sachar AT 3.8** (this source) — Muslim + All only |
| 1991 | `census-india-1991` (RGI C-9 XLSX + Paper 1 of 1995) — all 6 religions |
| 2001 | `census-india-2001` (primary C-1) — full breakdown |
| 2011 | `census-india-2011` (primary C-15) — full breakdown |

So Sachar contributes 4 canonical rows total (1961 Muslim + All; 1981 Muslim
+ All). Hindu / Christian / Sikh / Buddhist / Jain decadal sex-ratio for 1961
and 1981 remain unresolved — Sachar AT 3.8 doesn't carry those columns, and
the underlying RGI volumes (Census of India 1961 Religion Tables; 1981 RGI
religion compilation cited as "India, Registrar General 1984") aren't in
NADA's catalog as of 2026-05-31.

## Cross-validation against the primary RGI sources

At every overlap year, Sachar AT 3.8's national values match the underlying
RGI primary publications used elsewhere in this pipeline:

| Year | Series | Sachar AT 3.8 | Primary (this repo's L3 derivation) |
|---|---|---|---|
| 1971 | All | 930 | 930 (sum of 6 named from RGI 1972) |
| 1971 | Muslim | 922 | 922 (RGI 1972 Summary) |
| 1991 | All | 927 | 927 (RGI 1991 C-9 XLSX) |
| 1991 | Muslim | 930 | 930 (RGI 1991 C-9 XLSX) |
| 2001 | All | 933 | 933 (primary C-1 2001) |
| 2001 | Muslim | 936 | 936 (primary C-1 2001) |

That match across four overlap years is what justifies treating Sachar's
1961 + 1981 figures as the trustworthy fallback for the years where the
primary source isn't pullable.

## Coverage caveats Sachar flags

- **1981 excludes Assam** (RGI did not enumerate that round — Sachar's All-India figure for 1981 is constructed without Assam)
- **1991 excludes J&K** (similarly — but the dashboard now consumes the RGI 1991 primary which has the same caveat)
- Sachar AT 3.8 has **Muslim + All only**. Hindu / Christian / Sikh / Buddhist / Jain pre-2001 are NOT in this table.

## Pulling

```
.venv/bin/python ingest/pull.py --source sachar-committee-2006
```

Single target — the 6.5 MB full report PDF from the Internet Archive mirror
of the original Ministry of Minority Affairs publication. The official MoMA
URL (`minorityaffairs.gov.in/sites/default/files/sachar_comm.pdf`) 404s as
of 2026-05-31, so we use archive.org's mirror as the canonical pull URL.

## Other Sachar tables not (yet) used

| Table | Page | What it gives | Status |
|---|---|---|---|
| Appendix Table 3.1 | p292 | Population Trends for Major Religions 1961-2001 (share + growth) | Not used — the existing `pop-share` decadal series uses these same figures via `census-decadal-religion` source-id |
| AT 3.10-3.13 | p303-306 | NFHS-2 1998-99 religion x child mortality / fertility / contraception | Not used — we have full NFHS-2/3/4/5 primary extracts |
| AT 4.1 | p308 | State-wise literacy levels — 2001 only | Not used as decadal (2001-only); 2001 literacy by religion already comes from primary C-09 |

## Why no literacy decadal extension

Sachar Chapter 4 (Education) Section 3.1 "Time Trends in Literacy Levels"
narrates the all-India trend by SRC since the 1960s, but the underlying
decadal table is published only as **Figure-Set 4.3** — a chart, not a
table. AT 4.1 is 2001-only. The 1971 RGI religion paper has no literacy
section; the 1991 RGI C-9 XLSX is population-only. Pre-2001 literacy-by-
religion at the national level remains a known gap and would need either
chart digitization of Sachar Fig 4.3 (~±1pp precision), or direct access
to the original Census 1961-1991 C-9 Education-by-Religion tables which
aren't on NADA.
