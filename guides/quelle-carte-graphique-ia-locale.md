---
title: Quelle carte graphique pour une IA locale ?
description: Guide expert pour dimensionner la VRAM, éviter les goulets d'étranglement et choisir une carte adaptée à vos usages IA.
category: IA locale
---
Pour l’IA locale, la question clé n’est pas “quelle carte est la plus puissante ?”, mais “quelle carte tient mes modèles avec un débit acceptable ?”. Dans la majorité des cas, la **VRAM** prime sur le reste.

## Objectif du guide

Vous aider à :

- estimer la VRAM nécessaire avant achat ;
- comprendre les compromis quantification/qualité ;
- éviter les erreurs de configuration coûteuses.

## Méthode experte de dimensionnement

## 1) Partir des usages, pas du marketing

Posez-vous ces questions :

- chat rapide en local ?
- rédaction/assistants quotidiens ?
- code + contexte long ?
- RAG/documentation volumineuse ?

Plus le contexte et la complexité montent, plus la VRAM grimpe.

## 2) Estimer la VRAM minimale

Variables principales :

- taille du modèle (7B, 14B, 32B…) ;
- quantification (Q4, Q5, Q8, FP16) ;
- longueur de contexte.

Repères simples :

- **Q4** : environ 0,6 Go par milliard de paramètres ;
- **Q8** : environ 1,1 Go par milliard ;
- ajoutez 1 à 4 Go selon le contexte visé.

Exemples pratiques :

- 8B en Q4 : ~6 Go => carte 8 Go ;
- 14B en Q4 : ~10 Go => carte 12 Go ;
- 32B en Q4 : ~21 Go => carte 24 Go.

## 3) Prévoir une marge de sécurité

Ne visez pas “juste suffisant”. Gardez 15 à 25 % de marge pour :

- pics de mémoire ;
- contexte plus long ;
- multitâche local ;
- évolution des modèles.

## 4) Optimiser le ratio budget/valeur

Règle très fiable pour débuter :

- à budget égal, privilégier **plus de VRAM** plutôt qu’un gain théorique de puissance brute.

Un modèle qui tient en VRAM est souvent plus utile qu’un GPU rapide mais limité en mémoire.

## Checklist avant achat

- [ ] Modèles cibles identifiés (taille + quantification)
- [ ] Contexte moyen et contexte max définis
- [ ] Estimation VRAM calculée + marge
- [ ] Alimentation et boîtier compatibles
- [ ] Plan d’évolution à 12 mois

## Erreurs fréquentes

- **Acheter trop juste** : impossible de tester des modèles plus grands ensuite.
- **Comparer uniquement les FPS gaming** : peu pertinent pour usage LLM local.
- **Ignorer le contexte** : 4k et 32k ne demandent pas la même mémoire.
- **Négliger le bruit/chauffe** : important en usage long.

## FAQ rapide

### 8 Go suffisent-ils ?
Oui pour démarrer sur 7B/8B en Q4 et des contextes modérés.

### 12 Go, c’est le bon milieu ?
Souvent oui pour un usage polyvalent local, avec plus de marge.

### 24 Go, c’est utile ?
Très utile si vous ciblez 32B, du contexte long ou des workflows plus lourds.

### La RAM système peut-elle compenser ?
Partiellement, mais avec forte pénalité de performances. La VRAM reste prioritaire.

## Conclusion

Le choix d’une carte pour IA locale doit être piloté par vos modèles cibles et votre contexte d’usage. Une estimation réaliste + marge de sécurité évite les achats regrettés et vous donne une base durable.
