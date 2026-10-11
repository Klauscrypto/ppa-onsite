/*!
 * analytics.js – Besucherstatistik für Pilsner-Websites
 * - Umami (selbst gehostet, cookielos): lädt immer, keine Einwilligung nötig
 * - Google Analytics 4: lädt NUR nach Einwilligung (Consent Mode v2, "basic")
 * - Eigenes, schlankes Cookie-Banner mit gleichwertigen Buttons
 *
 * Einbindung (vor </head>):
 *   <script src="/analytics.js" defer
 *     data-ga="G-XXXXXXXXXX"
 *     data-umami="00000000-0000-0000-0000-000000000000"
 *     data-umami-src="https://stats.pilsner-vertrieb.de/script.js"
 *     data-privacy="/datenschutz.html"
 *     data-accent="#0f766e"></script>
 *
 * Banner erneut öffnen: beliebiges Element mit Attribut data-consent-open
 * oder window.pvConsent.open()
 */
(function () {
  'use strict';
  if (window.pvConsent) return;

  var me = document.currentScript || document.querySelector('script[src*="analytics.js"]');
  var cfg = (me && me.dataset) || {};
  var isPlaceholder = function (v) { return !v || /X{4,}|^0{8}-/.test(v); };
  var GA_ID = isPlaceholder(cfg.ga) ? '' : cfg.ga;
  var UMAMI_ID = isPlaceholder(cfg.umami) ? '' : cfg.umami;
  var UMAMI_SRC = cfg.umamiSrc || 'https://stats.pilsner-vertrieb.de/script.js';
  var PRIVACY = cfg.privacy || '/datenschutz.html';
  var ACCENT = cfg.accent || '#0f766e';
  var KEY = 'pv_consent_v1';

  var lang = (document.documentElement.lang || 'de').slice(0, 2).toLowerCase();
  var T = {
    de: {
      title: 'Dürfen wir Statistik-Cookies setzen?',
      text: 'Wir möchten mit Google Analytics verstehen, wie diese Seite genutzt wird. Das ist freiwillig und jederzeit widerrufbar. Eine anonyme, cookielose Reichweitenmessung läuft unabhängig davon.',
      more: 'Datenschutzerklärung',
      accept: 'Akzeptieren',
      reject: 'Ablehnen'
    },
    en: {
      title: 'May we set statistics cookies?',
      text: 'We would like to use Google Analytics to understand how this site is used. This is optional and can be withdrawn at any time. Anonymous, cookieless reach measurement runs independently.',
      more: 'Privacy policy',
      accept: 'Accept',
      reject: 'Decline'
    }
  };
  var t = T[lang] || T.de;

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { return null; }
  }
  function write(analytics) {
    try { localStorage.setItem(KEY, JSON.stringify({ analytics: !!analytics, ts: Date.now() })); } catch (e) {}
  }

  /* ---------- Umami (cookielos) ---------- */
  function loadUmami() {
    if (!UMAMI_ID || document.querySelector('script[data-website-id]')) return;
    var s = document.createElement('script');
    s.defer = true;
    s.src = UMAMI_SRC;
    s.setAttribute('data-website-id', UMAMI_ID);
    s.setAttribute('data-do-not-track', 'true');
    document.head.appendChild(s);
  }

  /* ---------- Google Analytics 4 (nur mit Einwilligung) ---------- */
  var gaLoaded = false;
  function loadGA() {
    if (!GA_ID || gaLoaded) return;
    gaLoaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('consent', 'default', {
      ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied',
      analytics_storage: 'granted'
    });
    window.gtag('js', new Date());
    window.gtag('config', GA_ID, { anonymize_ip: true });
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GA_ID);
    document.head.appendChild(s);
  }
  function removeGACookies() {
    document.cookie.split(';').forEach(function (c) {
      var name = c.split('=')[0].trim();
      if (/^_ga/.test(name)) {
        var host = location.hostname.split('.');
        for (var i = 0; i < host.length - 1; i++) {
          var d = host.slice(i).join('.');
          document.cookie = name + '=; Max-Age=0; path=/; domain=.' + d;
        }
        document.cookie = name + '=; Max-Age=0; path=/';
      }
    });
  }

  /* ---------- Banner ---------- */
  var box;
  function css() {
    if (document.getElementById('pvc-style')) return;
    var st = document.createElement('style');
    st.id = 'pvc-style';
    st.textContent =
      '#pvc{position:fixed;z-index:2147483000;left:16px;right:16px;bottom:16px;max-width:520px;margin:0 auto;' +
      'background:#fff;color:#1f2937;border:1px solid rgba(0,0,0,.08);border-radius:14px;padding:18px 20px;' +
      'box-shadow:0 18px 50px rgba(0,0,0,.18);font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}' +
      '#pvc h2{margin:0 0 6px;font-size:15px;font-weight:700;color:#111827}' +
      '#pvc p{margin:0 0 14px;color:#4b5563}' +
      '#pvc a{color:' + ACCENT + ';text-decoration:underline}' +
      '#pvc .pvc-b{display:flex;gap:10px}' +
      '#pvc button{flex:1;padding:10px 14px;border-radius:999px;font:600 14px system-ui,sans-serif;cursor:pointer;' +
      'border:1.5px solid ' + ACCENT + '}' +
      '#pvc .pvc-acc{background:' + ACCENT + ';color:#fff}' +
      '#pvc .pvc-rej{background:#fff;color:' + ACCENT + '}' +
      '#pvc button:focus-visible{outline:3px solid #93c5fd;outline-offset:2px}' +
      '@media (prefers-color-scheme:dark){#pvc{background:#111827;color:#e5e7eb;border-color:rgba(255,255,255,.1)}' +
      '#pvc h2{color:#f9fafb}#pvc p{color:#cbd5e1}#pvc .pvc-rej{background:transparent}}';
    document.head.appendChild(st);
  }
  function close() { if (box) { box.remove(); box = null; } }
  function open() {
    if (!GA_ID) return; // ohne GA gibt es nichts einzuwilligen
    css();
    close();
    box = document.createElement('div');
    box.id = 'pvc';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-live', 'polite');
    box.setAttribute('aria-labelledby', 'pvc-t');
    box.innerHTML =
      '<h2 id="pvc-t"></h2><p><span class="pvc-x"></span> <a></a></p>' +
      '<div class="pvc-b"><button type="button" class="pvc-rej"></button><button type="button" class="pvc-acc"></button></div>';
    box.querySelector('h2').textContent = t.title;
    box.querySelector('.pvc-x').textContent = t.text;
    var a = box.querySelector('a'); a.textContent = t.more; a.href = PRIVACY;
    var rej = box.querySelector('.pvc-rej'); rej.textContent = t.reject;
    var acc = box.querySelector('.pvc-acc'); acc.textContent = t.accept;
    rej.onclick = function () { decide(false); };
    acc.onclick = function () { decide(true); };
    document.body.appendChild(box);
  }
  function decide(yes) {
    var before = read();
    write(yes);
    close();
    if (yes) { loadGA(); }
    else if (before && before.analytics) { removeGACookies(); location.reload(); }
  }

  window.pvConsent = { open: open, get: read };

  function init() {
    loadUmami();
    var c = read();
    if (c && c.analytics) loadGA();
    else if (!c) open();
    document.addEventListener('click', function (e) {
      var el = e.target.closest && e.target.closest('[data-consent-open]');
      if (el) { e.preventDefault(); open(); }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
