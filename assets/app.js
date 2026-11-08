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

// ── Actualités dynamiques via rss2json ─────────────────────────────────────
(function () {
  const newsList = document.getElementById('news-list');
  const modelNewsList = document.getElementById('model-news-list');
  if (!newsList && !modelNewsList) return;

  const API = 'https://api.rss2json.com/v1/api.json?rss_url=';
  const feeds = [
    { name: 'Numerama',        url: 'https://www.numerama.com/feed/' },
    { name: 'Korben',          url: 'https://korben.info/feed' },
    { name: 'Frandroid',       url: 'https://www.frandroid.com/feed' },
    { name: 'Clubic',          url: 'https://www.clubic.com/feed/news.rss' },
    { name: 'Journal du Geek', url: 'https://www.journaldugeek.com/feed/' },
    { name: 'Hugging Face',    url: 'https://huggingface.co/blog/feed.xml' },
  ];
  const MODEL_KEYWORDS = ['llama', 'mistral', 'qwen', 'gemma', 'phi', 'model', 'modèle', 'open source'];
  const PER_FEED = 4;
  const NEWS_TOTAL = 12;

  const fmt = (iso) => {
    const d = new Date(iso);
    return isNaN(d) ? '' : `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}`;
  };

  Promise.allSettled(
    feeds.map(f =>
      fetch(API + encodeURIComponent(f.url))
        .then(r => r.json())
        .then(data => (data.items || []).slice(0, PER_FEED).map(it => ({
          t: it.title,
          u: it.link,
          s: f.name,
          d: it.pubDate || '',
        })))
        .catch(() => [])
    )
  ).then(results => {
    const all = results.flatMap(r => r.status === 'fulfilled' ? r.value : []);
    all.sort((a, b) => new Date(b.d) - new Date(a.d));
    const news = all.slice(0, NEWS_TOTAL);

    if (newsList) {
      if (news.length === 0) {
        newsList.innerHTML = '<li>Les actualités apparaissent après la première mise à jour automatique.</li>';
      } else {
        newsList.innerHTML = news.map(n =>
          `<li><a href="${n.u}" target="_blank" rel="noopener noreferrer nofollow">${n.t}</a>` +
          `<small>${n.s} · ${fmt(n.d)}</small></li>`
        ).join('');
      }
    }

    if (modelNewsList) {
      const modelNews = news.filter(n => MODEL_KEYWORDS.some(k => n.t.toLowerCase().includes(k))).slice(0, 5);
      if (modelNews.length === 0) {
        modelNewsList.innerHTML = '<li>Les flux n\u2019ont pas encore remonté de nouveauté modèle.</li>';
      } else {
        modelNewsList.innerHTML = modelNews.map(n =>
          `<li><a href="${n.u}" target="_blank" rel="noopener noreferrer nofollow">${n.t}</a>` +
          `<small>${n.s} · ${fmt(n.d)}</small></li>`
        ).join('');
      }
    }
  });
})();


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
  if (!enabled || !clientId || !slotId) return;
  const container = document.getElementById('ad-slot-home');
  if (!container || container.querySelector('ins.adsbygoogle')) return;

  loadScript(`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${encodeURIComponent(clientId)}`, { crossorigin: 'anonymous' }, () => {
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
  const saved = localStorage.getItem(CONSENT_KEY);

  if (saved === 'accepted') {
    applyTracking(true);
    return;
  }
  if (saved === 'rejected') {
    return;
  }

  banner.hidden = false;

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

initCookieBanner();
initAiThemeFilter();
