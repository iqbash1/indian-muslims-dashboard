# Runbook: NFHS-4 (2015-16)

## Source identity
- Manifest entry: `nfhs-4`
- Publisher: IIPS, MoHFW; canonical English mirror: dhsprogram.com
- Pulled 2026-05-29 for multi-round (time-series) religion differentials on health indicators.

## Target
| target_id | url | content_length | sha256 (first 12) |
|---|---|---|---|
| india-report-fr339 | https://dhsprogram.com/pubs/pdf/FR339/FR339.pdf | 7,256,916 | ae8295012077 |

Pulled via `ingest/pull.py`. Wayback: failed (non-blocking; large-file Cloudflare pattern — see nfhs-5 runbook). Local SHA256-sidecared archive is authoritative.

## Where the religion tables live (FR339, 671 pp; verified 2026-05-29 via pdfplumber scan)
| indicator | table | page | panel | extractor |
|---|---|---|---|---|
| Infant mortality (IMR) | 7.2 | 225 | TOTAL (urban p223 / rural p224 / total p225) | `transform/nfhs/extract_imr_trend.py` |
| Institutional delivery | 8.13 | 260 | total-residence | `transform/nfhs/extract_delivery_trend.py` |
| Women's anaemia (any) | 10.21.1 | 366 | total-residence | `transform/nfhs/extract_anaemia_trend.py` |
| Sanitation/toilet | — | — | NOT religion-disaggregated in FR339 (Ch.2 by residence/wealth only) | skipped |

IMR Table 7.2 TOTAL panel (p225) matches published national IMR 40.7 — confirms the right panel is read. Religion list in these tables: Hindu / Muslim / Christian / Sikh / Buddhist-Neo-Buddhist (no separate Jain).

## Known issues
- Anaemia cross-round comparability limited (blood-draw method / cut-offs) → `break_flag=true` on canonical women-anemia rows.
- Institutional-delivery % is the column immediately after the `100.0` total column in Table 8.13.
