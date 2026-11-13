---
title: La règle de sauvegarde 3-2-1
description: Guide expert pour appliquer la stratégie 3-2-1 (et 3-2-1-1) contre pannes, erreurs et ransomware.
category: Informatique
---
Perdre ses données n’est pas une question de “si”, mais de “quand”. La stratégie 3-2-1 reste la base la plus robuste pour les particuliers, freelances et petites structures. Aujourd’hui, face aux ransomwares, il faut aller un cran plus loin avec la logique 3-2-1-1.

## Objectif du guide

Vous saurez :

- implémenter une sauvegarde réellement résiliente ;
- différencier synchronisation et sauvegarde ;
- tester la restauration pour éviter les fausses sécurités.

## Méthode experte en 5 étapes

## 1) Appliquer la règle 3-2-1

Structure minimale :

- **3 copies** de vos données (production + 2 copies) ;
- **2 supports différents** (ex : SSD interne + disque externe/NAS) ;
- **1 copie hors site** (cloud ou support distant).

C’est la protection de base contre panne, vol, incendie et erreur humaine.

## 2) Renforcer avec le principe 3-2-1-1

Le risque moderne : un ransomware peut chiffrer aussi vos sauvegardes accessibles.

Ajoutez donc :

- **1 copie immuable ou déconnectée** (air-gap, snapshots immutables, objet lock).

Sans cette couche, vos “sauvegardes” peuvent disparaître en même temps que la production.

## 3) Automatiser la sauvegarde

Une sauvegarde manuelle finit toujours par être oubliée.

Bonnes pratiques :

- planification quotidienne pour les données actives ;
- rétention adaptée (historique sur plusieurs semaines/mois) ;
- journal de succès/échec.

Automatiser, c’est transformer une intention en système fiable.

## 4) Chiffrer et segmenter les accès

Sécurité recommandée :

- chiffrement des copies hors site ;
- compte de sauvegarde séparé du compte utilisateur principal ;
- MFA activée sur les comptes cloud.

L’objectif est d’éviter qu’un seul compte compromis détruise production + backup.

## 5) Tester la restauration régulièrement

La vraie question n’est pas “ai-je un backup ?”, mais “puis-je restaurer vite et proprement ?”.

Test minimal à faire :

- restaurer un fichier critique chaque mois ;
- restaurer un dossier complet chaque trimestre ;
- mesurer le temps de reprise.

## Checklist opérationnelle

- [ ] Règle 3-2-1 appliquée
- [ ] Copie immuable ou déconnectée en place
- [ ] Sauvegardes automatiques planifiées
- [ ] Chiffrement activé pour l’offsite
- [ ] Test de restauration documenté

## Erreurs fréquentes à éviter

- **Confondre cloud sync et backup** : une suppression se propage partout.
- **Laisser le disque de backup branché en permanence**.
- **Ne jamais tester la restauration**.
- **Tout protéger avec le même compte admin**.
- **Absence de politique de rétention** (on écrase trop vite les versions saines).

## FAQ rapide

### La sauvegarde cloud suffit-elle seule ?
Non. Il faut aussi une copie locale pour restaurer vite et limiter la dépendance réseau.

### Combien de versions garder ?
Dépend de votre activité, mais gardez au moins plusieurs points de restauration sur plusieurs semaines.

### Un NAS remplace-t-il une copie hors site ?
Non, sauf s’il réplique vers un second site/cloud indépendant.

### Quelle fréquence minimale ?
Pour des données actives : quotidien. Pour de l’archive froide : hebdomadaire ou mensuel selon criticité.

## Conclusion

La meilleure sauvegarde est celle qui survit à l’incident et se restaure rapidement. Avec 3-2-1 + une copie immuable/déconnectée + tests réguliers, vous passez d’une protection théorique à une vraie résilience.
