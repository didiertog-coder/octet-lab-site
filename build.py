#!/usr/bin/env python3
"""Génère le site statique dans public/ — usage : python build.py (Python 3.9+, aucune dépendance)."""
import email.utils
import gzip
import html
import json
import re
import shutil
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# ── Constantes globales ───────────────────────────────────────────────────────
ROOT = Path(__file__).parent
OUT  = ROOT / "public"
CFG  = json.loads((ROOT / "config.json").read_text("utf-8"))
esc  = html.escape
AT   = "{http://www.w3.org/2005/Atom}"

# Content-Security-Policy partagée (HTML + _headers + .htaccess)
_CSP = (
    "default-src 'self'; "
    "img-src 'self' https: data:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "script-src 'self' https://www.googletagmanager.com "
        "https://pagead2.googlesyndication.com https://plausible.io "
        "https://cdn.umami.is; "
    "connect-src 'self' https://www.google-analytics.com "
        "https://region1.google-analytics.com https://plausible.io "
        "https://cdn.umami.is; "
    "frame-src https://googleads.g.doubleclick.net "
        "https://tpc.googlesyndication.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'; "
    "upgrade-insecure-requests"
)

# Headers RSS : User-Agent complet pour éviter les 403
_RSS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*;q=0.9",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
}
_RSS_RETRIES = 2
_RSS_TIMEOUT = 12

# Jours et mois en français pour la date du header
_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS  = ["", "janvier", "février", "mars", "avril", "mai", "juin",
          "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


# ── Utilitaires Markdown ──────────────────────────────────────────────────────

def inline(t):
    """Convertit le Markdown inline (gras, code, liens) en HTML."""
    t = esc(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" rel="noopener noreferrer">\1</a>', t)
    return t


def md(text):
    """Convertit un texte Markdown en HTML (titres, paragraphes, listes, blocs de code, tableaux)."""
    out, para, items, code = [], [], [], None

    def flush():
        nonlocal para, items
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
            para = []
        if items:
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(i) for i in items))
            items = []

    for line in text.splitlines():
        # Bloc de code
        if line.startswith("```"):
            if code is None:
                flush()
                code = []
            else:
                out.append("<pre><code>%s</code></pre>" % esc("\n".join(code)))
                code = None
            continue
        if code is not None:
            code.append(line)
            continue

        # Titres
        m = re.match(r"(#{2,3}) (.+)", line)
        if m:
            flush()
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl))
            continue

        # Tableau Markdown (ligne avec |)
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # Ligne séparatrice (---)
            if all(re.match(r"-+", c) for c in cells if c):
                continue
            # Première ligne → <thead>, suivantes → <tbody> géré en post-traitement
            out.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in cells))
            continue

        # Listes
        if line.startswith("- "):
            if para:
                flush()
            items.append(line[2:])
            continue

        # Ligne vide
        if not line.strip():
            flush()
            continue

        # Paragraphe
        if items:
            flush()
        para.append(line.strip())

    flush()

    # Enveloppe les lignes <tr> dans un <table>
    result = "\n".join(out)
    result = re.sub(
        r"(<tr>.*?</tr>(?:\n<tr>.*?</tr>)*)",
        lambda m: "<table>" + m.group(1) + "</table>",
        result,
        flags=re.DOTALL,
    )
    return result


# ── Chargement des fichiers Markdown ─────────────────────────────────────────

def load(path):
    """Lit un fichier .md avec frontmatter YAML minimal (title, description, category)."""
    raw, meta = path.read_text("utf-8"), {}
    if raw.startswith("---"):
        _, head, raw = raw.split("---", 2)
        for line in head.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    meta["slug"] = path.stem
    return meta, md(raw.strip())


# ── Parsing de dates RSS ──────────────────────────────────────────────────────

def pdate(s):
    """Parse une date RSS (RFC 2822 ou ISO 8601) en datetime UTC."""
    try:
        d = email.utils.parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def txt(el, *names):
    """Retourne le texte du premier élément XML trouvé parmi names."""
    for n in names:
        e = el.find(n)
        if e is not None and (e.text or "").strip():
            return e.text.strip()
    return ""


# ── Récupération des flux RSS ─────────────────────────────────────────────────

def _fetch_url(url):
    """Télécharge une URL avec retries et gestion explicite des erreurs HTTP."""
    last_exc = None
    for attempt in range(1 + _RSS_RETRIES):
        try:
            req = urllib.request.Request(url, headers=_RSS_HEADERS)
            with urllib.request.urlopen(req, timeout=_RSS_TIMEOUT) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding", "") == "gzip":
                    data = gzip.decompress(data)
                return data
        except urllib.error.HTTPError as e:
            last_exc = e
            if e.code in (401, 403, 404, 410):
                raise  # Erreur permanente : pas de retry
            if attempt < _RSS_RETRIES:
                time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            last_exc = e
            if attempt < _RSS_RETRIES:
                time.sleep(1.0)
    raise last_exc


def fetch_news():
    """Récupère et fusionne les actualités de tous les flux RSS configurés."""
    items = []
    for f in CFG["feeds"]:
        try:
            raw = _fetch_url(f["url"])
            root = ET.fromstring(raw)
        except Exception as e:
            print("Flux ignoré :", f["name"], "-", type(e).__name__, str(e)[:120])
            continue
        got = []
        for it in list(root.iter("item")) + list(root.iter(AT + "entry")):
            link = txt(it, "link")
            le = it.find(AT + "link")
            if le is not None and le.get("href"):
                link = le.get("href")
            title = txt(it, "title", AT + "title")
            if title and link.startswith("http"):
                got.append({
                    "t": title,
                    "u": link,
                    "s": f["name"],
                    "d": pdate(txt(it, "pubDate", AT + "published", AT + "updated")),
                })
        items += got[:CFG["per_feed"]]
    items.sort(key=lambda x: x["d"], reverse=True)
    return items[:CFG["news_total"]]


# ── Accès sécurisé à la config ────────────────────────────────────────────────

def cfg(path, default=""):
    """Lit une valeur imbriquée dans CFG sans lever d'exception."""
    ref = CFG
    for key in path:
        if not isinstance(ref, dict) or key not in ref:
            return default
        ref = ref[key]
    return ref


# ── Génération du layout HTML commun ─────────────────────────────────────────

def layout(title, desc, body, depth=0):
    """Retourne le HTML complet d'une page (head + nav + body + footer)."""
    r    = "../" * depth
    year = datetime.now().year
    now  = datetime.now()
    date_fr = f"{_JOURS[now.weekday()]} {now.day} {_MOIS[now.month]} {now.year}"

    legal = (
        f'<a href="{r}mentions-legales.html">Mentions légales</a> · '
        f'<a href="{r}politique-confidentialite.html">Confidentialité</a> · '
        f'<a href="{r}politique-cookies.html">Cookies</a> · '
        f'<a href="{r}cgu.html">CGU</a>'
    )

    body_attrs = {
        "data-ga4":               cfg(["analytics", "ga4_measurement_id"]),
        "data-plausible-domain":  cfg(["analytics", "plausible_domain"]),
        "data-umami-script":      cfg(["analytics", "umami_script_url"]),
        "data-umami-id":          cfg(["analytics", "umami_website_id"]),
        "data-adsense-enabled":   "1" if cfg(["adsense", "enabled"], False) else "0",
        "data-adsense-client":    cfg(["adsense", "client_id"]),
        "data-adsense-slot-home": cfg(["adsense", "slot_home_top"]),
    }
    attrs = " ".join(f'{k}="{esc(str(v))}"' for k, v in body_attrs.items())

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta http-equiv="Content-Security-Policy" content="{_CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="DENY">
<meta http-equiv="Permissions-Policy" content="geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600&family=Space+Mono&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}assets/style.css">
</head>
<body {attrs}>
<header class="bar">
  <div class="bar-left">
    <span class="date-badge">&#128197; {date_fr}</span>
    <a class="logo" href="{r}index.html">{esc(CFG['site_name'])}</a>
  </div>
  <nav>
    <a href="{r}index.html#guides">Guides</a>
    <a href="{r}index.html#actus">Actualités</a>
    <a href="{r}index.html#materiel">Matériel</a>
    <a href="{r}ia-thematiques.html">IA thématiques</a>
  </nav>
</header>
{body}
<div id="cookie-banner" class="cookie-banner" hidden>
  <p>Nous utilisons des cookies de mesure d\u2019audience et publicitaires pour améliorer le site.
     <a href="{r}politique-cookies.html">En savoir plus</a>.</p>
  <div>
    <button id="cookie-accept" type="button">Accepter</button>
    <button id="cookie-reject" type="button">Refuser</button>
  </div>
</div>
<footer>
  <p>{esc(CFG['disclosure'])}</p>
  <p>{legal}</p>
  <p>\u00a9 {year} {esc(CFG.get('copyright_holder', 'BinaryForge'))}. Tous droits réservés.</p>
</footer>
<script src="{r}assets/app.js" defer></script>
</body>
</html>"""


# ── Corps de la page d'accueil ────────────────────────────────────────────────

def index_body(guides, news):
    """Génère le corps HTML de index.html."""
    cards = "".join(
        f'<a class="card" href="guides/{g["slug"]}.html">'
        f'<span class="tag">{esc(g.get("category", ""))}</span>'
        f'<h3>{esc(g["title"])}</h3>'
        f'<p>{esc(g.get("description", ""))}</p>'
        f'</a>'
        for g in guides
    )

    lis = "".join(
        f'<li><a href="{esc(n["u"])}" target="_blank" rel="noopener noreferrer nofollow">'
        f'{esc(n["t"])}</a>'
        f'<small>{esc(n["s"])}</small>'
        f'<small>{n["d"]:%d/%m}</small></li>'
        for n in news
    ) or "<li>Les actualités apparaissent après la première mise à jour automatique.</li>"

    model_keywords = ("llama", "mistral", "qwen", "gemma", "phi", "model", "modèle", "open source")
    model_rss = [n for n in news if any(k in n["t"].lower() for k in model_keywords)][:5]
    model_rss_html = "".join(
        f'<li><a href="{esc(n["u"])}" target="_blank" rel="noopener noreferrer nofollow">'
        f'{esc(n["t"])}</a>'
        f'<small>{esc(n["s"])} · {n["d"]:%d/%m}</small></li>'
        for n in model_rss
    ) or "<li>Les flux n\u2019ont pas encore remonté de nouveauté modèle.</li>"

    spotlight_html = "".join(
        f'<article class="model-card">'
        f'<h3>{esc(m.get("name", "Modèle IA"))}</h3>'
        f'<p><strong>Usage :</strong> {esc(m.get("mode", "Non précisé"))}</p>'
        f'<p><strong>Tarif :</strong> {esc(m.get("pricing", "Non précisé"))}</p>'
        f'<p><strong>Supports :</strong> {esc(m.get("supports", "Non précisé"))}</p>'
        f'<p><strong>Variantes :</strong> {esc(m.get("variants", "Non précisé"))}</p>'
        f'<p class="pro"><strong>Avantages :</strong> {esc(m.get("pros", ""))}</p>'
        f'<p class="con"><strong>Inconvénients :</strong> {esc(m.get("cons", ""))}</p>'
        f'<p><a href="{esc(m.get("url", "#"))}" target="_blank" rel="noopener noreferrer nofollow">Voir le modèle</a></p>'
        f'</article>'
        for m in CFG.get("model_spotlight", [])[:4]
    )

    part = "".join(
        f'<a class="card" href="{esc(p["url"])}" target="_blank" rel="sponsored noopener noreferrer">'
        f'<h3>{esc(p["name"])}</h3>'
        f'<p>{esc(p["desc"])}</p>'
        f'<span class="tag">Lien partenaire</span>'
        f'</a>'
        for p in CFG["partners"]
    )

    ad_block = (
        '<section class="full" id="monetisation"><h2>Publicité</h2>'
        '<div id="ad-slot-home" class="partners"></div></section>'
        if cfg(["adsense", "enabled"], False) else ""
    )

    return f"""
<section class="hero">
  <div class="hero-copy">
    <h1>{esc(CFG['tagline'])}</h1>
    <p class="lead">Comprendre, choisir, installer. Les guides sont complétés régulièrement
       et l'actualité du secteur se met à jour chaque jour.</p>
    <div class="word-box">
      <h2>Un petit mot pour vous ...</h2>
      <p>Merci de visiter OCTET LAB. Ce site est pensé pour vous aider à comprendre l\u2019IA
         simplement, choisir les bons outils et avancer à votre rythme.</p>
      <p>Astuce : commencez par les guides essentiels puis explorez la page IA thématique
         selon vos besoins.</p>
    </div>
    <p class="help-inline">Aide rapide : commencez par un guide de niveau débutant,
       puis utilisez l\u2019estimateur pour valider la VRAM avant achat.</p>
  </div>
  <div class="hero-side">
    <form id="vram" class="est" aria-label="Estimateur de VRAM">
      <h2>Estimer la VRAM d'un modèle</h2>
      <p class="help-inline help-inline--accent">Besoin d\u2019aide ? Modifiez un paramètre
         à la fois pour comparer facilement les besoins mémoire.</p>
      <label>Taille du modèle (milliards de paramètres)
        <input name="params" type="number" value="8" min="1" max="400">
      </label>
      <label>Quantification
        <select name="quant">
          <option value="0.6">Q4 (équilibré)</option>
          <option value="0.72">Q5</option>
          <option value="1.1">Q8</option>
          <option value="2.1">FP16 (sans compression)</option>
        </select>
      </label>
      <label>Contexte
        <select name="ctx">
          <option value="0.5">4k tokens</option>
          <option value="1" selected>8k tokens</option>
          <option value="2">16k tokens</option>
          <option value="4">32k tokens</option>
        </select>
      </label>
      <p id="vram-out" class="out" aria-live="polite"></p>
    </form>
  </div>
</section>
<div class="wrap">
  <main id="guides">
    <h2>Guides</h2>
    <p class="help-inline">Astuce : ouvrez les guides dans l\u2019ordre de complexité pour progresser sans bloquer.</p>
    <div class="grid">{cards}</div>
    <section class="side-block models-left">
      <h2>Nouveaux modèles IA</h2>
      <p class="help-inline help-inline--accent">Veille rapide : avantages, limites, tarifs et supports techniques.</p>
      <div class="model-grid">{spotlight_html}</div>
      <h3>Tendance RSS modèles</h3>
      <ul class="news model-news">{model_rss_html}</ul>
    </section>
  </main>
  <aside id="actus">
    <section class="side-block">
      <h2>Actualités du jour</h2>
      <p class="help-inline">Les liens externes s\u2019ouvrent dans un nouvel onglet pour garder votre progression.</p>
      <ul class="news">{lis}</ul>
    </section>
  </aside>
</div>
<section class="full" id="materiel">
  <h2>Matériel et logiciels</h2>
  <p class="help-inline">Transparence : les blocs ci-dessous sont des liens partenaires monétisables.</p>
  <div class="partners">{part}</div>
</section>
{ad_block}"""


# ── Corps de la page IA thématiques ──────────────────────────────────────────

def ai_tools_body():
    """Génère le corps HTML de ia-thematiques.html."""
    order = {"gratuit": 0, "freemium": 1, "payant": 2}
    tools = sorted(
        CFG.get("ai_tools", []),
        key=lambda x: (order.get(str(x.get("pricing", "")).lower(), 3), x.get("theme", ""), x.get("name", "")),
    )
    themes  = sorted({t.get("theme", "Autre") for t in tools})
    options = '<option value="all">Toutes les thématiques</option>' + "".join(
        f'<option value="{esc(t)}">{esc(t)}</option>' for t in themes
    )
    cards = "".join(
        f'<article class="card ai-card" data-theme="{esc(t.get("theme", "Autre"))}">'
        f'<span class="tag">{esc(t.get("theme", "Autre"))}</span>'
        f'<h3>{esc(t.get("name", "IA"))}</h3>'
        f'<p><strong>Finalité :</strong> {esc(t.get("purpose", ""))}</p>'
        f'<p><strong>Tarif :</strong> {esc(t.get("pricing", "Non précisé"))}</p>'
        f'<p><a href="{esc(t.get("url", "#"))}" target="_blank" rel="noopener noreferrer nofollow">Accéder à l\u2019outil</a></p>'
        f'</article>'
        for t in tools
    )
    return f"""
<section class="full">
  <article class="prose prose-wide">
    <div class="page-head">
      <h1>IA classées par thématiques</h1>
      <a class="btn-back" href="index.html">\u2190 Retour à la page principale</a>
    </div>
    <p class="lead">Comparez rapidement les outils selon leur finalité, leur prix et leur catégorie.</p>
    <p class="help-inline help-inline--accent">Aide : utilisez le filtre pour afficher uniquement la thématique qui vous intéresse.</p>
    <div class="tool-actions">
      <label for="theme-filter">Thématique</label>
      <select id="theme-filter" aria-label="Filtrer les IA par thématique">{options}</select>
    </div>
    <div id="ai-tools-grid" class="grid ai-grid">{cards}</div>
  </article>
</section>"""


# ── Fichiers de sécurité serveur ──────────────────────────────────────────────

def write_security_files():
    """Génère _headers (Netlify/Cloudflare) et .htaccess (Apache)."""
    headers_txt = f"""/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()
  Content-Security-Policy: {_CSP}
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-XSS-Protection: 1; mode=block
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Resource-Policy: same-origin
"""
    (OUT / "_headers").write_text(headers_txt, "utf-8")

    htaccess_txt = """# Sécurité HTTP — généré automatiquement par build.py
<IfModule mod_headers.c>
    Header always set X-Frame-Options "DENY"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Cross-Origin-Opener-Policy "same-origin"
    Header always set Cross-Origin-Resource-Policy "same-origin"
</IfModule>
Options -Indexes
ServerSignature Off
"""
    (OUT / ".htaccess").write_text(htaccess_txt, "utf-8")


# ── Point d'entrée principal ──────────────────────────────────────────────────

def main():
    """Construit le site complet dans public/."""
    shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "guides").mkdir(parents=True)
    shutil.copytree(ROOT / "assets", OUT / "assets")

    # Guides
    guides = []
    for p in sorted((ROOT / "guides").glob("*.md")):
        meta, body = load(p)
        guides.append(meta)
        page = (
            f'<article class="prose">'
            f'<h1>{esc(meta["title"])}</h1>'
            f'{body}'
            f'<p><a href="../index.html">← Retour aux guides</a></p>'
            f'</article>'
        )
        (OUT / "guides" / f"{meta['slug']}.html").write_text(
            layout(meta["title"] + " | " + CFG["site_name"], meta.get("description", ""), page, depth=1),
            "utf-8",
        )

    # Pages légales
    for p in (ROOT / "pages").glob("*.md"):
        meta, body = load(p)
        (OUT / f"{meta['slug']}.html").write_text(
            layout(meta["title"], meta["title"], f'<article class="prose"><h1>{esc(meta["title"])}</h1>{body}</article>'),
            "utf-8",
        )

    # Pages principales
    news = fetch_news()
    (OUT / "index.html").write_text(
        layout(CFG["site_name"] + " : " + CFG["tagline"], CFG["tagline"], index_body(guides, news)),
        "utf-8",
    )
    (OUT / "ia-thematiques.html").write_text(
        layout("IA par thématiques | " + CFG["site_name"], "Catalogue d\u2019IA triable par thématique, finalité et prix.", ai_tools_body()),
        "utf-8",
    )

    # Sitemap
    urls = (
        ["index.html", "ia-thematiques.html"]
        + [f"guides/{g['slug']}.html" for g in guides]
        + [f"{p.stem}.html" for p in (ROOT / "pages").glob("*.md")]
    )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{CFG['base_url']}/{u}</loc></url>" for u in urls)
        + "</urlset>"
    )
    (OUT / "sitemap.xml").write_text(sitemap, "utf-8")

    # robots.txt
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {CFG['base_url']}/sitemap.xml\n",
        "utf-8",
    )

    # Fichiers de sécurité
    write_security_files()

    print(f"OK : {len(guides)} guides, {len(news)} actualités")


if __name__ == "__main__":
    main()
