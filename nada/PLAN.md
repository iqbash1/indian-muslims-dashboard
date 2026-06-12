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

### PLFS — labour (SHIPPED: Commits EW/EX; pre-PLFS EUS history added in FN)
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

### AIDIS — wealth / assets (SHIPPED: 2013 cards EY-FB, 2012->2018 trend FM; 2003/1992 history Nesstar-blocked)
Debt & Investment: `2018-19` 77th (156, Visit 1+2) · `2013` 70th V1 (130) / V2 (132) ·
`2003` 59th (103) · `1992` 48th (70).
- **Adds** a NEW **wealth-disparity card** — Muslim household net worth / asset ownership /
  debt vs Hindu / all-India. The *original* question this project opened with.
- Target = assets & liabilities. By religion = **SAFE / verify** (less routinely published
  by religion than PLFS, so confirm AIDIS's own Rider). `2013 -> 2018-19` = a 2-point trend;
  2003 / 1992 optional deeper history. Truest "wealth" measure (stock, not the MPCE flow).

### HCES — consumption / MPCE (2023-24 SHIPPED: EV/EO/EY; 2022-23 mid-point BLOCKED, Nesstar-only)
`2023-24` (237, **already banked locally**, 244MB) · `2022-23` (224) · `2007-08` (116).
- **Updates** the `mpce` **By-state tab to CURRENT** (replace Sachar 2004-05 with 2023-24
  state x religion — fixes a *live staleness*: the card hero is already 2023-24 but the
  By-state tab still shows 2004-05). The state build needs **no new download** (use the
  banked 237 grouped by State).
- **Adds** a **2022-23 mid-point** (2004 -> 2022-23 -> 2023-24) + optional food-share /
  poverty-headcount by religion. Target = MPCE -> **SAFE** (proven).

### Health Social Consumption — out-of-pocket spending (SHIPPED: Commit FU, 2026-06-11)
`2025` (290) · `2017-18` 75th (152) · `2014` 71st (135).
- **Shipped** as the `hospital-oop-spend` card: OOPME per hospitalisation case
  (excl childbirth), 2017-18 -> 2025 trend, gated to 0.01% on Report 586 +
  the 2025 press note. Recipe: docs/runbooks/nss-health.md +
  nada/health-layout-map.md. The 2014 round stays Nesstar-blocked.
- Morbidity / hospitalisation *rate* by religion = **AMBER** -> avoided as
  planned; only the spending angle is published.

### Education Social Consumption — out-of-pocket spending (SHIPPED: Commit FV, 2026-06-11)
CMSE `2025` 80th (255) · `2017-18` 75th (151) · `2014` (136).
- **Shipped** as the `school-edu-spend` card: per enrolled school student per
  academic year excl coaching, 2017-18 -> 2025 trend (break_flag on 2025;
  CMS:E concept revisions), gated to 0.01% on Reports 585 + 595. Recipe:
  docs/runbooks/cmse-education.md + nada/education-layout-map.md. The 2014
  round stays Nesstar-blocked.
- Literacy / GER / attendance by religion from this survey = **OFF-LIMITS**
  (use AISHE / Census, which we already do).

### Tier 3 — niche (bank only if cheap)
Time Use `2024` (236) / `2019` (223): both rounds verified Nesstar-only
2026-06-11 (the 2024 "full data" zip is an 899MB .Nesstar disc image,
2019's a 564MB one; Wayback has no TXT mirror) -> the Windows-VM unlock
set · ASUSE `2023-24` (238) = enterprise by owner religion **if** captured.

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

1. **HCES state-level + 2022-23 mid-point** — state-level DONE (Commit EV: mpce
   By-state = HCES 2023-24 microdata). The 2022-23 mid-point is BLOCKED
   (verified 2026-06-11: catalog id 224 ships only a 2.5GB .Nesstar binary;
   no TXT mirror — React-era release; data.gov.in empty). Unlock = Nesstar
   Explorer export in a Windows VM.
2. **PLFS 7-round trends + unemployment metric** — DONE (Commits EW/EX; recipe
   in docs/runbooks/plfs-microdata.md).
3. **AIDIS wealth card** — DONE and EXTENDED: 2013 card (Commits EY-FB) +
   2012->2018 trend via the NSS7718 TXT mirror (Commit FM; the deleted Drupal
   page's mospi.NIC.in twin in Wayback was the key). AIDIS 2003 third point is
   Nesstar-blocked (the "new format" rar = a Nesstar Explorer disc image, NOT
   plain data; same for ces-2009-10/2011-12 and sas-agri-2013).
4. **Health / Education spending** metrics — DONE (Commits FU/FV, 2026-06-11):
   hospital-oop-spend + school-edu-spend, each a 2017-18 -> 2025 trend from
   the 75th-round TXT mirrors (NSS75250H/ and NSS75252E/, found via the
   mospi.nic.in-twin Wayback trick) + the 2025-round CSV pulls. Only the
   2014 rounds stay Nesstar-blocked. Bonus mirrors banked the same day:
   SAS 2019 (NSS7733/, 34/35 files - v1 L04 is permanently 404 upstream;
   NEXT in the build queue) and disability 76th (NSS7626d/, bank
   incomplete at 1/16 files).
5. **EUS 2004-12 pre-PLFS labour history** — DONE 2026-06-11: the three
   quinquennial rounds (61st/66th/68th) extend lfpr/wpr/salaried-share/
   unemployment-rate back to 2004, gated on NSS Reports 568/552 (310 cells);
   the 64th (2007-08) is excluded for want of published by-religion anchors.
   Recipe: nada/eus-layout-map.md + docs/runbooks/plfs-microdata.md.

---

## 5. Doc hygiene
- `VIEW-FEASIBILITY.md` "PLFS over-time skipped" is now **stale** — that skip was a PDF-table
  limitation; microdata carries religion every round. Cross-referenced from there to here.
- Wherever a religion cross-tab from these surveys is published, reuse the **mpce caveat banner**.
