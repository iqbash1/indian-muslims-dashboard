# Runbook: Census decadal religion proportions (SECONDARY)

## Source identity

- Manifest entry: `census-decadal-religion`
- Publisher: Office of the Registrar General & Census Commissioner (figures); compiled here from secondary transcriptions.
- Tier: **SECONDARY / manual-entry** — flagged as such on the dashboard card. Same handling as the `ls-share` / `mla-share` manual-entry metrics.

## Why this exists

The `pop-share` card shows each community's share of India's population as a
decadal trend (1961 → 2011). The 2001 and 2011 points come from this repo's
**primary** C-01 extracts (`census-india-2001`, `census-india-2011`). The
pre-2001 points (1961, 1971, 1981, 1991) are the published Census decadal
religion proportions, entered manually because **no clean machine-readable RGI
decadal table is downloadable**:

- The censusindia NADA catalog digitised only the 2001 + 2011 religion tables.
- The RGI "drop-in article" on religion (NADA cat 40443) is a 2001 *snapshot*, not a decadal table.
- Pew (2021), the PIB/RGI press release, the Wayback mirror, and data.gov.in all bot-block automated retrieval (403 / unreachable) — verified 2026-05-29.

## The values (manual entry)

% of total population, all-India. Held in `transform/canonicalize/pop_share.py`
(`DECADAL_SECONDARY`). Standard published Census series, reproduced identically
by RGI summaries, Pew 2021, and en.wikipedia.org/wiki/Religion_in_India.

| year | Hindu | Muslim | Christian | Sikh | Buddhist | Jain |
|---|---|---|---|---|---|---|
| 1961 | 83.45 | 10.69 | 2.44 | 1.79 | 0.74 | 0.46 |
| 1971 | 82.73 | 11.21 | 2.60 | 1.89 | 0.70 | 0.48 |
| 1981 | 82.30 | 11.75 | 2.44 | 1.92 | 0.70 | 0.47 |
| 1991 | 81.53 | 12.61 | 2.32 | 1.94 | 0.77 | 0.40 |

## Validation

- **Continuity:** the secondary 1991 Muslim share (12.61) flows smoothly into the
  primary 2001 (13.43) and 2011 (14.23) C-01 points — no discontinuity at the
  secondary→primary handoff.
- **Overlap cross-check:** the same secondary table gives 2001 = 13.43 / 2011 =
  14.23, which match this repo's primary C-01 extracts to <0.02pp.
- **Endpoint cross-check:** 1951 endpoints (Muslim 9.8, Hindu 84.1) independently
  confirmed by the Pew-derived search summary; 1951 itself is *omitted* from the
  series (post-Partition coverage + unreliable small-community figures).

## Caveats (carried on the card + canonical methodology_note)

- 1981 excludes Assam; 1991 excludes Jammu & Kashmir (not enumerated those rounds).
- Single secondary source for 1961-1991. **Upgrade path:** if a pullable primary
  RGI decadal table (or a reputable PDF) surfaces, archive it to L1 and replace
  the `DECADAL_SECONDARY` constant with an extractor, bumping these rows from
  `census-decadal-religion` to that source.
