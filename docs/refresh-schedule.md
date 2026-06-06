# Refresh schedule

Manifest-driven cadence per source. Update `next_expected` in `manifest/sources.yaml` when a release lands so the refresh check can flag overdue sources.

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

`validate/check_refresh.py` flags any source past its `next_expected` date, and fails CI (non-zero exit) once a source is more than 60 days overdue (`OVERDUE_THRESHOLD_DAYS`). It runs in CI as a punch-list, not as an on-page banner; the maintainer triages.
