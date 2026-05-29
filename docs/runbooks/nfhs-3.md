# Runbook: NFHS-3 (2005-06)

## Source identity
- Manifest entry: `nfhs-3`
- Publisher: IIPS, MoHFW; canonical English mirror: dhsprogram.com
- Pulled 2026-05-29 for the earliest reliably religion-disaggregated round on the tracked health indicators.

## Target
| target_id | url | content_length | sha256 (first 12) |
|---|---|---|---|
| india-report-frind3 | https://dhsprogram.com/pubs/pdf/frind3/frind3-vol1andvol2.pdf | 5,934,171 | c1fb9db3227e |

Pulled via `ingest/pull.py`. Wayback: failed (non-blocking). Local SHA256-sidecared archive is authoritative.

## Where the religion tables live (FRIND3 Vol I & II, 765 pp; verified 2026-05-29)
| indicator | table | page | panel | extractor |
|---|---|---|---|---|
| Infant mortality (IMR) | 7.2 | 231 | TOTAL (urban p230 / rural+total p231) | `transform/nfhs/extract_imr_trend.py` |
| Institutional delivery | 8.12 | 257 | total-residence | `transform/nfhs/extract_delivery_trend.py` |
| Women's anaemia (any) | 10.24.1 | 359 | total-residence | `transform/nfhs/extract_anaemia_trend.py` |
| Sanitation/toilet | — | — | NOT cleanly religion-disaggregated in this report | skipped |

IMR Table 7.2 spans pages: p230 = URBAN panel, p231 = RURAL (top) then TOTAL (bottom). The extractor anchors on the standalone `TOTAL` header; the TOTAL panel matches published national IMR 57.

## Known issues
- Older report layout; table numbering differs from NFHS-4/5. Anchor extraction on the `TOTAL` section header, not fixed line offsets.
- Anaemia: NFHS-3 note restricts cross-round comparison to ever-married women (NFHS-2 lacked never-married) — another reason the anaemia trend carries `break_flag`.
- Buddhist/Sikh cells rest on small samples in some tables; values can be parenthesized in the source (extractors strip parens).
