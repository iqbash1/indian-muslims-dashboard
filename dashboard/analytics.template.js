// ============================================================
// muslimdata.in — Analytics (GA4 + Microsoft Clarity)
//
// Owner / internal-traffic opt-out
// ---------------------------------
// Visit any page with ?notrack=1 once to mark this browser as internal:
//
//     https://muslimdata.in/?notrack=1
//
// That sets a localStorage flag (md_notrack=1) that persists across
// sessions on this browser. From then on:
//
//   - Clarity is NOT loaded (no session recording)
//   - GA4 is loaded but every event tags traffic_type=internal so the
//     GA4 Data Filter (admin → Data Settings → Data filters →
//     "Internal traffic") drops them from reports while keeping them
//     visible in DebugView for verification.
//
// To undo on a device, visit /?track=1 once.
//
// The flag is checked via `window.__mdInternal` (true | false) for
// debugging. Works on iOS Safari, Android Chrome, desktop browsers.
//
// IDs are injected at build time from dashboard/build.py — see the
// __GA4_ID__ / __CLARITY_ID__ placeholders there. The runtime file
// already has the real IDs substituted in.
// ============================================================

(function () {
    'use strict';

    var GA4_ID = '__GA4_ID__';
    var CLARITY_ID = '__CLARITY_ID__';

    try {
        var params = new URLSearchParams(location.search);
        if (params.has('notrack')) localStorage.setItem('md_notrack', '1');
        if (params.has('track')) localStorage.removeItem('md_notrack');
    } catch (e) {
        // localStorage may throw in Safari Private mode; treat as no-flag.
    }

    var isInternal = false;
    try {
        isInternal = localStorage.getItem('md_notrack') === '1';
    } catch (e) {
        isInternal = false;
    }
    window.__mdInternal = isInternal;

    // Microsoft Clarity (session recording). Skipped for internal traffic
    // and when the ID is still the placeholder.
    if (!isInternal && CLARITY_ID && CLARITY_ID.indexOf('__') !== 0) {
        (function (c, l, a, r, i, t, y) {
            c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
            t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
            y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
        })(window, document, 'clarity', 'script', CLARITY_ID);
    }

    // Google Analytics 4. Skipped when the ID is still the placeholder.
    if (GA4_ID && GA4_ID.indexOf('__') !== 0) {
        var gaScript = document.createElement('script');
        gaScript.async = true;
        gaScript.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA4_ID;
        document.head.appendChild(gaScript);

        window.dataLayer = window.dataLayer || [];
        window.gtag = function () { window.dataLayer.push(arguments); };
        window.gtag('js', new Date());
        window.gtag('config', GA4_ID, isInternal ? { traffic_type: 'internal' } : {});
    }
})();
