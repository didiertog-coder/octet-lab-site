// ── Date dynamique dans le header ──────────────────────────────────────────
(function () {
  const el = document.getElementById('live-date');
  if (!el) return;
  const JOURS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
  const MOIS  = ['', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
  const now = new Date();
  el.textContent = `📅 ${JOURS[now.getDay()]} ${now.getDate()} ${MOIS[now.getMonth() + 1]} ${now.getFullYear()}`;
})();

const f = document.getElementById('vram');
if (f) {
  const out = document.getElementById('vram-out'), e = f.elements;
  const calc = () => {
    const need = (+e.params.value || 0) * +e.quant.value + +e.ctx.value + 0.5;
    const card = [6, 8, 12, 16, 24, 32, 48].find(x => x >= need);
    out.textContent = card ? `≈ ${need.toFixed(1)} Go. Carte conseillée : ${card} Go ou plus.` : `≈ ${need.toFixed(1)} Go. Prévoyez plusieurs cartes ou de la RAM système.`;
  };
  f.addEventListener('input', calc);
  calc();
}

const CONSENT_KEY = 'octetlab_cookie_consent';
const body = document.body;

function loadScript(src, attrs = {}, onload) {
  if (!src) return;
  if (document.querySelector(`script[src="${src}"]`)) {
    if (onload) onload();
    return;
  }
  const s = document.createElement('script');
  s.src = src;
  s.async = true;
  Object.entries(attrs).forEach(([k, v]) => s.setAttribute(k, v));
  if (onload) s.addEventListener('load', onload, { once: true });
  document.head.appendChild(s);
}

function initGA4(measurementId) {
  if (!measurementId || !/^G-[A-Z0-9]+$/i.test(measurementId)) return;
  loadScript(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`, {}, () => {
    window.dataLayer = window.dataLayer || [];
    function gtag(){ window.dataLayer.push(arguments); }
    gtag('js', new Date());
    gtag('config', measurementId, { anonymize_ip: true });
  });
}

function initPlausible(domain) {
  if (!domain) return;
  loadScript('https://plausible.io/js/script.js', { 'data-domain': domain });
}

function initUmami(scriptUrl, websiteId) {
  if (!scriptUrl || !websiteId) return;
  loadScript(scriptUrl, { 'data-website-id': websiteId });
}

function initAdSense(enabled, clientId, slotId) {
  if (!enabled || !clientId) return;
  loadScript(`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(clientId)}`, { crossorigin: 'anonymous' }, () => {
    if (!slotId) return;
    const container = document.getElementById('ad-slot-home');
    if (!container || container.querySelector('ins.adsbygoogle')) return;

    const ad = document.createElement('ins');
    ad.className = 'adsbygoogle';
    ad.style.display = 'block';
    ad.setAttribute('data-ad-client', clientId);
    ad.setAttribute('data-ad-slot', slotId);
    ad.setAttribute('data-ad-format', 'auto');
    ad.setAttribute('data-full-width-responsive', 'true');
    container.appendChild(ad);
    (window.adsbygoogle = window.adsbygoogle || []).push({});
  });
}

function applyTracking(consentGranted) {
  if (!body || !consentGranted) return;
  initGA4(body.dataset.ga4 || '');
  initPlausible(body.dataset.plausibleDomain || '');
  initUmami(body.dataset.umamiScript || '', body.dataset.umamiId || '');
  initAdSense(body.dataset.adsenseEnabled === '1', body.dataset.adsenseClient || '', body.dataset.adsenseSlotHome || '');
}

function initCookieBanner() {
  const banner = document.getElementById('cookie-banner');
  if (!banner) return;

  const btnAccept = document.getElementById('cookie-accept');
  const btnReject = document.getElementById('cookie-reject');
  const btnManage = document.getElementById('cookie-manage');
  const saved = localStorage.getItem(CONSENT_KEY);

  const openBanner = () => {
    banner.hidden = false;
  };

  if (saved === 'accepted') {
    applyTracking(true);
  } else if (saved !== 'rejected') {
    openBanner();
  }

  if (btnAccept) {
    btnAccept.addEventListener('click', () => {
      localStorage.setItem(CONSENT_KEY, 'accepted');
      banner.hidden = true;
      applyTracking(true);
    });
  }

  if (btnReject) {
    btnReject.addEventListener('click', () => {
      localStorage.setItem(CONSENT_KEY, 'rejected');
      banner.hidden = true;
    });
  }

  if (btnManage) {
    btnManage.addEventListener('click', () => {
      localStorage.removeItem(CONSENT_KEY);
      openBanner();
    });
  }
}

function initAiThemeFilter() {
  const select = document.getElementById('theme-filter');
  const grid = document.getElementById('ai-tools-grid');
  if (!select || !grid) return;

  const cards = Array.from(grid.querySelectorAll('.ai-card'));
  const apply = () => {
    const wanted = (select.value || 'all').toLowerCase();
    cards.forEach(card => {
      const theme = (card.dataset.theme || '').toLowerCase();
      const visible = wanted === 'all' || theme === wanted;
      card.style.display = visible ? '' : 'none';
    });
  };

  select.addEventListener('change', apply);
  apply();
}

function initPromptLibrary() {
  const select = document.getElementById('prompt-theme-filter');
  const search = document.getElementById('prompt-search');
  const favoritesOnly = document.getElementById('prompt-favorites-only');
  const grid = document.getElementById('prompt-library-grid');
  const results = document.getElementById('prompt-results-count');
  const randomBtn = document.getElementById('prompt-random');
  const resetBtn = document.getElementById('prompt-reset');
  const favKey = 'octetlab_prompt_favorites';

  const loadFavorites = () => {
    try {
      const raw = localStorage.getItem(favKey);
      const parsed = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(parsed) ? parsed : []);
    } catch (_error) {
      return new Set();
    }
  };

  const saveFavorites = (set) => {
    localStorage.setItem(favKey, JSON.stringify(Array.from(set)));
  };

  const favorites = loadFavorites();

  if (grid) {
    const cards = Array.from(grid.querySelectorAll('.prompt-card'));
    const favButtons = Array.from(grid.querySelectorAll('.fav-btn'));

    const updateFavButtons = () => {
      favButtons.forEach(btn => {
        const id = btn.getAttribute('data-fav-id') || '';
        const active = favorites.has(id);
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        btn.classList.toggle('is-active', active);
        btn.title = active ? 'Retirer des favoris' : 'Ajouter aux favoris';
      });

      cards.forEach(card => {
        const id = card.getAttribute('data-id') || '';
        card.classList.toggle('is-favorite', favorites.has(id));
      });
    };

    const apply = () => {
      const wantedTheme = (select ? (select.value || 'all') : 'all').toLowerCase();
      const q = (search ? (search.value || '') : '').trim().toLowerCase();
      const onlyFav = !!(favoritesOnly && favoritesOnly.checked);

      let visibleCount = 0;
      cards.forEach(card => {
        const theme = (card.dataset.theme || '').toLowerCase();
        const searchable = (card.dataset.search || '').toLowerCase();
        const id = card.getAttribute('data-id') || '';

        const themeOk = wantedTheme === 'all' || theme === wantedTheme;
        const searchOk = !q || searchable.includes(q);
        const favOk = !onlyFav || favorites.has(id);

        const visible = themeOk && searchOk && favOk;
        card.style.display = visible ? '' : 'none';
        if (visible) visibleCount += 1;
      });

      if (results) {
        results.textContent = `${visibleCount} prompt${visibleCount > 1 ? 's' : ''} affiché${visibleCount > 1 ? 's' : ''}`;
      }
    };

    favButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-fav-id') || '';
        if (!id) return;

        if (favorites.has(id)) favorites.delete(id);
        else favorites.add(id);

        saveFavorites(favorites);
        updateFavButtons();
        apply();
      });
    });

    if (select) select.addEventListener('change', apply);
    if (search) search.addEventListener('input', apply);
    if (favoritesOnly) favoritesOnly.addEventListener('change', apply);

    if (randomBtn) {
      randomBtn.addEventListener('click', () => {
        const visible = cards.filter(c => c.style.display !== 'none');
        if (!visible.length) return;
        const picked = visible[Math.floor(Math.random() * visible.length)];
        picked.scrollIntoView({ behavior: 'smooth', block: 'center' });
        picked.classList.add('prompt-highlight');
        setTimeout(() => picked.classList.remove('prompt-highlight'), 1200);
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (select) select.value = 'all';
        if (search) search.value = '';
        if (favoritesOnly) favoritesOnly.checked = false;
        apply();
      });
    }

    updateFavButtons();
    apply();
  }

  const buttons = Array.from(document.querySelectorAll('[data-copy-prompt]'));
  buttons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const targetId = btn.getAttribute('data-copy-prompt');
      const target = targetId ? document.getElementById(targetId) : null;
      const text = target ? target.textContent || '' : '';
      if (!text) return;

      try {
        await navigator.clipboard.writeText(text);
        const initial = btn.textContent;
        btn.textContent = 'Copié';
        setTimeout(() => {
          btn.textContent = initial || 'Copier le prompt';
        }, 1200);
      } catch (_error) {
        btn.textContent = 'Copie non supportée';
      }
    });
  });
}

initCookieBanner();
initAiThemeFilter();
initPromptLibrary();
