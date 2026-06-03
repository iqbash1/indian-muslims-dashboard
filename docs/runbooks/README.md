# Runbooks

One runbook per source. Owned by the data maintainer; the operational memory for how to keep that source flowing.

## Required sections per runbook

1. **Source identity** — manifest entry ID, publisher, home URL, cadence.
2. **Targets** — table of what we pull, with status.
3. **URL discovery procedure** — exact steps for finding and verifying a download URL on the publisher's site.
4. **Verified URLs log** — append-only record of each URL verification with date and who verified.
5. **Known issues** — quirks, traps, file-format gotchas.
6. **When the next release lands** — what to do when a new edition is published.
7. **Backup access** — mirrors, archives, fallbacks if the source goes offline.

## Source runbooks

### Census of India
- [census-india-1961.md](census-india-1961.md)
- [census-india-1971.md](census-india-1971.md)
- [census-india-1981.md](census-india-1981.md)
- [census-india-1991.md](census-india-1991.md)
- [census-india-2001.md](census-india-2001.md)
- [census-india-2011.md](census-india-2011.md)
- [census-decadal-religion.md](census-decadal-religion.md) (secondary, decadal summary)

### Health and nutrition (NFHS)
- [nfhs-2.md](nfhs-2.md)
- [nfhs-3.md](nfhs-3.md)
- [nfhs-4.md](nfhs-4.md)
- [nfhs-5.md](nfhs-5.md)

### Employment, education, consumption
- [plfs.md](plfs.md) — labour force (PLFS)
- [aishe.md](aishe.md) — higher education
- [hces-2022-23.md](hces-2022-23.md) — consumption expenditure (blocked on unit-level processing)

### Justice and crime (NCRB)
- [ncrb-prison.md](ncrb-prison.md)
- [ncrb-crime.md](ncrb-crime.md)

### Representation
- [prs-eci.md](prs-eci.md) — Lok Sabha and state MLA shares from PRS / ECI affidavits

### Civic and contested counts
- [civic-databases.md](civic-databases.md) — India Hate Lab and similar

### Historical context (one-off)
- [sachar-committee-2006.md](sachar-committee-2006.md) — used as fallback for 1961 and 1981 sex-ratio

### Pre-registered for future metrics (not yet feeding dashboard)
- [mha-parliament.md](mha-parliament.md)
- [niti-mpi.md](niti-mpi.md)
- [rbi-minority-lending.md](rbi-minority-lending.md)
- [rti-public-sector.md](rti-public-sector.md)

## Operations
- [deploy-setup.md](deploy-setup.md) — one-time Cloudflare Workers, DNS, GA4, Clarity wiring.
