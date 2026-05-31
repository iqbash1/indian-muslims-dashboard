# Runbook: Census decadal religion proportions (SECONDARY)

## Source identity

- Manifest entry: `census-decadal-religion`
- Publisher: Office of the Registrar General & Census Commissioner (figures); compiled here from secondary transcriptions.
- Tier: **SECONDARY / manual-entry**.
- **Status post-Commit-AJ:** REGISTERED-BUT-NOT-FEEDING-CANONICAL. All decadal pop-share rows now flow from RGI PRIMARY publications (census-india-1961 / -1971 / -1981 / -1991 / -2001 / -2011). This source served as a fallback for 1961-1991 (Commits originally), then narrowed to 1961+1981 (Commit AI), then retired entirely (Commit AJ) after the RGI 1961 + 1981 religion volumes were located on NADA.

## Why this exists

The `pop-share` card shows each community's share of India's population as a
decadal trend (1961 → 2011). 2001 and 2011 come from PRIMARY C-01 extracts
(`census-india-2001`, `census-india-2011`); 1971 + 1991 come from PRIMARY RGI
religion publications (`census-india-1971`, `census-india-1991`) post-Commit-AI.
That leaves **1961 + 1981** as the two years still depending on this entry —
the underlying RGI religion volumes for those years aren't in NADA's
digitised catalog.

- The RGI "drop-in article" on religion (NADA cat 40443) is a 2001 *snapshot*, not a decadal table.
- Pew (2021), the PIB/RGI press release, the Wayback mirror, and data.gov.in all bot-block automated retrieval (403 / unreachable) — verified 2026-05-29.

## The values (manual entry)

% of total population, all-India. Held in `transform/canonicalize/pop_share.py`
(`DECADAL_SECONDARY`). Standard published Census series, reproduced identically
by RGI summaries, Pew 2021, and en.wikipedia.org/wiki/Religion_in_India.

| year | Hindu | Muslim | Christian | Sikh | Buddhist | Jain |
|---|---|---|---|---|---|---|
| 1961 | 83.45 | 10.69 | 2.44 | 1.79 | 0.74 | 0.46 |
| 1981 | 82.30 | 11.75 | 2.44 | 1.92 | 0.70 | 0.47 |

(1971 + 1991 were previously here too; both now come from PRIMARY RGI
publications via `census-india-1971` + `census-india-1991`. The 1991 primary
value differs from the secondary it replaced — 12.12% Muslim primary vs
12.61% Muslim secondary — because the primary C-9 XLSX excludes J&K (Census
not held there) while the secondary used RGI's J&K-interpolated all-India
total. The methodology note on the 1991 canonical row explains this.)

## Validation

- **Endpoint cross-check at 2001 / 2011:** if we project the 1981 secondary
  trajectory forward, it lands on the primary 2001 + 2011 values consistent
  with the published series — the secondary 1961 + 1981 figures are reliable.
- **Endpoint cross-check at 1951:** 1951 endpoints (Muslim 9.8, Hindu 84.1)
  independently confirmed by the Pew-derived search summary; 1951 itself is
  *omitted* from the series (post-Partition coverage + unreliable small-
  community figures).

## Caveats (carried on the card + canonical methodology_note)

- 1981 excludes Assam (not enumerated that round).
- Single secondary source for 1961 + 1981. To remove this source entirely,
  the original RGI Religion Tables for 1961 (C-VII) and 1981 (a 1984
  publication referenced by Sachar) would need to be located. Neither is in
  NADA's current digitised catalog (verified 2026-05-31).
