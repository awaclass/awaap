/**
 * awaClass PWA Install Script
 *
 * Responsibilities:
 *   1. Register the service worker
 *   2. Capture and surface the beforeinstallprompt event
 *   3. Show a custom install banner (mobile + desktop)
 *   4. Handle iOS / Safari manual-install instructions
 *   5. Track install state so the banner never annoys repeat users
 *   6. Expose window.awaClassPWA for in-page use
 */

(function () {
  'use strict';

  // ─── Config ────────────────────────────────────────────────────────────────
  const SW_PATH        = '/serviceworker.js';
  const SW_SCOPE       = '/';
  const DISMISSED_KEY  = 'awa_pwa_dismissed';   // localStorage key
  const INSTALLED_KEY  = 'awa_pwa_installed';
  const SNOOZE_DAYS    = 3;                      // days before re-showing after dismiss

  // ─── State ─────────────────────────────────────────────────────────────────
  let deferredPrompt   = null;   // BeforeInstallPromptEvent
  let bannerEl         = null;

  // ═══════════════════════════════════════════════════════════════════════════
  // 1. SERVICE WORKER REGISTRATION
  // ═══════════════════════════════════════════════════════════════════════════
  function registerSW() {
    if (!('serviceWorker' in navigator)) return;

    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register(SW_PATH, { scope: SW_SCOPE })
        .then((reg) => {
          console.log('[PWA] Service worker registered, scope:', reg.scope);

          // Check for updates every time the page loads
          reg.addEventListener('updatefound', () => {
            const newWorker = reg.installing;
            newWorker.addEventListener('statechange', () => {
              if (
                newWorker.state === 'installed' &&
                navigator.serviceWorker.controller
              ) {
                // A new SW is waiting — optionally notify the user
                showUpdateToast();
              }
            });
          });
        })
        .catch((err) => console.warn('[PWA] SW registration failed:', err));

      // When a new SW takes over, reload to get fresh assets
      let refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (!refreshing) {
          refreshing = true;
          window.location.reload();
        }
      });
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 2. CAPTURE INSTALL PROMPT
  // ═══════════════════════════════════════════════════════════════════════════
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;

    if (!wasRecentlyDismissed() && !isInstalled()) {
      // Small delay so the page feels settled before the banner appears
      setTimeout(showInstallBanner, 1800);
    }
  });

  window.addEventListener('appinstalled', () => {
    localStorage.setItem(INSTALLED_KEY, 'true');
    hideBanner();
    deferredPrompt = null;
    console.log('[PWA] App installed');
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // 3. INSTALL BANNER
  // ═══════════════════════════════════════════════════════════════════════════
  function showInstallBanner() {
    if (bannerEl) return; // already shown

    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
    const isStandalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true;

    if (isStandalone) return; // already installed / running as app

    injectBannerStyles();

    bannerEl = document.createElement('div');
    bannerEl.id = 'awa-pwa-banner';
    bannerEl.setAttribute('role', 'dialog');
    bannerEl.setAttribute('aria-label', 'Install awaClass app');

    if (isIOS) {
      bannerEl.innerHTML = `
        <div class="awa-pwa-icon">A</div>
        <div class="awa-pwa-text">
          <strong>Add awaClass to Home Screen</strong>
          <span>Tap <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 2l-1.5 1.5L12 5l1.5-1.5zM11 5v9h2V5zm-6.5 7.5L3 14l1.5 1.5L6 14zm13 0L16 14l1.5 1.5L19 14zM7 17v2h10v-2z"/><path d="M5 19v2h14v-2z"/></svg> then "Add to Home Screen"</span>
        </div>
        <button class="awa-pwa-close" aria-label="Dismiss">✕</button>`;
    } else {
      bannerEl.innerHTML = `
        <div class="awa-pwa-icon">A</div>
        <div class="awa-pwa-text">
          <strong>Install awaClass</strong>
          <span>Study offline, faster, like a real app</span>
        </div>
        <button class="awa-pwa-install" aria-label="Install app">Install</button>
        <button class="awa-pwa-close" aria-label="Dismiss">✕</button>`;
    }

    document.body.appendChild(bannerEl);

    // Animate in
    requestAnimationFrame(() => {
      requestAnimationFrame(() => bannerEl.classList.add('awa-pwa-visible'));
    });

    // Wire up buttons
    const closeBtn = bannerEl.querySelector('.awa-pwa-close');
    if (closeBtn) closeBtn.addEventListener('click', dismissBanner);

    const installBtn = bannerEl.querySelector('.awa-pwa-install');
    if (installBtn) installBtn.addEventListener('click', triggerInstall);
  }

  async function triggerInstall() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log('[PWA] Install outcome:', outcome);
    deferredPrompt = null;
    hideBanner();
  }

  function dismissBanner() {
    localStorage.setItem(DISMISSED_KEY, Date.now().toString());
    hideBanner();
  }

  function hideBanner() {
    if (!bannerEl) return;
    bannerEl.classList.remove('awa-pwa-visible');
    setTimeout(() => {
      if (bannerEl && bannerEl.parentNode) bannerEl.parentNode.removeChild(bannerEl);
      bannerEl = null;
    }, 380);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 4. UPDATE TOAST
  // ═══════════════════════════════════════════════════════════════════════════
  function showUpdateToast() {
    const toast = document.createElement('div');
    toast.id = 'awa-pwa-update-toast';
    toast.innerHTML = `
      <span>awaClass has been updated!</span>
      <button id="awa-pwa-reload-btn">Reload</button>`;
    toast.style.cssText = `
      position:fixed;bottom:80px;left:50%;transform:translateX(-50%);
      background:#1c1917;color:#fff;padding:12px 20px;border-radius:12px;
      display:flex;align-items:center;gap:14px;font-size:13px;font-weight:600;
      z-index:99999;box-shadow:0 4px 20px rgba(0,0,0,.25);
      font-family:'Plus Jakarta Sans',-apple-system,sans-serif;
      animation:awaPwaSlideUp .35s ease;`;

    document.body.appendChild(toast);

    document.getElementById('awa-pwa-reload-btn').addEventListener('click', () => {
      if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage('SKIP_WAITING');
      }
      toast.remove();
    });

    // Auto-hide after 8 s
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 8000);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 5. HELPERS
  // ═══════════════════════════════════════════════════════════════════════════
  function wasRecentlyDismissed() {
    const ts = parseInt(localStorage.getItem(DISMISSED_KEY) || '0', 10);
    if (!ts) return false;
    return Date.now() - ts < SNOOZE_DAYS * 24 * 60 * 60 * 1000;
  }

  function isInstalled() {
    return (
      localStorage.getItem(INSTALLED_KEY) === 'true' ||
      window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 6. BANNER STYLES (injected once)
  // ═══════════════════════════════════════════════════════════════════════════
  function injectBannerStyles() {
    if (document.getElementById('awa-pwa-styles')) return;
    const style = document.createElement('style');
    style.id = 'awa-pwa-styles';
    style.textContent = `
      @keyframes awaPwaSlideUp {
        from { opacity:0; transform:translateX(-50%) translateY(20px); }
        to   { opacity:1; transform:translateX(-50%) translateY(0); }
      }

      #awa-pwa-banner {
        position: fixed;
        bottom: 76px;           /* sits just above the bottom nav if present */
        left: 12px;
        right: 12px;
        max-width: 480px;
        margin: 0 auto;
        background: #fff;
        border: 1.5px solid #e7e5e4;
        border-radius: 18px;
        padding: 14px 14px 14px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,.14);
        z-index: 99998;
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
        opacity: 0;
        transform: translateY(16px);
        transition: opacity .35s ease, transform .35s ease;
        pointer-events: none;
      }

      #awa-pwa-banner.awa-pwa-visible {
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
      }

      .awa-pwa-icon {
        width: 40px; height: 40px;
        min-width: 40px;
        background: #f97316;
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px; font-weight: 800; color: #fff;
      }

      .awa-pwa-text {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .awa-pwa-text strong {
        font-size: 13px;
        font-weight: 700;
        color: #1c1917;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .awa-pwa-text span {
        font-size: 12px;
        color: #78716c;
        display: flex;
        align-items: center;
        gap: 3px;
        flex-wrap: wrap;
      }

      .awa-pwa-install {
        background: #f97316;
        color: #fff;
        border: none;
        border-radius: 10px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 700;
        cursor: pointer;
        white-space: nowrap;
        font-family: inherit;
        transition: background .15s;
      }
      .awa-pwa-install:hover { background: #ea6e0b; }

      .awa-pwa-close {
        background: none;
        border: none;
        cursor: pointer;
        color: #78716c;
        font-size: 14px;
        padding: 4px 6px;
        border-radius: 6px;
        line-height: 1;
        transition: background .15s;
        flex-shrink: 0;
        font-family: inherit;
      }
      .awa-pwa-close:hover { background: #f5f5f4; color: #1c1917; }
    `;
    document.head.appendChild(style);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // 7. PUBLIC API
  // ═══════════════════════════════════════════════════════════════════════════
  window.awaClassPWA = {
    /** Programmatically trigger the install prompt (e.g. from a Settings page) */
    install: triggerInstall,
    /** Show the banner manually */
    showBanner: showInstallBanner,
    /** Check if running as installed app */
    isInstalled,
  };

  // ─── Boot ──────────────────────────────────────────────────────────────────
  registerSW();

})();
