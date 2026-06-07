# Deploy setup — muslimdata.in

One-time setup to put the dashboard at `https://muslimdata.in/`. Mirrors the
hawaiidashboard.org stack: Cloudflare Pages (auto-deploys from GitHub) + GA4
+ Microsoft Clarity. After this is done, every `git push origin main`
rebuilds and ships the site.

## What's already wired in the repo

- `wrangler.jsonc` — declares `./docs` as the static asset directory.
- `docs/_headers` — CSP + security headers, CSV CORS for `/canonical/*`.
- `docs/_redirects` — empty placeholder; add aliases here later.
- `docs/robots.txt`, `docs/sitemap.xml` — SEO basics.
- `dashboard/analytics.template.js` — GA4 + Clarity loader with the
  `?notrack=1` / `?track=1` internal-traffic toggle.
- `dashboard/build.py` — `GA4_ID` and `CLARITY_ID` constants near the top;
  build emits the substituted `docs/js/analytics.js` on every run.
- `docs/index.html` — references `js/analytics.js`, has canonical URL,
  OG/Twitter cards, meta description.

---

## 1. Connect Cloudflare Pages to the GitHub repo

1. Cloudflare dashboard → Workers & Pages → Create → Pages → Connect to Git.
2. Select repo `iqbash1/indian-muslims-dashboard`, branch `main`.
3. Build settings:
   - **Framework preset**: None
   - **Build command**: **leave empty (recommended)**, or `python3 dashboard/build.py`.
     `docs/` is committed pre-built, so an empty build command makes Cloudflare
     just serve the committed `./docs` — no pip, no Python, nothing to fail.
     This is the most robust setting. Only keep `python3 dashboard/build.py` if
     you want Cloudflare to rebuild from source on every push; if so, see the
     dependency note below.
   - **Build output directory**: `docs`
   - **Root directory**: (blank — repo root)
4. Environment variables: none required (Python 3 is preinstalled in CF builds).
   Dependency note (only relevant if Build command is `python3 dashboard/build.py`):
   Cloudflare runs `pip install -r requirements.txt` before the build command.
   `requirements.txt` is deliberately the **minimal deploy set — PyYAML only**
   (pure Python, always installs). `build.py` needs nothing else: the OG social
   images are committed under `docs/og/` and are not re-rendered on deploy, so
   **Pillow and the other pipeline deps live in `requirements-dev.txt`, NOT
   `requirements.txt`.** Do not move a native dep (Pillow) back into
   `requirements.txt` — a flaky Pillow wheel install on the build server caused
   intermittent build failures that froze the site (June 2026).
5. Save and deploy. The first build should produce
   `https://muslimdata.pages.dev/`.

---

## 2. Point muslimdata.in at Cloudflare

The domain was bought at a `.in` registrar (e.g. BigRock, Hostinger,
GoDaddy). The cleanest setup is to move the **nameservers** to Cloudflare;
DNS records then live in Cloudflare.

1. Cloudflare dashboard → Add a site → enter `muslimdata.in` → Free plan.
2. Cloudflare returns two nameservers, e.g.
   `tegan.ns.cloudflare.com` + `walt.ns.cloudflare.com`.
3. At the `.in` registrar, change nameservers to those two values.
   Propagation: 15 min – 24 h.
4. Once Cloudflare shows the domain as Active, in the Pages project:
   - Custom domains → Set up a custom domain → enter `muslimdata.in`.
   - Cloudflare auto-creates a CNAME flattening to the Pages URL.
   - Repeat for `www.muslimdata.in` if you want the www subdomain to work
     (set it as a redirect to apex).
5. SSL/TLS → Edge Certificates → Always Use HTTPS = ON.

---

## 3. Create the GA4 property and paste the ID

1. analytics.google.com → Admin → Create → Property.
   - Name: `muslimdata.in`
   - Time zone + currency: India / INR.
2. Add a Web data stream → URL `https://muslimdata.in` → stream name
   `muslimdata web`.
3. Copy the **Measurement ID** (format `G-XXXXXXXXXX`).
4. In `dashboard/build.py`, set:
   ```python
   GA4_ID = "G-XXXXXXXXXX"
   ```
5. Internal-traffic filter (optional but recommended):
   - Admin → Data Streams → Web → Configure tag settings → Show all →
     Define internal traffic.
   - Rule: `traffic_type` equals `internal`.
   - Admin → Data Settings → Data filters → activate the "Internal Traffic"
     filter (Filter state = Active).
   - To mark your browser as internal, visit
     `https://muslimdata.in/?notrack=1` once. To undo, `?track=1`.

---

## 4. Create the Clarity project and paste the ID

1. clarity.microsoft.com → New project.
   - Name: `muslimdata.in`
   - Website: `https://muslimdata.in`
2. Settings → Setup → copy the **Project ID** (10-char alphanumeric).
3. In `dashboard/build.py`, set:
   ```python
   CLARITY_ID = "abc123xyz9"
   ```
4. Internal traffic with `?notrack=1` already skips Clarity entirely (no
   session recording for marked browsers).

---

## 5. Rebuild + commit + push

```bash
.venv/bin/python dashboard/build.py
git add dashboard/build.py docs/js/analytics.js
git commit -m "wire GA4 + Clarity IDs"
git push origin main
```

Cloudflare Pages picks up the push, rebuilds, and ships. The deployed
site at `https://muslimdata.in/` should now load GA4 + Clarity (verify
in GA4 DebugView and the Clarity dashboard within ~5 minutes).

---

## Troubleshooting

- **CSP blocks GA or Clarity**: check `docs/_headers`. The CSP allows
  `googletagmanager.com`, `google-analytics.com`, `clarity.ms`. If you
  add another telemetry SDK, extend `script-src` and `connect-src`.
- **CSVs return CORS error from external tools**: confirm
  `Access-Control-Allow-Origin: *` is still on `/canonical/*` in
  `docs/_headers`.
- **Build fails on `yaml`**: ensure `PyYAML` is in `requirements.txt`
  and Cloudflare's build step runs `pip install -r requirements.txt`
  before `python3 dashboard/build.py`. (Simplest fix: set the Build
  command to empty so Cloudflare serves the committed `./docs` and runs
  no Python at all — `docs/` is already built.)
- **Build fails installing a dependency (e.g. Pillow / a native wheel)**:
  the deploy build must NOT install native packages. Keep `requirements.txt`
  to pure-Python deploy deps only (PyYAML); everything else belongs in
  `requirements-dev.txt`. A native-wheel install flaking on the Cloudflare
  build server froze the site once (June 2026); the durable fix is an empty
  Build command (serve committed `./docs`).
- **Old domain still pointing somewhere**: nameserver propagation can
  take up to 48 hours; verify with `dig NS muslimdata.in` from terminal.
