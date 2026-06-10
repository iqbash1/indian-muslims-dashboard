#!/usr/bin/env python3
"""Turn the local nada-work archive into committable repo provenance.

For each survey banked by nada/bank.py autoget (a ~/Desktop/nada-work/<slug>/ with
MANIFEST.json), this writes sources/nada/<slug>/ containing:
  - <datafile>.meta.json  : provenance for the unit-level file (kept LOCAL, not committed)
  - the build-critical docs (layout / estimation / readme / rider / schedule / codes / DDI)
  - MANIFEST.json + SHA256SUMS.txt (copied) and a PROVENANCE.md re-fetch recipe
Bulky published reports & field manuals are NOT copied (they stay in the local archive;
the archive has everything, the repo keeps what's needed to rebuild + audit permitted use).
It also appends one manifest/pulls.log.jsonl line per file. See nada/PLAN.md.

Run after the autoget batch:  .venv/bin/python nada/finalize.py
"""
import glob, json, os, re, shutil

ARCHIVE = os.path.expanduser("~/Desktop/nada-work")
DEST_ROOT = "sources/nada"
PULLS = "manifest/pulls.log.jsonl"
CATALOG = "https://microdata.gov.in/NADA/index.php/catalog"

# slug -> (numeric catalog id, human title, by-religion safety verdict per nada/PLAN.md)
SURVEYS = {
    "plfs-2017-18": (204, "Periodic Labour Force Survey 2017-18 (NSS, Jul2017-Jun2018)", "SAFE: employment x religion is the intended cross-tab"),
    "plfs-2018-19": (216, "Periodic Labour Force Survey 2018-19", "SAFE: employment x religion"),
    "plfs-2019-20": (217, "Periodic Labour Force Survey 2019-20", "SAFE: employment x religion"),
    "plfs-2020-21": (206, "Periodic Labour Force Survey 2020-21", "SAFE: employment x religion"),
    "plfs-2021-22": (214, "Periodic Labour Force Survey 2021-22", "SAFE: employment x religion"),
    "plfs-2022-23": (210, "Periodic Labour Force Survey 2022-23", "SAFE: employment x religion"),
    "plfs-2023-24": (213, "Periodic Labour Force Survey 2023-24", "SAFE: employment x religion"),
    "aidis-2018-19": (156, "All-India Debt & Investment Survey, NSS 77th round 2018-19 (Sch 18.2)", "SAFE (verify rider): assets/liabilities x religion"),
    "hces-2022-23": (224, "Household Consumption Expenditure Survey 2022-23", "SAFE: MPCE x religion (proven on 2023-24)"),
    "health-2017-18": (152, "Household Social Consumption: Health, NSS 75th round 2017-18 (Sch 25.0)", "SAFE for OOP health spending x religion; morbidity rate = avoid"),
    "health-2025": (290, "Household Social Consumption: Health, NSS 80th round 2025", "SAFE for OOP health spending x religion; morbidity rate = avoid"),
    "education-2017-18": (151, "Household Social Consumption: Education, NSS 75th round 2017-18 (Sch 25.2)", "SAFE for education spending x religion; literacy/GER = off-limits"),
    "education-2025": (255, "Comprehensive Modular Survey: Education, NSS 80th round 2025 (CMSE)", "SAFE for education spending x religion; literacy/GER = off-limits"),
    # --- expansion (Sachar 2004-05 anchor onward + AIDIS/housing deep points) ---
    "ces-2004-05": (108, "Household Consumer Expenditure, NSS 61st round, Jul2004-Jun2005 (the Sachar round)", "SAFE: MPCE x religion (intended use; reproduces Sachar from microdata)"),
    "ces-2006-07": (114, "Household Consumer Expenditure, NSS 63rd round, 2006-07", "SAFE: MPCE x religion"),
    "ces-2007-08": (116, "Household Consumer Expenditure, NSS 64th round, 2007-08", "SAFE: MPCE x religion"),
    "ces-2009-10": (123, "Household Consumer Expenditure, NSS 66th round, 2009-10", "SAFE: MPCE x religion"),
    "ces-2011-12-t1": (1, "Household Consumer Expenditure, NSS 68th round Type-1, 2011-12", "SAFE: MPCE x religion"),
    "ces-2011-12-t2": (126, "Household Consumer Expenditure, NSS 68th round Type-2, 2011-12", "SAFE: MPCE x religion"),
    "eus-2004-05": (109, "Employment & Unemployment, NSS 61st round, Jul2004-Jun2005", "SAFE: employment x religion (pre-PLFS, same indicators)"),
    "eus-2007-08": (117, "Employment, Unemployment & Migration, NSS 64th round, 2007-08", "SAFE: employment x religion"),
    "eus-2009-10": (124, "Employment & Unemployment, NSS 66th round, 2009-10", "SAFE: employment x religion"),
    "eus-2011-12": (127, "Employment & Unemployment, NSS 68th round, 2011-12 (last pre-PLFS)", "SAFE: employment x religion"),
    "aidis-2013-v1": (130, "Debt & Investment, NSS 70th round Visit-1, 2013", "SAFE (verify rider): assets/liabilities x religion"),
    "aidis-2013-v2": (132, "Debt & Investment, NSS 70th round Visit-2, 2013", "SAFE (verify rider): assets/liabilities x religion"),
    "aidis-2003": (103, "Debt & Investment, NSS 59th round, 2003", "SAFE (verify rider): assets/liabilities x religion"),
    "aidis-1992": (70, "Debt & Investment, NSS 48th round, 1992", "SAFE (verify rider): assets/liabilities x religion"),
    "health-2014": (135, "Social Consumption: Health, NSS 71st round, Jan-Jun 2014", "SAFE for OOP health spending x religion; morbidity rate = avoid"),
    "morbidity-2004": (107, "Morbidity & Health Care, NSS 60th round, Jan-Jun 2004", "SAFE for OOP health spending x religion; morbidity rate = avoid"),
    "education-2014": (136, "Social Consumption: Education, NSS 71st round, 2014", "SAFE for education spending x religion; literacy/GER = off-limits"),
    "housing-water-2018": (153, "Drinking Water, Sanitation, Hygiene & Housing, NSS 76th round, 2018", "SAFE: housing/water/sanitation amenities x religion"),
    "housing-water-2012": (129, "Drinking Water, Sanitation, Hygiene & Housing, NSS 69th round, 2012", "SAFE: housing/water/sanitation amenities x religion"),
    "housing-2008-09": (120, "Housing Condition Survey, NSS 65th round, 2008-09", "SAFE: housing amenities x religion"),
    "tus-2019": (223, "Time Use Survey, 2019", "SAFE: time-use minutes x religion (niche new metric)"),
    "tus-2024": (236, "Time Use Survey, 2024", "SAFE: time-use minutes x religion (niche new metric)"),
    "sas-agri-2013": (134, "Situation Assessment of Agricultural Households, NSS 70th round, 2013", "SAFE: agri-household income x religion (agricultural households only)"),
}

# Copy these doc kinds into the repo; everything else (reports, field manuals) stays local.
COMMIT_RE = re.compile(
    r'(layout|datalay|estimation|sample.?design|readme|note_for_data|note_on|rider|'
    r'schedule|sch_|sch -|_codes|district_code|state_|tabulation_state|codes for blocks|'
    r'nic_amendment|\.xml$)', re.I)

RIDER = ("NSO unit-level Rider: religion is self-reported and unverified; State/UT is the "
         "finest stratum (NO district/sub-state estimates); a target-indicator x religion "
         "cross-tab is the intended use, demographic indicators (population share, sex ratio, "
         "literacy, GER, morbidity prevalence) are off-limits. See nada/PLAN.md section 1.")


def provenance_md(slug, cat_id, title, verdict, data, docs):
    return f"""# Provenance: {title}

- **Survey idno:** `{data['idno']}`  (NADA catalog id {cat_id})
- **Catalog page:** {CATALOG}/{cat_id}
- **Pulled:** {data['pulled_at'][:10]} via MoSPI NADA REST API (personal X-API-KEY header)
- **By-religion verdict:** {verdict}

## Unit-level data file (kept LOCAL, not committed)
- `{data['name']}`  ({data['bytes']:,} bytes)
- sha256 `{data['sha256']}`
- archived at `~/Desktop/nada-work/{slug}/{data['name']}`

## Re-fetch recipe (if the API is still up)
```
NADA_API_KEY=...  .venv/bin/python nada/bank.py autoget {data['idno']} ~/Desktop/nada-work/{slug}
```
`bank.py` lists the survey's files, picks the unit-level data file (CSV zip, else .rar,
else the lone unit-level zip), downloads it + the method/layout docs, and re-verifies the
sha256 above. The API may be withdrawn; this directory + the local archive are the durable copy.

## Committed here (build-critical docs)
{chr(10).join(f'- `{d}`' for d in docs)}

## Permitted use
{RIDER}
"""


def main():
    pulls = []
    summary = []
    for man_path in sorted(glob.glob(f"{ARCHIVE}/*/MANIFEST.json")):
        slug = os.path.basename(os.path.dirname(man_path))
        if slug not in SURVEYS:
            print(f"!! unknown slug {slug}, skipping"); continue
        cat_id, title, verdict = SURVEYS[slug]
        man = json.load(open(man_path))
        dest = os.path.join(DEST_ROOT, slug)
        os.makedirs(dest, exist_ok=True)
        shutil.copy2(man_path, os.path.join(dest, "MANIFEST.json"))
        sums = os.path.join(ARCHIVE, slug, "SHA256SUMS.txt")
        if os.path.exists(sums):
            shutil.copy2(sums, os.path.join(dest, "SHA256SUMS.txt"))

        data = next((f for f in man["files"] if f["role"] == "data"), None)
        committed = []
        for f in man["files"]:
            src = os.path.join(ARCHIVE, slug, f["name"])
            keep = (f["role"] == "doc" and COMMIT_RE.search(f["name"]))
            if keep and os.path.exists(src):
                shutil.copy2(src, os.path.join(dest, f["name"]))
                committed.append(f["name"])
            saved_to = (f"sources/nada/{slug}/{f['name']}" if keep
                        else f"LOCAL:~/Desktop/nada-work/{slug}/{f['name']}")
            pulls.append({"source_id": f"nada-{slug}", "target_id": f["name"], "url": f["url"],
                          "pulled_at": man["pulled_at"],
                          "status_code": 200, "sha256": f["sha256"], "result": "new",
                          "wayback_url": None, "saved_to": saved_to})

        if data:
            meta = {
                "source_id": f"nada-{slug}", "target_id": f"{slug}-microdata",
                "idno": man["idno"], "filename": data["name"],
                "url": f"{CATALOG}/{cat_id}", "download_url": data["url"],
                "pulled_at": man["pulled_at"][:10],
                "content_length": data["bytes"], "sha256": data["sha256"],
                "pull_method": "MoSPI NADA REST API (personal X-API-KEY header)",
                "by_religion_verdict": verdict,
                "archival": (f"provenance-only: the unit-level file is NOT committed (kept local "
                             f"at ~/Desktop/nada-work/{slug}/). Re-fetch with the recipe in "
                             f"PROVENANCE.md and verify against this sha256. The schema/method "
                             f"docs in this directory ARE committed."),
            }
            json.dump(meta, open(os.path.join(dest, data["name"] + ".meta.json"), "w"), indent=2)
            open(os.path.join(dest, "PROVENANCE.md"), "w").write(
                provenance_md(slug, cat_id, title, verdict, data, committed))
        summary.append((slug, data["bytes"] if data else 0, len(committed)))
        print(f"{slug:18s}: data {(data['bytes']/1e6 if data else 0):6.1f}MB local, "
              f"{len(committed)} docs committed")

    with open(PULLS, "a") as log:
        for p in pulls:
            log.write(json.dumps(p) + "\n")
    print(f"\nappended {len(pulls)} lines to {PULLS}")
    tot = sum(b for _, b, _ in summary)
    print(f"{len(summary)} surveys, {tot/1e6:,.0f} MB unit-level data archived locally")


if __name__ == "__main__":
    main()
