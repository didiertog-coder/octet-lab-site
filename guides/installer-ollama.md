---
title: Installer Ollama et lancer son premier modèle
description: Guide expert pour installer Ollama, choisir le bon modèle et démarrer une IA locale fiable.
category: IA locale
---
Ollama est aujourd’hui l’une des façons les plus simples d’exécuter un LLM en local, sans envoyer vos prompts vers un service cloud. Ce guide vous donne une méthode propre pour éviter les erreurs classiques : machine sous-dimensionnée, modèle mal choisi, lenteur excessive ou confusion entre installation et usage réel.

## Objectif du guide

À la fin, vous saurez :

- installer Ollama proprement ;
- vérifier que votre environnement est prêt ;
- lancer un premier modèle adapté à votre matériel ;
- utiliser les commandes essentielles pour un usage quotidien.

## Méthode experte en 5 étapes

## 1) Vérifier votre machine avant installation

Avant de lancer quoi que ce soit, validez trois points :

- **RAM système** : 16 Go minimum recommandés pour une expérience confortable ;
- **VRAM GPU** (si vous avez une carte graphique) : plus vous en avez, plus vous pouvez utiliser des modèles grands ;
- **espace disque** : prévoyez 10 à 30 Go libres pour démarrer.

Si votre machine est modeste, ciblez un modèle compact (7B/8B en quantification Q4).

## 2) Installer Ollama

- Téléchargez la version officielle : [ollama.com](https://ollama.com).
- Installez puis ouvrez un terminal.
- Vérifiez que la commande répond :

```bash
ollama --version
```

Si la version s’affiche, l’installation est opérationnelle.

## 3) Lancer un premier modèle réaliste

Commencez par un modèle polyvalent et léger :

```bash
ollama run llama3.2
```

Au premier lancement, Ollama télécharge le modèle. Les lancements suivants sont plus rapides.

Conseil pratique : pour un premier test, faites des prompts courts et observez la vitesse de réponse avant de passer à des tâches lourdes.

## 4) Comprendre les commandes clés

Commandes utiles au quotidien :

- `ollama list` : voir les modèles installés ;
- `ollama pull nom-modele` : télécharger un modèle sans le lancer ;
- `ollama rm nom-modele` : supprimer un modèle inutilisé ;
- `ollama ps` : voir les sessions en cours.

Avec ces quatre commandes, vous gérez déjà 90 % d’un usage local classique.

## 5) Stabiliser votre setup pour durer

Après les premiers tests, fixez une base :

- 1 modèle principal pour vos tâches courantes ;
- 1 modèle plus léger pour les machines nomades ;
- une convention de prompts (structure claire, objectif précis).

Vous gagnerez plus en régularité qu’en changeant de modèle tous les jours.

## Checklist de mise en production personnelle

- [ ] Installation validée (`ollama --version`)
- [ ] Premier modèle lancé sans erreur
- [ ] Temps de réponse acceptable sur 5 prompts de test
- [ ] Espace disque maîtrisé (modèles inutiles supprimés)
- [ ] Guide VRAM consulté pour choisir les prochains modèles

## Erreurs fréquentes à éviter

- **Choisir un modèle trop grand dès le départ** : frustration garantie si la machine n’est pas dimensionnée.
- **Comparer les modèles sans protocole** : utilisez toujours les mêmes 5 à 10 prompts de référence.
- **Confondre confidentialité locale et sécurité globale** : local ne veut pas dire invulnérable ; protégez votre poste (mises à jour, chiffrement, sauvegardes).
- **Ignorer la qualité des prompts** : un bon modèle avec un prompt flou donne un mauvais résultat.

## FAQ rapide

### Ollama fonctionne-t-il sans GPU ?
Oui, mais ce sera souvent plus lent. Le CPU est utilisable pour débuter, surtout avec des modèles petits.

### Quelle taille de modèle choisir pour commencer ?
En pratique, 7B/8B en Q4 est un excellent point de départ.

### Puis-je utiliser Ollama dans mes propres outils ?
Oui, Ollama expose une API locale, utile pour scripts, apps ou automatisations.

### Quand passer à un modèle plus grand ?
Quand vos cas d’usage montrent une limite claire (raisonnement, précision métier, contexte long) et que votre matériel suit.

## Conclusion

Installer Ollama est simple ; bien démarrer l’est moins si on saute les étapes. Avec cette méthode, vous partez sur une base propre, mesurable et évolutive. Ensuite, améliorez votre chaîne : prompts plus structurés, tests comparatifs, et choix de modèles aligné avec votre matériel réel.
