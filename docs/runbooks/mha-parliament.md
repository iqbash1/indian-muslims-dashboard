# Runbook: Ministry of Home Affairs — Parliament answers

## Source identity

- Manifest entry: `mha-parliament-answers`
- Publisher: Ministry of Home Affairs (and others — Personnel & Training,
  CAPF, etc.), via Lok Sabha / Rajya Sabha question replies.
- Role: would feed civic-cluster metrics around **public-sector employment
  composition by religion** (police, paramilitary, civil services) that
  RBI/NCRB don't cover.
- **Status: pre-registered, not yet pulled.** Hardest-tier — these data live
  only in scattered Parliament responses that aren't bot-pullable from PIB
  or sansad.in.

## Why this is stub-only

Parliament replies that disaggregate central / state employment by
religion appear intermittently. Examples that have been cited in
journalistic coverage:

- IPS officer composition by religion (Question replies, several MoMA
  intakes 2015–2023)
- CAPF (CRPF, BSF, ITBP, SSB, CISF) intake by religion
- Civil services preliminary exam clearance by religion
- Subordinate judicial services intake by community (state legislative
  assemblies; not always MHA's domain)

The data exists in PDF/HTML form on sansad.in but:
1. sansad.in's search isn't bot-friendly (login walls + bot detection)
2. PIB releases that summarise these answers don't load via WebFetch
   (403 bot-block)
3. Coverage is question-driven, not periodic — there's no annual report
   to anchor against

## Unblocking

Most realistic path: **manual RTI filing**. See `docs/rti-tracker.md`.
Filing template (to draft): request specific year-X intake numbers from
the target department, with religion column. Cross-validate the response
against any prior Parliament reply on the same question.

Alternative: PRS Legislative Research occasionally compiles "religion in
public service" tables in its sectoral briefs; check `prsindia.org`
manually for the latest before filing an RTI.

When unblocked: register target(s) for each per-department RTI response
PDF, write an extractor (likely per-PDF since structure varies), write a
canonicalizer.

## Caveats (when implemented)

- Parliament-answer numbers are point-in-time snapshots; they aren't
  comparable across years unless the question was identically worded.
- Always cite the specific reply (member name, date, question number) in
  the canonical row's methodology_note, since the same statistic can be
  cited differently in different Parliament sessions.
