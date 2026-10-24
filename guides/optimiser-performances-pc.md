---
title: Optimiser les performances de son PC sans dépenser un euro
description: Nettoyage, configuration Windows, stockage et RAM : des réglages concrets qui changent vraiment la donne.
category: Matériel
---
Avant d'envisager une mise à niveau matérielle, plusieurs réglages logiciels permettent de récupérer des performances significatives sur un PC existant. Ce guide s'applique à Windows 10 et 11.

## 1. Nettoyer les programmes au démarrage

Les applications qui se lancent au démarrage ralentissent le boot et consomment RAM et CPU en permanence.

- `Ctrl + Maj + Échap` → onglet **Démarrage** → désactivez tout ce qui n'est pas indispensable (Spotify, Discord, OneDrive si inutilisé, Teams, launchers de jeux…).
- Règle : si vous ne l'ouvrez pas dans les 10 premières minutes après le démarrage, désactivez-le.

## 2. Vérifier l'utilisation du disque

Un disque dur (HDD) saturé à plus de 80 % de capacité ralentit considérablement. Vérifiez avec `WinDirStat` (gratuit) quels fichiers occupent l'espace.

- Videz la Corbeille et le dossier `Téléchargements`.
- Nettoyage Windows : `Win + R` → `cleanmgr` → cochez tout, incluant **Fichiers Windows Update**.
- Désinstallez les jeux et logiciels inutilisés.

## 3. Passer en SSD si ce n'est pas fait

Un SSD NVMe transforme l'expérience utilisateur plus qu'aucune autre mise à niveau. Le démarrage passe de 60–90 secondes à 10–15 secondes.

- Clonez votre disque avec **Macrium Reflect Free** avant de remplacer.
- Les SSD NVMe d'entrée de gamme (Crucial P3, Kingston NV3) coûtent moins de 60 € pour 1 To.

## 4. Ajuster les paramètres d'alimentation

- `Panneau de configuration > Options d'alimentation` → choisissez **Haute performance** ou **Performances optimales** (débloquable via PowerShell : `powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61`).
- Sur PC portable, restez sur **Équilibré** sur batterie pour préserver son autonomie.

## 5. Libérer la RAM

- Désactivez SysMain (SuperFetch) si votre RAM est < 8 Go et votre disque un SSD : `services.msc` → SysMain → Type de démarrage : Désactivé.
- Fermez les onglets de navigateur inutilisés — chaque onglet Chrome/Edge consomme 100–300 Mo.

## 6. Mettre à jour les pilotes GPU

Les fabricants optimisent régulièrement leurs pilotes pour les nouveaux jeux et logiciels.

- **NVIDIA** : [GeForce Experience](https://www.nvidia.com/geforce/geforce-experience/) ou téléchargement direct sur nvidia.com.
- **AMD** : [AMD Software: Adrenalin](https://www.amd.com/fr/support).
- Évitez les pilotes bêta sauf si vous cherchez un correctif précis.

## 7. Activer le mode jeu et désactiver les effets visuels

- `Win + I > Jeux > Mode Jeu` → Activé.
- `Propriétés système > Avancé > Paramètres (Performances)` → « Ajuster afin d'obtenir les meilleures performances » pour le bureau, ou personnalisez en ne gardant que les effets utiles.

## 8. Vérifier la température

Un PC qui ralentit subitement (throttling) surchauffe peut-être. Installez **HWiNFO64** pour surveiller les températures CPU et GPU.

- CPU en charge : < 90 °C acceptable, < 80 °C idéal.
- GPU en charge : < 85 °C acceptable.
- Remède : nettoyage des filtres à poussière, remplacement de la pâte thermique (CPU) si le PC a plus de 4–5 ans.
