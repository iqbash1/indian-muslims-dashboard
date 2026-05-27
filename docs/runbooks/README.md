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

## Existing runbooks

- [census-india-2011.md](census-india-2011.md)
- _(other sources: stub until URL discovery starts)_
