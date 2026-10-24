# OCTET LAB — Site statique avec actualités automatiques

## Comment ça fonctionne

`build.py` lit `config.json`, les guides (`guides/*.md`) et les flux RSS, puis génère le site complet dans `public/`.  
Le workflow GitHub Actions (`.github/workflows/daily.yml`) relance le build chaque jour à 6 h UTC : les actualités se mettent à jour seules, sans intervention manuelle.

---

## Mise en ligne sur GitHub Pages (étapes complètes)

### Étape 1 — Préparer config.json

Ouvrez `config.json` et renseignez au minimum :

```json
"base_url": "https://VOTRE_PSEUDO.github.io/NOM_DEPOT",
"owner_name": "Votre Nom",
"contact_email": "votre@email.com"
```

Si vous avez un domaine custom (ex: octetlab.fr), mettez l'URL finale ici et lisez `CNAME.example`.

### Étape 2 — Créer le dépôt GitHub

1. Allez sur [github.com/new](https://github.com/new)
2. Nom du dépôt : `octet-lab-site` (ou ce que vous voulez)
3. Visibilité : **Public** (obligatoire pour GitHub Pages gratuit)
4. **Ne cochez rien** (pas de README, pas de .gitignore) — laissez le dépôt vide

### Étape 3 — Envoyer le code source

Dans un terminal PowerShell, depuis `E:\Octet_Lab_Site` :

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/VOTRE_PSEUDO/octet-lab-site.git
git push -u origin main
```

> Au premier push, Windows peut ouvrir une fenêtre d'authentification GitHub — connectez-vous.

### Étape 4 — Activer GitHub Pages

1. Sur GitHub, ouvrez votre dépôt → **Settings** → **Pages**
2. Section **Source** : choisissez **GitHub Actions**
   *(pas "Deploy from a branch" — on utilise le workflow)*
3. Sauvegardez

### Étape 5 — Lancer le premier déploiement

Le déploiement se lance automatiquement au push de l'étape 3.
Vous pouvez aussi le déclencher manuellement :
**Actions** → `Mise à jour quotidienne et déploiement GitHub Pages` → **Run workflow**

### Étape 6 — Vérifier

Après 1 à 3 minutes, votre site est accessible sur :

```
https://VOTRE_PSEUDO.github.io/octet-lab-site/
```

---

## Structure du projet

| Chemin | Rôle |
|---|---|
| `build.py` | Générateur du site (Python 3.9+, aucune dépendance pip) |
| `config.json` | Nom du site, flux RSS, partenaires, analytics |
| `guides/*.md` | Un fichier = un guide publié |
| `pages/*.md` | Pages légales (mentions, RGPD, cookies, CGU) |
| `assets/style.css` | Thème cyberpunk dark |
| `assets/app.js` | Estimateur VRAM, cookies, filtre IA |
| `.github/workflows/daily.yml` | CI/CD : build + deploy quotidien |
| `.gitignore` | Exclut `public/`, `.vs/`, `backup_*/`... |
| `CNAME.example` | Instructions domaine personnalisé |
| `Deploiement.bat` | Script de déploiement alternatif (usage local) |

> `public/` est **généré sur GitHub** par le workflow — ne le commitez pas.

---

## Ajouter un guide

Créez `guides/mon-guide.md` avec l'en-tête :

```markdown
---
title: Mon titre
description: Description courte pour le SEO.
category: Ma catégorie
---
Contenu en Markdown ici...
```

Commitez et poussez : le workflow regénère le site automatiquement.

---

## Monétisation

- Remplacez les URL `partners` dans `config.json` par vos liens d'affiliation réels.
- AdSense : passez `"enabled": true` et renseignez `client_id` + `slot_home_top`.
- Gardez toujours `rel="sponsored"` et la mention lien partenaire (obligation légale).

---

## À faire avant la mise en ligne

- [ ] Mettre à jour `base_url` dans `config.json`
- [ ] Compléter `pages/mentions-legales.md` avec vos vraies coordonnées
- [ ] Remplacer les liens partenaires placeholders par vos vrais liens affiliés
- [ ] (Optionnel) Configurer un domaine custom — voir `CNAME.example`

## Arborescence
- `config.json` : nom du site, flux RSS, liens partenaires
- `guides/` : un fichier `.md` = un guide (en-tête `title`, `description`, `category`)
- `pages/` : pages légales
- `assets/` : `style.css`, `app.js` (estimateur de VRAM)
- `public/` : site généré, prêt à être envoyé tel quel
- `.github/workflows/daily.yml` : mise à jour quotidienne

## Mise en ligne gratuite (GitHub Pages)
1. Créez un dépôt GitHub et envoyez-y tout le contenu de ce dossier (branche `main`).
2. Réglages > Pages > Source : **GitHub Actions**.
3. Le site est publié, puis mis à jour chaque jour. Domaine perso : Réglages > Pages > Custom domain.
Alternative : tout hébergeur statique (Cloudflare Pages, Netlify, OVH) en envoyant `public/`, mais il faut alors relancer `python build.py` chaque jour (tâche planifiée).

## Ajouter un guide
Créez `guides/mon-guide.md` avec l'en-tête, écrivez en Markdown (`##`, listes, `**gras**`, liens, blocs de code), puis relancez `python build.py`.

## Monétisation
- Remplacez les URL de `partners` par vos liens d'affiliation (programmes Awin, Amazon Partenaires, etc.). Gardez `rel="sponsored"` et la mention « lien partenaire ».
- Publicité display (AdSense) : à ajouter seulement avec un bandeau de consentement cookies conforme RGPD.

## À faire avant la mise en ligne
- Compléter `pages/mentions-legales.md` et `base_url` dans `config.json`.
- Les polices viennent de Google Fonts : pour être strictement conforme RGPD, hébergez-les vous-même dans `assets/`.
- Vérifier que chaque flux RSS répond (le build ignore ceux qui échouent et l'indique dans ses logs).
- Un dépôt sans activité pendant 60 jours peut voir ses tâches planifiées suspendues : relancez-les depuis l'onglet Actions.
