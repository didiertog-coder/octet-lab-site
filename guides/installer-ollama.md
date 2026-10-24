---
title: Installer Ollama et lancer son premier modèle
description: De l'installation au premier échange avec une IA locale, en quelques minutes.
category: IA locale
---
Ollama est un outil gratuit qui télécharge et exécute des modèles d'IA sur votre propre machine, sans envoyer vos données à un service en ligne.

## Installation

- Téléchargez l'installateur sur [ollama.com](https://ollama.com) (Windows, macOS, Linux).
- Lancez l'installation, puis ouvrez un terminal.

## Premier modèle

```
ollama run llama3.2
```

Le modèle se télécharge au premier lancement, puis vous pouvez discuter directement dans le terminal. Tapez `/bye` pour quitter.

## Aller plus loin

- `ollama list` affiche les modèles installés.
- `ollama pull nom-du-modèle` télécharge un modèle sans le lancer.
- Si le modèle est lent, choisissez une version plus petite : voir le guide sur la carte graphique.
