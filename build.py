#!/usr/bin/env python3
"""Génère le site statique dans public/ — usage : python build.py (Python 3.9+, aucune dépendance)."""
import email.utils
import gzip
import html
import json
import re
import shutil
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
        "https://cdn.umami.is https://googleads.g.doubleclick.net "
        "https://pagead2.googlesyndication.com https://tpc.googlesyndication.com; "
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


def _entry_link(it):
    """Extrait le lien d'un item RSS/Atom (texte, href Atom, guid)."""
    link = txt(it, "link")
    if link.startswith("http"):
        return link

    atom_links = list(it.findall(AT + "link"))
    for le in atom_links:
        href = (le.get("href") or "").strip()
        rel = (le.get("rel") or "alternate").strip().lower()
        if href.startswith("http") and rel in ("alternate", ""):
            return href
    for le in atom_links:
        href = (le.get("href") or "").strip()
        if href.startswith("http"):
            return href

    plain_link = it.find("link")
    if plain_link is not None:
        href = (plain_link.get("href") or "").strip()
        if href.startswith("http"):
            return href

    guid = txt(it, "guid")
    if guid.startswith("http"):
        return guid

    return ""


def fetch_news():
    """Récupère et fusionne les actualités de tous les flux RSS configurés."""
    items = []
    for f in CFG["feeds"]:
        try:
            raw = _fetch_url(f["url"])
            try:
                root = ET.fromstring(raw)
            except ET.ParseError:
                # Certains flux (ex: agrégateurs) contiennent des '&' non échappés
                repaired = re.sub(r"&(?!#?\w+;)", "&amp;", raw.decode("utf-8", "ignore"))
                root = ET.fromstring(repaired.encode("utf-8"))
        except Exception as e:
            print("Flux ignoré :", f["name"], "-", type(e).__name__, str(e)[:120])
            continue

        got = []
        for it in list(root.iter("item")) + list(root.iter(AT + "entry")):
            title = txt(it, "title", AT + "title")
            link = _entry_link(it)
            date_txt = txt(it, "pubDate", AT + "published", AT + "updated", "date")
            if title and link.startswith("http"):
                got.append({
                    "t": title,
                    "u": link,
                    "s": f["name"],
                    "d": pdate(date_txt),
                })

        items += got[:CFG["per_feed"]]

    items.sort(key=lambda x: x["d"], reverse=True)

    # Dé-duplication (URL) pour ne garder que les plus récentes
    deduped, seen = [], set()
    for it in items:
        key = it["u"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    # Toujours afficher les plus récentes en premier
    return deduped[:CFG["news_total"]]


# ── Accès sécurisé à la config ────────────────────────────────────────────────

def cfg(path, default=""):
    """Lit une valeur imbriquée dans CFG sans lever d'exception."""
    ref = CFG
    for key in path:
        if not isinstance(ref, dict) or key not in ref:
            return default
        ref = ref[key]
    return ref


_GUIDE_STOPWORDS = {
    "avec", "dans", "pour", "sans", "votre", "vous", "guide", "local",
    "site", "petit", "comment", "entre", "plus", "moins", "tous", "tout",
    "vers", "chez", "etre", "cette", "faire", "base", "mise", "jour",
    "the", "and", "from", "that", "this"
}


def guide_tokens(meta):
    """Retourne un set de tokens utiles pour relier les guides entre eux."""
    raw = " ".join([
        str(meta.get("title", "")),
        str(meta.get("description", "")),
        str(meta.get("category", "")),
    ]).lower()
    words = re.findall(r"[a-z0-9àâçéèêëîïôûùüÿñæœ-]+", raw)
    tokens = set()
    for word in words:
        token = word.strip("-")
        if len(token) < 4 or token in _GUIDE_STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def build_related_guides(guides, limit=3):
    """Calcule des recommandations internes par similarité de catégorie et de thèmes."""
    by_slug = {}
    token_cache = {g["slug"]: guide_tokens(g) for g in guides}

    for guide in guides:
        g_slug = guide["slug"]
        g_cat = str(guide.get("category", "")).strip().lower()
        g_tokens = token_cache.get(g_slug, set())
        ranked = []

        for other in guides:
            o_slug = other["slug"]
            if o_slug == g_slug:
                continue

            score = 0
            o_cat = str(other.get("category", "")).strip().lower()
            if g_cat and o_cat and g_cat == o_cat:
                score += 4

            overlap = len(g_tokens & token_cache.get(o_slug, set()))
            score += overlap
            if score <= 0:
                continue

            ranked.append((score, other.get("title", ""), other))

        ranked.sort(key=lambda x: (-x[0], x[1]))
        by_slug[g_slug] = [entry[2] for entry in ranked[:limit]]

    return by_slug


def default_guide_faq(meta):
    """FAQ générique de base quand aucune FAQ dédiée n'est configurée."""
    title = str(meta.get("title", "ce guide")).strip()
    category = str(meta.get("category", "")).strip() or "ce sujet"

    return [
        {
            "question": f"À qui s’adresse le guide « {title} » ?",
            "answer": "Ce guide s’adresse aux profils débutants à intermédiaires qui veulent appliquer une méthode claire sans jargon inutile.",
        },
        {
            "question": f"Par quoi commencer pour progresser sur {category} ?",
            "answer": "Commencez par appliquer les étapes dans l’ordre, validez chaque checkpoint, puis passez à une optimisation mesurable.",
        },
        {
            "question": "Comment éviter les erreurs courantes ?",
            "answer": "Préparez une checklist, testez sur un périmètre réduit et documentez les changements avant de généraliser en production.",
        },
    ]


def resolve_amazon_affiliate_tag():
    """Retourne le tag Amazon configuré explicitement ou présent dans le lien partenaire Amazon."""
    explicit_tag = str(CFG.get("amazon_affiliate_tag", "")).strip()
    if explicit_tag:
        return explicit_tag

    for partner in CFG.get("partners", []):
        url = str(partner.get("url", "")).strip()
        if not url:
            continue

        host = urlsplit(url).netloc.lower()
        if "amazon." not in host:
            continue

        for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=True):
            if key.lower() == "tag" and value.strip():
                return value.strip()

    return ""


def add_amazon_affiliate_tag(url, tag):
    """Ajoute le tag d'affiliation aux URLs Amazon si absent."""
    if not tag:
        return url

    clean_url = str(url or "").strip()
    if not clean_url:
        return clean_url

    split = urlsplit(clean_url)
    if "amazon." not in split.netloc.lower():
        return clean_url

    query = parse_qsl(split.query, keep_blank_values=True)
    if any(key.lower() == "tag" and value.strip() for key, value in query):
        return clean_url

    query.append(("tag", tag))
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


# ── Génération du layout HTML commun ─────────────────────────────────────────

def build_absolute_url(page_path):
    """Construit une URL absolue propre à partir de base_url et d'un chemin relatif."""
    clean_path = str(page_path or "index.html").lstrip("/")
    base = CFG["base_url"].rstrip("/")
    return f"{base}/{clean_path}"


def slugify(value):
    """Convertit un titre en slug URL ASCII stable."""
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or "prompt"


def prompt_slug(prompt):
    return str(prompt.get("slug", "")).strip() or slugify(prompt.get("title", ""))


def prompt_tags(prompt):
    tags = list(prompt.get("tags", [])) if isinstance(prompt.get("tags", []), list) else []
    tags.extend([
        prompt.get("theme", "Autre"),
        prompt.get("difficulty", "Intermédiaire"),
    ])
    models = prompt.get("models", ["GPT", "Claude", "Copilot", "Gemini"])
    if isinstance(models, list):
        tags.extend(models)
    return list(dict.fromkeys(str(tag).strip() for tag in tags if str(tag).strip()))


def prompt_collections(prompt):
    tags_text = " ".join(prompt_tags(prompt)).lower()
    theme = str(prompt.get("theme", "")).lower()
    collections = ["all"]

    if any(k in theme for k in ("développement", "automatisation", "analyse", "sécurité", "data")):
        collections.append("developers")
    if any(k in tags_text for k in ("marketing", "rédaction", "réseaux", "image", "seo")):
        collections.append("creators")
    if any(k in tags_text for k in ("marketing", "vente", "support", "productivité", "gestion", "data", "sécurité", "seo")):
        collections.append("pme")
    if any(k in tags_text for k in ("seo", "marketing", "réseaux")):
        collections.append("seo")

    return list(dict.fromkeys(collections))


def layout(title, desc, body, depth=0, page_path="index.html"):
    """Retourne le HTML complet d'une page (head + nav + body + footer)."""
    r    = "../" * depth
    year = datetime.now().year
    now  = datetime.now()
    date_fr = f"{_JOURS[now.weekday()]} {now.day} {_MOIS[now.month]} {now.year}"

    canonical_url = build_absolute_url(page_path)
    is_home = page_path == "index.html"
    is_guide = str(page_path).startswith("guides/")
    og_type = "article" if is_guide else "website"

    base_org = {
        "@type": "Organization",
        "name": CFG.get("owner_name", CFG.get("site_name", "BinaryForge")),
        "url": CFG["base_url"],
    }

    if is_home:
        structured_data = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": CFG["site_name"],
            "url": CFG["base_url"],
            "description": desc,
            "inLanguage": "fr-FR",
            "publisher": base_org,
        }
    elif is_guide:
        structured_data = {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": title,
            "description": desc,
            "inLanguage": "fr-FR",
            "url": canonical_url,
            "mainEntityOfPage": canonical_url,
            "author": base_org,
            "publisher": base_org,
            "dateModified": datetime.now(timezone.utc).date().isoformat(),
        }
    else:
        structured_data = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": desc,
            "url": canonical_url,
            "inLanguage": "fr-FR",
            "isPartOf": {
                "@type": "WebSite",
                "name": CFG["site_name"],
                "url": CFG["base_url"],
            },
        }

    json_ld = json.dumps(structured_data, ensure_ascii=False).replace("</", "<\\/")

    legal = (
        f'<a href="{r}mentions-legales.html">Mentions légales</a> · '
        f'<a href="{r}politique-confidentialite.html">Confidentialité</a> · '
        f'<a href="{r}politique-cookies.html">Cookies</a> · '
        f'<a href="{r}cgu.html">CGU</a> · '
        f'<a href="mailto:{esc(CFG["contact_email"])}">Contact</a>'
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
    adsense_meta = ""
    adsense_client = cfg(["adsense", "client_id"]).strip()
    if cfg(["adsense", "enabled"], False) and adsense_client:
        adsense_meta = f'\n<meta name="google-adsense-account" content="{esc(adsense_client)}">'

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{esc(canonical_url)}">
<meta property="og:locale" content="fr_FR">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(CFG['site_name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical_url)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">{adsense_meta}
<meta http-equiv="Content-Security-Policy" content="{_CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="DENY">
<meta http-equiv="Permissions-Policy" content="geolocation=(), microphone=(), camera=(), payment=(), usb=(), interest-cohort=()">
<script type="application/ld+json">{json_ld}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;600&family=Space+Mono&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{r}assets/style.css">
</head>
<body {attrs}>
<header class="bar">
  <div class="bar-left">
    <span class="date-badge" id="live-date">&#128197; {date_fr}</span>
    <a class="logo" href="{r}index.html">{esc(CFG['site_name'])}</a>
  </div>
  <nav>
    <a href="{r}index.html#guides">Guides</a>
    <a href="{r}index.html#actus">Actualités</a>
    <a href="{r}index.html#materiel">Matériel</a>
    <a href="{r}ia-thematiques.html">IA thématiques</a>
    <a href="{r}prompts-utiles.html">Prompts utiles</a>
    <span class="visit-counter" id="visit-counter" aria-live="polite" title="Compteur local (ce navigateur)">Visites : --</span>
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
  <p><button id="cookie-manage" type="button" class="link-button">Gérer mes cookies</button></p>
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

    amazon_tag = resolve_amazon_affiliate_tag()

    part = "".join(
        f'<a class="card" href="{esc(add_amazon_affiliate_tag(p["url"], amazon_tag))}" target="_blank" rel="sponsored noopener noreferrer">'
        f'<h3>{esc(p["name"])}</h3>'
        f'<p>{esc(p["desc"])}</p>'
        f'<span class="tag">Lien partenaire</span>'
        f'</a>'
        for p in CFG["partners"]
    )

    resources_cards = "".join(
        f'<a class="card resource-card" href="{esc(r.get("url", "#"))}" target="_blank" rel="noopener noreferrer nofollow">'
        f'<span class="tag">{esc(r.get("type", "Ressource"))}</span>'
        f'<h3>{esc(r.get("name", "Ressource IA"))}</h3>'
        f'<p>{esc(r.get("desc", ""))}</p>'
        f'</a>'
        for r in CFG.get("ai_resources", [])[:8]
    )

    resources_block = (
        '<section class="full" id="ressources-ia">'
        '<h2>Ressources IA incontournables</h2>'
        '<p class="help-inline help-inline--accent">Sélection utile pour les passionnés : benchmarks, datasets, leaderboards, papier et veille technique.</p>'
        f'<div class="partners resources-grid">{resources_cards}</div>'
        '</section>'
        if resources_cards else ""
    )

    lab_keywords = (
        "open source", "benchmark", "llm", "agent", "model", "modèle", "dataset",
        "release", "nouveau", "paper", "fine-tune", "embedding", "rag"
    )
    deals_keywords = (
        "promo", "bon plan", "soldes", "black friday", "amazon", "gpu", "ssd", "pc", "nas", "ryzen"
    )

    lab_news = [n for n in news if any(k in n["t"].lower() for k in lab_keywords)][:6]
    deals_news = [n for n in news if any(k in n["t"].lower() for k in deals_keywords)][:6]

    lab_news_html = "".join(
        f'<li><a href="{esc(n["u"])}" target="_blank" rel="noopener noreferrer nofollow">{esc(n["t"])}</a>'
        f'<small>{esc(n["s"])} · {n["d"]:%d/%m}</small></li>'
        for n in lab_news
    ) or "<li>La veille IA du jour sera visible après la prochaine mise à jour RSS.</li>"

    deals_news_html = "".join(
        f'<li><a href="{esc(n["u"])}" target="_blank" rel="noopener noreferrer nofollow">{esc(n["t"])}</a>'
        f'<small>{esc(n["s"])} · {n["d"]:%d/%m}</small></li>'
        for n in deals_news
    ) or "<li>Les bons plans matériel apparaîtront après la prochaine collecte RSS.</li>"

    daily_rss_block = (
        '<section class="full rss-rubrics" id="veille-quotidienne">'
        '<h2>Rubriques quotidiennes IA</h2>'
        '<p class="help-inline">Mise à jour automatique chaque jour via RSS : veille technique + opportunités matériel.</p>'
        '<div class="daily-columns">'
        '<article class="side-block"><h3>Veille IA & produits</h3><ul class="news">' + lab_news_html + '</ul></article>'
        '<article class="side-block"><h3>Bons plans matériel (RSS)</h3><ul class="news">' + deals_news_html + '</ul></article>'
        '</div>'
        '</section>'
    )

    daily_products = CFG.get("amazon_daily_products", [])

    products_cards = ""
    if daily_products:
        day_seed = datetime.now(timezone.utc).timetuple().tm_yday
        picks = []
        count = min(3, len(daily_products))
        for i in range(count):
            picks.append(daily_products[(day_seed + i) % len(daily_products)])

        products_cards = "".join(
            f'<a class="card" href="{esc(add_amazon_affiliate_tag(p.get("url", "#"), amazon_tag))}" target="_blank" rel="sponsored noopener noreferrer">'
            f'<span class="tag">Amazon · sélection du jour</span>'
            f'<h3>{esc(p.get("name", "Produit Amazon"))}</h3>'
            f'<p>{esc(p.get("desc", ""))}</p>'
            f'</a>'
            for p in picks
        )

    daily_amazon_block = (
        '<section class="full" id="amazon-du-jour">'
        '<h2>Produits Amazon du jour</h2>'
        '<p class="help-inline help-inline--accent">Sélection renouvelée quotidiennement pour les passionnés d’IA locale (liens partenaires).</p>'
        f'<div class="partners amazon-daily-grid">{products_cards}</div>'
        '</section>'
        if products_cards else ""
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
    <div class="kpi-strip" aria-label="Repères clés">
      <article><strong>17+</strong><span>guides experts</span></article>
      <article><strong>MAJ / jour</strong><span>veille RSS automatisée</span></article>
      <article><strong>100 % local-first</strong><span>focus IA pratique</span></article>
    </div>
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
    <p class="help-inline help-inline--accent">Nouveau : <a href="prompts-utiles.html">accédez à la bibliothèque de prompts utiles</a> classés par thèmes.</p>
    <div class="expert-pillars" aria-label="Piliers éditoriaux">
      <article><h3>IA locale utile</h3><p>Tutoriels actionnables orientés usage réel, pas théorie abstraite.</p></article>
      <article><h3>Matériel dimensionné</h3><p>Choix composants selon modèles cibles, performance et budget.</p></article>
      <article><h3>Sécurité & conformité</h3><p>Approche responsable : protection des données, RGPD, transparence.</p></article>
    </div>
    <div class="grid">{cards}</div>
    <section class="side-block models-left">
      <h2>Nouveaux modèles IA</h2>
      <p class="help-inline help-inline--accent">Veille rapide : avantages, limites, tarifs et supports techniques.</p>
      <div class="model-grid">{spotlight_html}</div>
      <h3>Tendance RSS modèles</h3>
      <ul class="news model-news" id="model-news-list">{model_rss_html}</ul>
    </section>
  </main>
  <aside id="actus">
    <section class="side-block">
      <h2>Actualités du jour</h2>
      <p class="help-inline">Les liens externes s\u2019ouvrent dans un nouvel onglet pour garder votre progression.</p>
      <ul class="news" id="news-list">{lis}</ul>
    </section>
  </aside>
</div>
{resources_block}
{daily_rss_block}
{daily_amazon_block}
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


def prompts_body_legacy():
    """Ancien rendu de prompts, conservé temporairement pour référence."""
    prompts = sorted(
        CFG.get("prompt_library", []),
        key=lambda x: (x.get("theme", "Autre"), x.get("title", "")),
    )
    themes = sorted({p.get("theme", "Autre") for p in prompts})
    options = '<option value="all">Tous les thèmes</option>' + "".join(
        f'<option value="{esc(t)}">{esc(t)}</option>' for t in themes
    )

    cards = "".join(
        f'<article class="card prompt-card" '
        f'data-id="prompt-{i}" '
        f'data-theme="{esc(p.get("theme", "Autre"))}" '
        f'data-search="{esc((p.get("title", "") + " " + p.get("theme", "") + " " + p.get("goal", "") + " " + p.get("inputs", "") + " " + p.get("prompt", "")).lower())}">'
        f'<div class="prompt-card-head">'
        f'<span class="tag">{esc(p.get("theme", "Autre"))}</span>'
        f'<button type="button" class="fav-btn" data-fav-id="prompt-{i}" aria-pressed="false" aria-label="Ajouter aux favoris">★</button>'
        f'</div>'
        f'<h3>{esc(p.get("title", "Prompt IA"))}</h3>'
        f'<p><strong>Résultat recherché :</strong> {esc(p.get("goal", ""))}</p>'
        f'<p><strong>Quand l’utiliser :</strong> {esc(p.get("when_to_use", ""))}</p>'
        f'<p><strong>Entrées à fournir :</strong> {esc(p.get("inputs", ""))}</p>'
        f'<p><strong>Checklist qualité :</strong> {esc(p.get("quality_checklist", ""))}</p>'
        f'<details><summary>Prompt prêt à l’emploi</summary>'
        f'<pre id="prompt-{i}"><code>{esc(p.get("prompt", ""))}</code></pre>'
        f'<div class="prompt-actions">'
        f'<button type="button" class="copy-btn" data-copy-prompt="prompt-{i}">Copier le prompt</button>'
        f'</div>'
        f'</details>'
        f'</article>'
        for i, p in enumerate(prompts, start=1)
    )

    return f"""
<section class="full">
  <article class="prose prose-wide">
    <div class="page-head">
      <h1>Prompts utiles par thème</h1>
      <a class="btn-back" href="index.html">\u2190 Retour à la page principale</a>
    </div>
    <p class="lead">Une bibliothèque de prompts IA pratiques, classés par usages concrets.</p>
    <p class="help-inline help-inline--accent">Version V2 : recherche plein texte, favoris, export JSON/CSV et navigation rapide.</p>

    <div class="prompt-toolbar">
      <div class="tool-actions">
        <label for="prompt-theme-filter">Thème</label>
        <select id="prompt-theme-filter" aria-label="Filtrer les prompts par thème">{options}</select>

        <label for="prompt-search">Recherche</label>
        <input id="prompt-search" type="search" placeholder="Ex: marketing, bug, synthèse, B2B..." aria-label="Rechercher dans les prompts">

        <label class="check-inline"><input id="prompt-favorites-only" type="checkbox"> Favoris uniquement</label>
      </div>
      <div class="prompt-toolbar-actions">
        <button type="button" id="prompt-random" class="copy-btn">Prompt aléatoire</button>
        <button type="button" id="prompt-reset" class="copy-btn">Réinitialiser</button>
        <a class="copy-btn export-link" href="prompt-library.json" download>Télécharger JSON</a>
        <a class="copy-btn export-link" href="prompt-library.csv" download>Télécharger CSV</a>
      </div>
      <p id="prompt-results-count" class="prompt-results">0 prompt</p>
    </div>

    <div id="prompt-library-grid" class="grid prompt-grid">{cards}</div>
  </article>
</section>"""


def prompts_body():
    """Génère le hub indexable de prompts avec cartes, collections et méthodologie."""
    prompts = sorted(CFG.get("prompt_library", []), key=lambda x: (x.get("theme", "Autre"), x.get("title", "")))
    themes = sorted({p.get("theme", "Autre") for p in prompts})
    options = '<option value="all">Tous les thèmes</option>' + "".join(
        f'<option value="{esc(t)}">{esc(t)}</option>' for t in themes
    )

    cards = []
    for i, prompt in enumerate(prompts, start=1):
        slug = prompt_slug(prompt)
        tags = prompt_tags(prompt)
        difficulty = str(prompt.get("difficulty", "Intermédiaire"))
        time_saved = str(prompt.get("time_saved", "25 min"))
        quality = str(prompt.get("quality_score", "4,7"))
        search_blob = " ".join([
            prompt.get("title", ""), prompt.get("theme", ""), prompt.get("goal", ""),
            prompt.get("inputs", ""), prompt.get("prompt", ""), " ".join(tags),
        ]).lower()
        tag_html = "".join(f'<span class="prompt-tag">{esc(tag)}</span>' for tag in tags[:9])
        cards.append(
            f'<article class="card prompt-card" data-id="prompt-{i}" data-prompt-stats="{esc(slug)}" '
            f'data-theme="{esc(prompt.get("theme", "Autre"))}" data-collections="{esc(" ".join(prompt_collections(prompt)))}" '
            f'data-search="{esc(search_blob)}">'
            f'<div class="prompt-card-head"><div class="prompt-meta-row"><span class="tag">{esc(prompt.get("theme", "Autre"))}</span>'
            f'<span class="level-badge">{esc(difficulty)}</span></div>'
            f'<button type="button" class="fav-btn" data-fav-id="prompt-{i}" aria-pressed="false" aria-label="Ajouter aux favoris">★</button></div>'
            f'<h3><a href="prompts/{esc(slug)}.html">{esc(prompt.get("title", "Prompt IA"))}</a></h3>'
            f'<p><strong>Objectif :</strong> {esc(prompt.get("goal", ""))}</p><div class="prompt-tags">{tag_html}</div>'
            f'<div class="prompt-proof"><span>Gain estimé : {esc(time_saved)}</span><span>Score éditorial : {esc(quality)}/5</span>'
            f'<span data-prompt-uses="{esc(slug)}">0 copie locale</span></div>'
            f'<p><strong>Quand l’utiliser :</strong> {esc(prompt.get("when_to_use", ""))}</p>'
            f'<p><strong>Entrées :</strong> {esc(prompt.get("inputs", ""))}</p>'
            f'<div class="prompt-code-block"><div class="prompt-code-head"><strong>Prompt prêt à copier</strong><span>Texte brut</span></div>'
            f'<pre id="prompt-{i}"><code>{esc(prompt.get("prompt", ""))}</code></pre></div>'
            f'<div class="prompt-actions"><button type="button" class="copy-btn" data-copy-prompt="prompt-{i}" data-copy-key="{esc(slug)}">Copier</button>'
            f'<button type="button" class="copy-btn" data-edit-prompt="prompt-{i}">Modifier</button>'
            f'<button type="button" class="copy-btn" data-test-prompt="prompt-{i}" data-provider="chatgpt">Tester ChatGPT</button>'
            f'<button type="button" class="copy-btn" data-test-prompt="prompt-{i}" data-provider="claude">Tester Claude</button>'
            f'<button type="button" class="copy-btn" data-test-prompt="prompt-{i}" data-provider="copilot">Tester Copilot</button>'
            f'<a class="copy-btn detail-link" href="prompts/{esc(slug)}.html">Fiche complète</a></div></article>'
        )

    collection_buttons = "".join(
        f'<button type="button" class="collection-btn" data-prompt-collection="{key}">{label}</button>'
        for key, label in (
            ("all", "Tous les prompts"), ("pme", "Top prompts PME"), ("developers", "Top développeurs"),
            ("creators", "Top créateurs"), ("seo", "Top SEO"),
        )
    )

    return f"""
<section class="full prompt-hub">
  <article class="prose prose-wide">
    <div class="page-head">
      <div><span class="eyebrow">Bibliothèque expert OCTET LAB</span><h1>Prompts IA professionnels, testables et adaptables</h1></div>
      <a class="btn-back" href="index.html">← Retour à la page principale</a>
    </div>
    <p class="lead">Des prompts complets et immédiatement copables pour produire, analyser, coder, vendre et automatiser avec plusieurs assistants IA.</p>

    <div class="prompt-conversion">
      <div><span class="tag">Nouveau chaque semaine</span><h2>Recevez les prochains prompts professionnels</h2><p>Inscrivez-vous par e-mail : aucune donnée n’est publiée ni revendue. L’envoi reste manuel pour préserver un rythme éditorial exigeant.</p></div>
      <a class="primary-cta" href="mailto:contact@binaryforge.fr?subject=Inscription%20prompts%20OCTET%20LAB&amp;body=Bonjour%2C%20je%20souhaite%20recevoir%20le%20nouveau%20prompt%20hebdomadaire.">Recevoir le prompt de la semaine</a>
    </div>

    <nav class="prompt-collections" aria-label="Collections de prompts">{collection_buttons}</nav>
    <div class="prompt-toolbar">
      <div class="tool-actions">
        <label for="prompt-theme-filter">Thème</label><select id="prompt-theme-filter" aria-label="Filtrer les prompts par thème">{options}</select>
        <label for="prompt-search">Recherche</label><input id="prompt-search" type="search" placeholder="SEO, bug, B2B, SaaS, Copilot..." aria-label="Rechercher dans les prompts">
        <label class="check-inline"><input id="prompt-favorites-only" type="checkbox"> Favoris uniquement</label>
      </div>
      <div class="prompt-toolbar-actions">
        <button type="button" id="prompt-random" class="copy-btn">Prompt aléatoire</button><button type="button" id="prompt-reset" class="copy-btn">Réinitialiser</button>
        <a class="copy-btn export-link" href="prompt-library.json" download>Télécharger JSON</a><a class="copy-btn export-link" href="prompt-library.csv" download>Télécharger CSV</a>
      </div><p id="prompt-results-count" class="prompt-results">0 prompt</p>
    </div>

    <div id="prompt-library-grid" class="grid prompt-grid">{''.join(cards)}</div>

    <section class="prompt-guide-index">
      <h2>Guide complet des prompts IA professionnels</h2>
      <p>Un bon prompt n’est pas une formule magique : c’est une spécification de travail. Plus l’objectif est précis, plus le modèle peut produire une réponse exploitable. OCTET LAB structure chaque prompt autour d’un rôle, d’un contexte, de données, d’une forme de sortie et de critères de contrôle. Cette méthode réduit les corrections et permet de comparer plusieurs assistants sur une base identique.</p>
      <h3>1. Commencer par une finalité mesurable</h3><p>Décrivez le livrable attendu : plan de publication, diagnostic reproductible, synthèse décisionnelle ou tableau de risques. « Analyse ceci » reste trop ouvert. Une bonne consigne précise le résultat, son format, son niveau de détail et la décision qu’il doit faciliter.</p>
      <h3>2. Fournir un contexte utile, sans bruit</h3><p>Ajoutez uniquement l’audience, les contraintes, le budget, la deadline, les outils et le ton. Anonymisez les données sensibles. Séparez clairement les instructions des données à analyser afin de limiter les ambiguïtés.</p>
      <h3>3. Choisir un format de sortie testable</h3><p>Demandez une checklist, un tableau, une structure JSON, des étapes numérotées ou des sections imposées. Ce format facilite la vérification et l’automatisation. Faites également distinguer les faits, les hypothèses et les éléments manquants.</p>
      <h3>4. Utiliser des critères de qualité explicites</h3><p>Nos prompts précisent la cohérence, l’actionnabilité, la vérifiabilité, la sécurité et l’adaptation au lecteur. Un résultat long n’est pas forcément meilleur : le bon résultat permet d’exécuter une tâche ou de prendre une décision avec moins d’aller-retours.</p>
      <h3>5. Itérer par essais contrôlés</h3><p>Testez avec un exemple simple, comparez la sortie attendue puis modifiez une seule variable. Conservez une version de référence. Pour un usage récurrent, transformez le prompt en gabarit avec des variables entre accolades.</p>
      <h3>6. Adapter le prompt au modèle</h3><p>GPT, Claude, Gemini, Copilot et les modèles locaux réagissent différemment. Testez la consigne courte, les exemples et les exigences de sortie sur un même cas d’essai, sans changer plusieurs paramètres à la fois.</p>
      <h3>7. Réduire les hallucinations</h3><p>Demandez au modèle d’indiquer ce qu’il ne sait pas, de citer les données fournies et de séparer recommandations et certitudes. Pour les sujets sensibles, vérifiez les sources externes et faites réaliser une revue métier.</p>
      <h3>8. Construire une bibliothèque interne</h3><p>Classez les prompts par équipe, objectif, niveau et modèle testé. Ajoutez un propriétaire, une date de révision et des exemples. Cette gouvernance transforme une collection personnelle en actif opérationnel partagé.</p>
    </section>

    <section class="prompt-methodology" id="methodologie">
      <div><span class="eyebrow">Méthodologie OCTET LAB</span><h2>Comment les prompts sont sélectionnés</h2></div>
      <div class="method-grid">
        <article><h3>Utilité</h3><p>Chaque prompt résout une tâche fréquente et produit un livrable concret.</p></article>
        <article><h3>Réutilisabilité</h3><p>Les variables sont visibles, adaptables et utilisables par plusieurs profils.</p></article>
        <article><h3>Contrôle</h3><p>Le format, les critères de qualité et les limites attendues sont précisés.</p></article>
        <article><h3>Transparence</h3><p>Les scores sont éditoriaux indicatifs ; les usages affichés sont des compteurs locaux du navigateur.</p></article>
      </div>
      <p class="help-inline">Compatibilité indicative : GPT, Claude, Copilot, Gemini et modèles locaux. Vérifiez toujours le résultat avant usage professionnel.</p>
    </section>
  </article>
</section>"""


def prompt_detail_body(prompt, related):
    """Génère une page SEO indexable complète pour un prompt."""
    title = str(prompt.get("title", "Prompt IA"))
    slug = prompt_slug(prompt)
    difficulty = str(prompt.get("difficulty", "Intermédiaire"))
    time_saved = str(prompt.get("time_saved", "25 min"))
    quality = str(prompt.get("quality_score", "4,7"))
    tags = prompt_tags(prompt)
    tag_html = "".join(f'<span class="prompt-tag">{esc(tag)}</span>' for tag in tags)
    example = str(prompt.get("example", "Remplacez les variables entre accolades par votre contexte, relancez une première fois, puis demandez une version plus concise ou orientée vers votre public."))
    variants = prompt.get("variants", [])
    if not isinstance(variants, list) or not variants:
        variants = [
            "Version concise : imposez 5 à 8 lignes et une seule recommandation prioritaire.",
            "Version expert : exigez hypothèses, risques, sources à vérifier et critères d’acceptation.",
            "Version équipe : structurez la réponse pour une validation manager puis une exécution opérationnelle.",
        ]
    variants_html = "".join(f'<li>{esc(variant)}</li>' for variant in variants)
    faq = [
        (f"Comment utiliser le prompt « {title} » ?", f"Copiez le prompt, remplacez les variables entre accolades et contrôlez la réponse avec : {prompt.get('quality_checklist', 'objectif, structure et précision')}."),
        ("Avec quels assistants IA l’utiliser ?", "Il peut servir de base avec GPT, Claude, Copilot, Gemini ou un modèle local. Utilisez un exemple identique pour comparer les sorties."),
        ("Puis-je modifier ce prompt ?", "Oui. Le bouton Modifier rend le texte éditable dans le navigateur. Rien n’est transmis avant l’ouverture explicite d’un assistant."),
    ]
    faq_html = "".join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faq)
    faq_schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq
    ]}
    creative_schema = {
        "@context": "https://schema.org", "@type": "CreativeWork", "name": title,
        "description": prompt.get("goal", ""), "url": build_absolute_url(f"prompts/{slug}.html"),
        "inLanguage": "fr-FR", "author": {"@type": "Organization", "name": CFG.get("owner_name", "BinaryForge")},
    }
    related_html = "".join(
        f'<a class="card" href="{esc(prompt_slug(item))}.html"><span class="tag">{esc(item.get("theme", ""))}</span>'
        f'<h3>{esc(item.get("title", "Prompt"))}</h3><p>{esc(item.get("goal", ""))}</p></a>'
        for item in related
    ) or '<p>Aucun prompt lié configuré pour le moment.</p>'

    return f"""
<section class="full prompt-detail-page"><article class="prose prompt-detail" data-prompt-stats="{esc(slug)}">
  <nav class="breadcrumb" aria-label="Fil d’Ariane"><a href="../prompts-utiles.html">Prompts utiles</a> / <span>{esc(title)}</span></nav>
  <span class="eyebrow">{esc(prompt.get("theme", "IA professionnelle"))}</span><h1>{esc(title)}</h1><p class="lead">{esc(prompt.get("goal", ""))}</p>
  <div class="prompt-tags">{tag_html}</div>
  <div class="prompt-proof prompt-proof-large"><span><strong>{esc(difficulty)}</strong>Niveau</span><span><strong>{esc(time_saved)}</strong>Gain estimé</span><span><strong>{esc(quality)}/5</strong>Score éditorial</span><span><strong data-prompt-views="{esc(slug)}">0</strong>Vues locales</span><span><strong data-prompt-uses="{esc(slug)}">0</strong>Copies locales</span></div>
  <h2>Prompt prêt à l’emploi</h2><div class="prompt-code-block prompt-code-block-large"><div class="prompt-code-head"><strong>Texte brut modifiable</strong><span>Variables entre accolades</span></div><pre id="prompt-detail-{esc(slug)}"><code>{esc(prompt.get("prompt", ""))}</code></pre></div>
  <div class="prompt-actions"><button type="button" class="copy-btn" data-copy-prompt="prompt-detail-{esc(slug)}" data-copy-key="{esc(slug)}">Copier le prompt</button><button type="button" class="copy-btn" data-edit-prompt="prompt-detail-{esc(slug)}">Modifier</button><button type="button" class="copy-btn" data-test-prompt="prompt-detail-{esc(slug)}" data-provider="chatgpt">Tester dans ChatGPT</button><button type="button" class="copy-btn" data-test-prompt="prompt-detail-{esc(slug)}" data-provider="claude">Tester dans Claude</button><button type="button" class="copy-btn" data-test-prompt="prompt-detail-{esc(slug)}" data-provider="copilot">Tester dans Copilot</button></div>
  <h2>Quand et comment l’utiliser</h2><p><strong>Moment adapté :</strong> {esc(prompt.get("when_to_use", ""))}</p><p><strong>Données à fournir :</strong> {esc(prompt.get("inputs", ""))}</p><h3>Exemple d’utilisation</h3><p>{esc(example)}</p><h3>Critères de qualité</h3><p>{esc(prompt.get("quality_checklist", ""))}</p>
  <h2>Variantes recommandées</h2><ul>{variants_html}</ul><section class="guide-faq"><h2>FAQ du prompt</h2>{faq_html}</section>
  <section class="prompt-detail-related"><h2>Prompts liés</h2><div class="grid">{related_html}</div></section>
  <script type="application/ld+json">{json.dumps(creative_schema, ensure_ascii=False).replace("</", "<\\/")}</script>
  <script type="application/ld+json">{json.dumps(faq_schema, ensure_ascii=False).replace("</", "<\\/")}</script>
</article></section>"""


def csv_escape(value):
    s = str(value or "")
    if any(c in s for c in [",", '"', "\n", "\r"]):
        return '"' + s.replace('"', '""') + '"'
    return s


def write_prompt_exports():
    prompts = CFG.get("prompt_library", [])
    (OUT / "prompt-library.json").write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2),
        "utf-8",
    )

    headers = [
        "theme", "title", "goal", "when_to_use", "inputs", "quality_checklist",
        "difficulty", "time_saved", "quality_score", "tags", "prompt"
    ]
    lines = [",".join(headers)]
    for p in prompts:
        values = []
        for h in headers:
            value = p.get(h, "")
            if isinstance(value, list):
                value = " | ".join(str(item) for item in value)
            values.append(csv_escape(value))
        lines.append(",".join(values))
    (OUT / "prompt-library.csv").write_text("\n".join(lines) + "\n", "utf-8")


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
    (OUT / "prompts").mkdir(parents=True)
    shutil.copytree(ROOT / "assets", OUT / "assets")

    # Guides
    guide_docs = []
    guides = []
    for p in sorted((ROOT / "guides").glob("*.md")):
        meta, body = load(p)
        guides.append(meta)
        guide_docs.append({"meta": meta, "body": body})

    related_map = build_related_guides(guides)
    configured_faq = CFG.get("guide_faq", {})
    configured_faq = configured_faq if isinstance(configured_faq, dict) else {}

    for doc in guide_docs:
        meta = doc["meta"]
        body = doc["body"]

        related = related_map.get(meta["slug"], [])
        related_html = ""
        if related:
            related_items = "".join(
                f'<li><a href="{esc(r["slug"])}.html">{esc(r.get("title", "Guide"))}</a>'
                f'<small>{esc(r.get("category", ""))}</small></li>'
                for r in related
            )
            related_html = (
                '<section class="guide-related">'
                '<h2>Guides liés</h2>'
                '<p>Pour aller plus loin sans quitter le site :</p>'
                f'<ul>{related_items}</ul>'
                '</section>'
            )

        raw_faq = configured_faq.get(meta["slug"])
        faq_candidates = raw_faq if isinstance(raw_faq, list) and raw_faq else default_guide_faq(meta)
        faq_items = []
        for qa in faq_candidates:
            if not isinstance(qa, dict):
                continue
            question = str(qa.get("question", "")).strip()
            answer = str(qa.get("answer", "")).strip()
            if question and answer:
                faq_items.append({"question": question, "answer": answer})

        if not faq_items:
            faq_items = default_guide_faq(meta)

        faq_rows = "".join(
            f'<details><summary>{esc(item["question"])}</summary><p>{esc(item["answer"])}</p></details>'
            for item in faq_items
        )
        faq_section = (
            '<section class="guide-faq">'
            '<h2>FAQ</h2>'
            '<p>Questions fréquentes pour appliquer ce guide correctement.</p>'
            f'{faq_rows}'
            '</section>'
        )

        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item["answer"],
                    },
                }
                for item in faq_items
            ],
        }
        faq_schema_html = (
            '<script type="application/ld+json">'
            + json.dumps(faq_schema, ensure_ascii=False).replace("</", "<\\/")
            + '</script>'
        )

        page = (
            f'<article class="prose">'
            f'<h1>{esc(meta["title"])}</h1>'
            f'{body}'
            f'{related_html}'
            f'{faq_section}'
            f'{faq_schema_html}'
            f'<p><a href="../index.html">← Retour aux guides</a></p>'
            f'</article>'
        )

        (OUT / "guides" / f"{meta['slug']}.html").write_text(
            layout(
                meta["title"] + " | " + CFG["site_name"],
                meta.get("description", ""),
                page,
                depth=1,
                page_path=f"guides/{meta['slug']}.html",
            ),
            "utf-8",
        )

    # Pages légales
    for p in (ROOT / "pages").glob("*.md"):
        meta, body = load(p)
        (OUT / f"{meta['slug']}.html").write_text(
            layout(
                meta["title"],
                meta["title"],
                f'<article class="prose"><h1>{esc(meta["title"])}</h1>{body}</article>',
                page_path=f"{meta['slug']}.html",
            ),
            "utf-8",
        )

    # Pages principales
    news = fetch_news()
    (OUT / "index.html").write_text(
        layout(
            CFG["site_name"] + " : " + CFG["tagline"],
            CFG["tagline"],
            index_body(guides, news),
            page_path="index.html",
        ),
        "utf-8",
    )
    (OUT / "ia-thematiques.html").write_text(
        layout(
            "IA par thématiques | " + CFG["site_name"],
            "Catalogue d\u2019IA triable par thématique, finalité et prix.",
            ai_tools_body(),
            page_path="ia-thematiques.html",
        ),
        "utf-8",
    )
    prompts = CFG.get("prompt_library", [])
    (OUT / "prompts-utiles.html").write_text(
        layout(
            "Prompts IA professionnels : bibliothèque complète | " + CFG["site_name"],
            "Prompts IA complets à copier, modifier et tester : SEO, développement, marketing, productivité et sécurité.",
            prompts_body(),
            page_path="prompts-utiles.html",
        ),
        "utf-8",
    )
    for prompt in prompts:
        slug = prompt_slug(prompt)
        same_theme = [item for item in prompts if item is not prompt and item.get("theme") == prompt.get("theme")]
        fallback = [item for item in prompts if item is not prompt]
        related = (same_theme + fallback)[:3]
        (OUT / "prompts" / f"{slug}.html").write_text(
            layout(
                f"{prompt.get('title', 'Prompt IA')} : prompt complet | {CFG['site_name']}",
                str(prompt.get("goal", "Prompt IA professionnel prêt à copier et à adapter.")),
                prompt_detail_body(prompt, related),
                depth=1,
                page_path=f"prompts/{slug}.html",
            ),
            "utf-8",
        )
    write_prompt_exports()

    # Sitemap
    today = datetime.now(timezone.utc).date().isoformat()
    sitemap_items = [
        {"path": "index.html", "changefreq": "daily", "priority": "1.0"},
        {"path": "ia-thematiques.html", "changefreq": "weekly", "priority": "0.8"},
        {"path": "prompts-utiles.html", "changefreq": "weekly", "priority": "0.8"},
    ]
    sitemap_items.extend(
        {"path": f"guides/{g['slug']}.html", "changefreq": "monthly", "priority": "0.72"}
        for g in guides
    )
    sitemap_items.extend(
        {"path": f"prompts/{prompt_slug(prompt)}.html", "changefreq": "monthly", "priority": "0.76"}
        for prompt in prompts
    )
    sitemap_items.extend(
        {"path": f"{p.stem}.html", "changefreq": "yearly", "priority": "0.35"}
        for p in (ROOT / "pages").glob("*.md")
    )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(
            f"<url><loc>{build_absolute_url(item['path'])}</loc>"
            f"<lastmod>{today}</lastmod><changefreq>{item['changefreq']}</changefreq>"
            f"<priority>{item['priority']}</priority></url>"
            for item in sitemap_items
        )
        + "</urlset>"
    )
    (OUT / "sitemap.xml").write_text(sitemap, "utf-8")

    # robots.txt
    host = CFG["base_url"].replace("https://", "").replace("http://", "").strip("/")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {CFG['base_url']}/sitemap.xml\nHost: {host}\n",
        "utf-8",
    )

    # Fichiers de sécurité
    write_security_files()

    # Fichiers statiques racine à conserver dans public/
    for fname in ("CNAME", "ads.txt", "googled0b4ae6e822c48bf.html"):
        src = ROOT / fname
        if src.exists():
            shutil.copy2(src, OUT / fname)

    print(f"OK : {len(guides)} guides, {len(news)} actualités")


if __name__ == "__main__":
    main()
