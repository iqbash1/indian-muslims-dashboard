# Refresh schedule

Manifest-driven cadence per source. Update `next_expected` in `manifest/sources.yaml` when a release lands so the dashboard can flag overdue sources.

## Recurring

| Window | Sources | Action |
|---|---|---|
| Monthly | PLFS quarterly urban; civic incident databases | Pull and reconcile |
| Quarterly | RBI reports; AISHE if window open | Pull; run cross-source recon |
| Annually | PLFS annual (~Jul); NCRB Prison + Crime (~Nov); AISHE; HCES (cycle years); RTI civil services filing | Pull on release |
| Per cycle | NFHS on release; HCES on release; Census on release | Pull on release; create new manifest entry for new edition |
| Per election | ECI / PRS affidavits | Pull within 60 days of result |

## Annual rituals

- **Q4** — Audit (see `docs/audit-log.md`): sample 10 metrics and trace L4 → L1.
- **Q1** — RTI filing round (see `docs/rti-tracker.md`).
- **Whenever** — Methodology change review: scan release notes from NFHS/PLFS/HCES/AISHE/NCRB for definitional changes that warrant `break_flag` on canonical rows.

## Overdue alert

A source is considered overdue if `last_pulled` is more than 1.5× the cadence interval past `next_expected`. The dashboard surfaces overdue sources as a banner; the maintainer triages.
