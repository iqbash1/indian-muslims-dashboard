# PRS / ECI affidavit compilations: Muslims in elected legislatures

Archived L1 source for the `ls-share` and `mla-share` metrics. Two committed,
human-readable, diffable tables (kept out of Git-LFS on purpose, see
`.gitattributes`) so any reader can review and re-use the exact figures.

| File | Coverage | Rows |
|---|---|---|
| `ls-muslim-mps-by-election.csv` | Muslim MPs in every Lok Sabha, 1952-2024 | 18 |
| `mla-muslim-mlas-by-assembly.csv` | Muslim MLAs by state/UT assembly (latest election each) + all-states aggregate | 32 |

## Why this is a manual compilation

Religion of MPs and MLAs is **not** published by the Election Commission of
India, and PRS Legislative Research's candidate-profile PDFs cover age, gender
and party but **not** religion. The counts are derived from ECI candidate
affidavits, classified post-election by journalists and researchers. Every row
is cross-verified across at least two independent compilations (Maktoob Media,
The India Forum / Hilal Ahmed's historical series, FACTLY, Statista, ORF,
Clarion India, The Wire, Deccan Herald, Outlook, Radiance Weekly, ummid.com and
others); the specific compilation used is recorded in each row's `citation`
column and carried into every canonical row's `methodology_note`.

## Columns

- `election_year`, plus `lok_sabha_number` (ls) or `geography_code` /
  `geography_level` / `geography_label` (mla)
- `muslim_seats`, `total_seats` (blank on the mla national-aggregate row)
- `share_pct` = `muslim_seats / total_seats x 100`, 2 dp (the aggregate row's
  ~6% headline where no count exists)
- `citation` = the journalistic compilation(s) the figure was verified against

## Provenance

Each file's SHA256 is recorded in its `<file>.meta.json` sidecar (also the
GitHub URL of the table itself). The canonicalisers
`transform/canonicalize/ls_share.py` and `mla_share.py` read these tables; the
tables, not the scripts, are the source of truth. Source registration and the
classification caveats: `docs/runbooks/prs-eci.md`.
