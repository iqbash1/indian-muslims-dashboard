"""Playwright smoke tests for the built dashboard (docs/).

Serves the committed docs/ over a local HTTP server and drives headless Chromium
through the core user flows that the unit-free validators can't see:

  * homepage renders the card grid with no console errors,
  * clicking a card opens the modal with a tab bar,
  * switching tabs rewrites the address bar to the clean /m/{id}/{view}/ path
    and activates the right panel,
  * the share popover opens with the full set of share targets,
  * a #{id}/{view} hash deep-link (the per-view stub's redirect target) opens
    the modal on that tab,
  * a per-view stub URL redirects into the modal,
  * a /m/{id}/ landing page is a real indexable page (no redirect) with a data
    table and a CTA back into the interactive chart.

Run (after building docs/):
    .venv/bin/python dashboard/build.py
    .venv/bin/python tests/smoke.py

Exits non-zero on the first failing check, like validate.py. Third-party
analytics requests are blocked so the run is deterministic offline.
"""

from __future__ import annotations

import functools
import http.server
import pathlib
import socketserver
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"

# Third-party hosts the page may reference (analytics); blocked in-test so a
# missing network connection can't spawn console errors and fail the run.
_THIRD_PARTY = ("googletagmanager.com", "google-analytics.com", "clarity.ms",
                "gtag", "doubleclick.net")

_CHECKS: list[tuple[str, bool]] = []


def check(name: str, cond: object) -> None:
    ok = bool(cond)
    _CHECKS.append((name, ok))
    print(("PASS" if ok else "FAIL") + f": {name}")


def _serve() -> socketserver.TCPServer:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DOCS))

    class Server(socketserver.TCPServer):
        allow_reuse_address = True

        def log_message(self, *_a):  # silence per-request logging
            pass

    httpd = Server(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def run() -> int:
    if not (DOCS / "index.html").exists():
        print("docs/index.html not found; run dashboard/build.py first.")
        return 1
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Install with:\n"
              "  pip install playwright && python -m playwright install chromium")
        return 1

    httpd = _serve()
    errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            # Stub third-party analytics with an empty 204 (rather than abort(),
            # which logs a net::ERR_FAILED console error) so blocking is silent.
            page.route("**/*", lambda route: (
                route.fulfill(status=204, body="") if any(h in route.request.url for h in _THIRD_PARTY)
                else route.continue_()))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))

            # 1) Homepage renders the card grid.
            page.goto(BASE + "/", wait_until="networkidle")
            check("homepage renders cards", page.locator(".cards .card").count() >= 15)

            # 2) Open a metric known to carry multiple views.
            page.locator('.card[data-metric-id="lit-7plus"] .card-metric').click()
            page.wait_for_selector("#modal-body .modal-tab")
            check("modal opens with a tab bar (>=2 tabs)",
                  page.locator("#modal-body .modal-tab").count() >= 2)
            check("overview shows the clean /m/{id}/ URL",
                  page.url.rstrip("/").endswith("/m/lit-7plus"))

            # 3) Switching to a view tab rewrites the URL + activates the panel.
            page.locator('#modal-body .modal-tab[data-view="by-state"]').click()
            check("by-state tab shows the clean /m/{id}/{view}/ URL",
                  page.url.rstrip("/").endswith("/m/lit-7plus/by-state"))
            check("by-state panel is active",
                  page.locator("#modal-body .modal-panel.active").get_attribute("data-view") == "by-state")

            # 4) Share popover opens with the full set of targets.
            page.locator("#modal-share").click()
            page.wait_for_selector(".share-menu")
            check("share menu has 5 targets",
                  page.locator(".share-menu .share-menu-item").count() == 5)
            page.keyboard.press("Escape")

            # 5) Hash deep-link (the per-view stub's redirect target) opens that tab.
            page.locator("#modal-close").click()
            page.goto(BASE + "/#sex-ratio/by-state", wait_until="networkidle")
            page.wait_for_selector('#modal-body .modal-panel[data-view="by-state"].active')
            check("hash deep-link opens the right tab",
                  page.locator("#modal-body .modal-tab.active").get_attribute("data-view") == "by-state")
            check("hash deep-link rewrites to the clean URL",
                  page.url.rstrip("/").endswith("/m/sex-ratio/by-state"))

            # 6) A per-view stub URL redirects into the modal on that tab.
            page.goto(BASE + "/m/sex-ratio/by-state/", wait_until="networkidle")
            page.wait_for_selector("#modal-body .modal-tab.active", timeout=8000)
            check("per-view stub redirects into the modal",
                  page.url.rstrip("/").endswith("/m/sex-ratio/by-state"))

            # 6b) An overview share URL (?open=1, Commit GD) bounces off the
            # landing page into the open modal.
            page.goto(BASE + "/m/sex-ratio/?open=1", wait_until="networkidle")
            page.wait_for_selector(
                '#modal-overlay:not([hidden]) .card[data-metric-id="sex-ratio"]',
                timeout=8000)
            check("?open share link opens the modal", True)

            # 7) The landing page is a real page, not a redirect stub.
            page.goto(BASE + "/m/lit-7plus/", wait_until="networkidle")
            check("landing page has an h1", (page.locator("h1").inner_text() or "").strip() != "")
            check("landing page has a data table", page.locator("table tbody tr").count() >= 3)
            check("landing page links into the interactive chart",
                  page.locator('a.cta[href="/#lit-7plus"]').count() == 1)
            check("landing page is not a redirect stub",
                  page.locator("meta[http-equiv='refresh']").count() == 0)

            browser.close()
    finally:
        httpd.shutdown()

    check("no console or page errors", not errors)
    if errors:
        print("  first errors:", errors[:5])

    passed = sum(1 for _, ok in _CHECKS if ok)
    print(f"\n{passed}/{len(_CHECKS)} checks passed")
    return 0 if passed == len(_CHECKS) else 1


if __name__ == "__main__":
    sys.exit(run())
