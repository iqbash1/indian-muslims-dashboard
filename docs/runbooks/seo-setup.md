# SEO setup - muslimdata.in

One-time search instrumentation plus the recurring re-submission commands.
Companion to the July 2026 SEO retarget (query-shaped titles composed by
`_seo_head` in `dashboard/build.py`, guarded by `audit_consistency.py`
Check D).

## One-time dashboard steps (need logins; ~20 minutes total)

### 1. Cloudflare: unblock AI crawlers (do this FIRST)

As of July 2026 the zone blocks AI crawlers at the edge: ClaudeBot, GPTBot,
OAI-SearchBot and PerplexityBot all receive 403 on every page while
Googlebot and bingbot receive 200. This defeats `docs/robots.txt`, which
explicitly allows those bots, and blocks the site's own top referral
channel (AI assistants).

- dash.cloudflare.com -> select the `muslimdata.in` zone -> **AI Crawl
  Control** (older UI: Security -> Bots) -> set AI crawlers to **Allow**.
- Also check Security -> WAF -> Custom rules for any "block AI bots" rule,
  and Security -> Events (filter: user agent contains `ClaudeBot`) to see
  which rule has been firing.

Verify (all rows must print 200):

```bash
for ua in "ClaudeBot/1.0" "GPTBot/1.2" "OAI-SearchBot/1.0" "PerplexityBot/1.0" "Googlebot/2.1"; do
  printf "%-18s " "$ua"; curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0 (compatible; $ua)" https://muslimdata.in/m/lit-7plus/
done
```

### 2. Google Search Console

- search.google.com/search-console -> Add property -> **Domain** ->
  `muslimdata.in`.
- Copy the `google-site-verification=...` TXT value it shows.
- Cloudflare dash -> `muslimdata.in` zone -> DNS -> Records -> Add record:
  Type `TXT`, Name `@`, Content = the token -> Save.
- Back in Search Console click Verify (give DNS a few minutes).
- Left nav -> Sitemaps -> enter `sitemap.xml` -> Submit. Expect status
  "Success" with 25 discovered URLs.
- URL Inspection -> paste `https://muslimdata.in/` -> Request indexing.
  Repeat for `/m/lit-7plus/`, `/m/mpce/`, `/m/imr/`, `/m/ls-share/`,
  `/m/sex-ratio/` (the daily request quota is small; spread over days if
  needed).

### 3. Bing Webmaster Tools

- bing.com/webmasters -> sign in -> **Import from Google Search Console**
  -> authorise -> select `muslimdata.in` -> Import (the sitemap carries
  over). Bing's index also feeds ChatGPT search surfaces.

### 4. Cloudflare Crawler Hints

- Zone -> Caching -> Configuration -> **Crawler Hints** -> enable. This
  auto-pings IndexNow-member engines on content changes.

## IndexNow (manual re-submission after a significant deploy)

The site key is committed at `docs/61db0364102ba448edd6296af98987d1.txt`
(served at `https://muslimdata.in/61db0364102ba448edd6296af98987d1.txt`).
Submit every sitemap URL in one POST:

```bash
curl -s -X POST https://api.indexnow.org/indexnow \
  -H "Content-Type: application/json; charset=utf-8" \
  -d "$(python3 - <<'EOF'
import json, re, urllib.request
urls = re.findall(r"<loc>(.*?)</loc>",
                  urllib.request.urlopen("https://muslimdata.in/sitemap.xml").read().decode())
print(json.dumps({"host": "muslimdata.in",
                  "key": "61db0364102ba448edd6296af98987d1",
                  "keyLocation": "https://muslimdata.in/61db0364102ba448edd6296af98987d1.txt",
                  "urlList": urls}))
EOF
)"
```

Expect HTTP 200 or 202. IndexNow reaches Bing, Yandex, Seznam and Naver;
Google is not a member (Search Console covers Google).

## Title convention (what Check D enforces)

- Landing titles are composed by `_seo_head` in `dashboard/build.py` from
  `SEO_PHRASE[mid]` + computed canonical values + a `(vintage)` token, so
  the numbers recompute on every build and can never drift.
- Hard rules: no em/en dashes anywhere, landing titles <= 70 chars with a
  trailing "(vintage)" paren, meta descriptions 90-160 chars, no duplicate
  titles. `validate/audit_consistency.py` Check D verifies the COMMITTED
  docs/ in CI, so a build.py wording change without a local rebuild fails.
- The metric `name:` fields in `manifest/metrics.yaml` are NOT SEO surface:
  they feed the committed OG PNGs; never edit them for search phrasing.
