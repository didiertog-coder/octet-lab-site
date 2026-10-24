---
title: Quelle carte graphique pour une IA locale ?
description: La règle simple pour estimer la VRAM nécessaire selon la taille du modèle.
category: IA locale
---
Pour faire tourner un modèle de langage chez soi, la mémoire vidéo (VRAM) compte plus que la puissance brute : si le modèle ne tient pas dans la VRAM, il ralentit fortement.

## La règle d'estimation

La VRAM nécessaire dépend de trois choses : la taille du modèle, sa quantification et la longueur du contexte.

- **Taille** : le nombre de milliards de paramètres (8B, 14B, 32B...).
- **Quantification** : en Q4, comptez environ 0,6 Go par milliard de paramètres. En Q8, environ 1,1 Go.
- **Contexte** : ajoutez 1 à 4 Go selon la longueur de conversation voulue.

## Repères pratiques en Q4

- Modèle 7-8B : environ 6 Go, soit une carte de 8 Go.
- Modèle 14B : environ 10 Go, soit une carte de 12 Go.
- Modèle 32B : environ 21 Go, soit une carte de 24 Go.

Ce sont des ordres de grandeur : utilisez l'estimateur en haut de la page d'accueil pour affiner.

## À retenir

- À budget égal, privilégiez la carte avec le plus de VRAM.
- La quantification Q4 est le meilleur compromis qualité/mémoire pour débuter.
