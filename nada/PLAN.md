# NADA microdata: update + banking plan

_Snapshot: 2026-06-10. API live (HTTP 200, 185 surveys on the open `listdatasets`
endpoint). **Posture: assume access to microdata.gov.in can be withdrawn. The raw
bytes are the irreplaceable asset; every transform/build step is fully offline once a
zip is on disk. So: bank raw + docs for everything SAFE now, build at leisure later.**_

Access method + the validated HCES recipe live in auto-memory `[[nada-microdata-api]]`.
Authoritative id/idno list captured today: [`nada/catalog-2026-06-10.tsv`](catalog-2026-06-10.tsv)
(185 surveys; committed so the catalog itself survives an API outage).

---

## 1. The safety rule (NSO "Rider for users")

Every NSS unit-level file ships a Rider. The governing principle, proven on HCES:

- **SAFE** = the survey's **target indicator, cross-classified BY religion.** This is the
  *intended* use (HCES Rider clause A; and NSO itself prints these religion cross-tabs in
  the published annual reports, e.g. PLFS Tables 48/49 we already extract).
- **OFF-LIMITS** = using these surveys to estimate religion-specific **demographic
  indicators** they were not designed for: **population share, sex ratio, literacy rate,
  school attendance / GER, morbidity prevalence.** The HCES Rider names
  population%/sex-ratio/literacy explicitly. We already source those from Census / AISHE /
  NFHS primary tables, which are both permitted and better.
- **Universal caveats** (publish identically to the `mpce` card): religion is self-reported
  and unverified; **State/UT is the finest stratum, NO district / sub-state estimates**;
  weighted religion shares run ~1pp below Census.

Each survey's OWN Rider is verified on download (riders differ slightly) and banked beside
the data.

---

## 2. What can be updated / added, and whether it is safe

Verdict key: **SAFE** = intended cross-tab, publish with the standard caveat ·
**AMBER** = safe only for the spending/target angle, avoid the demographic angle ·
**verify** = confirm against that survey's own Rider on download.

### PLFS — labour (BANK PRIORITY P1)
Consistent **July-June 7-round series**: `2017-18` (204), `2018-19` (216), `2019-20` (217),
`2020-21` (206), `2021-22` (214), `2022-23` (210), `2023-24` (213).
- **Updates** `lfpr-15plus`, `wpr-15plus`, `salaried-share`: single-year -> **7-point trends.**
- **Adds** a NEW **unemployment-rate-by-religion** metric.
- Target = labour-force status (LFPR / WPR / unemployment / job-type). By religion = **SAFE**
  (high confidence: NSO already prints employment x religion in the report tables we use).
  By-sex OK. State-level OK **where the Muslim cell-size supports it** — the unemployment
  numerator is thin, so gate any state x religion x sex breakdown on unweighted counts. NO district.
- Calendar-year PLFS variants exist (209/211/208/284/254/291/292) but mixing CY with
  July-June corrupts the trend — **stick to July-June**; latest is 2023-24 (213).

### AIDIS — wealth / assets (P1 latest, P3 history)
Debt & Investment: `2018-19` 77th (156, Visit 1+2) · `2013` 70th V1 (130) / V2 (132) ·
`2003` 59th (103) · `1992` 48th (70).
- **Adds** a NEW **wealth-disparity card** — Muslim household net worth / asset ownership /
  debt vs Hindu / all-India. The *original* question this project opened with.
- Target = assets & liabilities. By religion = **SAFE / verify** (less routinely published
  by religion than PLFS, so confirm AIDIS's own Rider). `2013 -> 2018-19` = a 2-point trend;
  2003 / 1992 optional deeper history. Truest "wealth" measure (stock, not the MPCE flow).

### HCES — consumption / MPCE (P1 for 2022-23)
`2023-24` (237, **already banked locally**, 244MB) · `2022-23` (224) · `2007-08` (116).
- **Updates** the `mpce` **By-state tab to CURRENT** (replace Sachar 2004-05 with 2023-24
  state x religion — fixes a *live staleness*: the card hero is already 2023-24 but the
  By-state tab still shows 2004-05). The state build needs **no new download** (use the
  banked 237 grouped by State).
- **Adds** a **2022-23 mid-point** (2004 -> 2022-23 -> 2023-24) + optional food-share /
  poverty-headcount by religion. Target = MPCE -> **SAFE** (proven).

### Health Social Consumption — out-of-pocket spending (P2)
`2025` (290) · `2017-18` 75th (152) · `2014` 71st (135).
- **Adds** a NEW **out-of-pocket / catastrophic health expenditure by religion** metric
  (complements the NFHS health cards with a *spending* angle).
- Target = health spending -> **SAFE**. Morbidity / hospitalisation *rate* by religion =
  **AMBER** -> avoid; publish the spending angle only.

### Education Social Consumption — out-of-pocket spending (P2)
CMSE `2025` 80th (255) · `2017-18` 75th (151) · `2014` (136).
- **Adds** a NEW **education expenditure / cost-of-schooling by religion** metric.
- Target = education spending -> **SAFE**. Literacy / GER / attendance by religion from
  this survey = **OFF-LIMITS** (use AISHE / Census, which we already do).

### Tier 3 — niche (bank only if cheap)
Time Use `2024` (236) / `2019` (223) = activity minutes by religion (SAFE, niche) ·
ASUSE `2023-24` (238) = enterprise by owner religion **if** captured.

---

## 3. Banking protocol (per survey, while the API is up)

1. `GET /api/datasets/{idno}/fileslist` (needs `X-API-KEY` header) -> pick the **CSV-format
   zip** (smallest), note its `FileNo` (= base64 of the filename).
2. `GET /api/fileslist/download/{idno}/{FileNo}` -> keep the zip **LOCAL** at
   `~/Desktop/nada-work/<survey>/` (**not** Git-LFS — the bandwidth lesson).
3. Compute **SHA256** of the zip.
4. **Commit** to the repo (small, provenance-only): the SHA256, the `fileslist` JSON, and the
   survey's **doc files** (Layout / Readme / **Rider** / methodology / state-codes). These are
   what make the pull reproducible *and the Rider auditable* offline.
5. Record idno / id / date in `manifest/sources.yaml` (+ `manifest/pulls.log.jsonl`).

Outcome: even if the API dies tomorrow, every SAFE metric is buildable from on-disk zips,
with provenance committed.

**Size estimate** (CSV zips, calibrated off HCES = 244MB / 2.6L households): PLFS ~50-150MB
x 7 ~= 0.5-1GB · AIDIS 2018-19 ~150-300MB · HCES 2022-23 ~244MB · Health / Education
~100-300MB each. **P1 set (PLFS x7 + AIDIS 2018-19 + HCES 2022-23) ~= 1.5-2.5GB.** Disk
free: 138GB -> non-issue. A reusable `nada/bank.sh` (key + idno list -> fileslist, pick CSV,
download, sha256, extract docs, write provenance) is the right tool; build it at banking time.

---

## 4. Build roadmap (offline, after banking; ordered by value / effort)

1. **HCES state-level + 2022-23 mid-point** — LOW effort, reuse
   `transform/hces/extract_mpce_2023_24_by_religion.py`; fixes the live-stale `mpce` By-state tab.
2. **PLFS 7-round trends + unemployment metric** — MODERATE; new person-level usual-status
   pipeline; unblocks the VIEW-FEASIBILITY "PLFS over-time skipped" row, converts 3 cards to
   trends, adds 1 card.
3. **AIDIS wealth card** — HIGHER; new survey + new card; the original wealth-disparity question.
4. **Health / Education spending** metrics — MODERATE each; net-new.

---

## 5. Doc hygiene
- `VIEW-FEASIBILITY.md` "PLFS over-time skipped" is now **stale** — that skip was a PDF-table
  limitation; microdata carries religion every round. Cross-referenced from there to here.
- Wherever a religion cross-tab from these surveys is published, reuse the **mpce caveat banner**.
