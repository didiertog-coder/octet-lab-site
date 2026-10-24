---
title: Mettre un site en ligne gratuitement avec GitHub Pages
description: De vos fichiers à un site public, sans serveur à gérer.
category: Mise en ligne
---
GitHub Pages héberge gratuitement les sites statiques (HTML, CSS, JavaScript). C'est une base solide pour un blog, un portfolio ou un site de guides.

## Ce qu'il vous faut

- Un compte GitHub gratuit.
- Un dossier contenant votre site, avec un fichier `index.html` à la racine.

## Étapes

- Créez un nouveau dépôt sur GitHub.
- Envoyez-y vos fichiers, depuis l'interface web (Add file > Upload files) ou avec Git.
- Ouvrez Settings > Pages, et choisissez la source de publication (branche, ou GitHub Actions si le site est généré par un script).
- Patientez quelques minutes : l'adresse du site s'affiche dans cette même page.

## Brancher votre propre domaine

Dans Settings > Pages, renseignez votre domaine dans « Custom domain », puis créez chez votre registrar les enregistrements DNS indiqués par la documentation GitHub. L'option « Enforce HTTPS » active le certificat gratuit.

## Limites à connaître

- Site statique uniquement : pas de base de données ni de code serveur.
- Pas d'usage commercial lourd : consultez les conditions d'utilisation de GitHub Pages.
- Pour du contenu qui change chaque jour, utilisez une tâche planifiée (GitHub Actions) qui régénère le site.
