# Runbook: PRS Legislative Research / ECI candidate affidavits

## Source identity

- Manifest entry: `prs-eci-affidavits`
- Publisher: PRS Legislative Research, analysing Election Commission of India
  candidate-affidavit data.
- Role: feeds the representation-cluster metrics **`ls-share`** (Muslim share
  of Lok Sabha members, 18-point series 1952→2024) and **`mla-share`** (Muslim
  share of state legislative assembly members, currently 30 state/UT
  assemblies covered).

## Why this is a SECONDARY manual-entry source (no L1 archive)

Neither PRS nor the ECI tabulates religion of elected representatives. PRS's
published candidate-profile PDFs cover age, gender, education, criminal
records, and asset declarations — but not religion. The ECI's published
results carry no religion field.

The underlying data is candidate-affidavit religion fields classified
**post-election by journalists and researchers** (Maktoob Media, Clarion
India, The India Forum, The Wire, Deccan Herald, FACTLY, Statista, ummid.com,
TimelineDaily, Maeeshat, Outlook, Radiance Weekly, Free Press Journal,
thenewzradar — plus aggregations by India Forum and Clarion India of all of
the above).

Because no clean machine-readable primary exists, this source is **pure
manual entry**: cited values embedded directly in the canonicalizers
(`transform/canonicalize/ls_share.py` and `mla_share.py`) with per-row
methodology notes listing the journalistic source(s) cross-verified.

There are no `targets` in this source's manifest entry and no `sources/prs-eci/`
directory — the L1 archive concept doesn't apply.

## Cross-source verification discipline

For every entry, at least two of the cited compilations must agree on the
headline count. Where compilations disagree (which has happened for Jharkhand
2024 — Outlook reported 4 UPA-only winners in 2019 but a Clarion summary
suggested ~10 cumulative since state formation), the canonicalizer commits
the value that can be verified from named MLAs in named compilations rather
than the aggregate-summary figure, and the methodology note records the
discrepancy.

## Series resulting

**ls-share** — all 18 Lok Sabhas 1952→2024:
- Peak: 9.04% (1980, 49/542)
- Recent: 4.42% (2024, 24/543)
- Always below the ~14% Muslim population share.

**mla-share** — 30 state/UT assemblies (most-recent election per assembly):
- Highest: J&K 2024 (54/90 = 60%) — first election since Article 370 reorg.
- Lowest: HP, Goa, Mizoram, Nagaland, Sikkim, Arunachal, Chhattisgarh,
  Tripura, Meghalaya — 0% (most have never elected a Muslim MLA in state
  history).
- National aggregate: ~6% across the 30 covered assemblies.

## Caveats (carried on canonical rows)

- **Religion of MLAs/MPs is derived from candidate affidavits**, classified
  post-election by journalists. Not directly tabulated by ECI or PRS.
- For state assemblies where the most-recent election produced 0 Muslim
  winners, the methodology note distinguishes "never had a Muslim MLA in
  state history" (HP, Goa, Mizoram, Nagaland, Sikkim, Arunachal) from
  "had one previously but not this term" (Chhattisgarh, Tripura main —
  the latter elected its first-ever Muslim MLA, Tafazzul Hossain BJP, via
  the Boxanagar bypoll Sep 2023, not in the main 2023 election row).
- Bypoll results are NOT folded into the main-election rows — each row
  represents the most-recent general election outcome.

## When the next release lands

Per-election. Add a new row to the `ROWS` list in `ls_share.py` (for Lok
Sabha) or `mla_share.py` (for any state assembly) within ~60 days of result,
once 2-3 journalistic compilations have stabilised on the count. State elections
covered: BR, AP, AR, GA, GJ, HR, HP, JH, KA, KL, MP, MH, MN, ML, MZ, NL,
OD, PB, RJ, SK, TN, TG, TR, UP, UK, WB, CG, AS + UTs (DL, PY, JK).
