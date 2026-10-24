---
title: Construire un NAS maison avec TrueNAS Scale
description: Stockage centralisé, RAID logiciel, partages réseau et sauvegardes : montez votre propre serveur de fichiers.
category: Matériel
---
Un NAS (Network Attached Storage) maison offre bien plus qu'un NAS commercial au même prix : accès root complet, apps Docker, pas d'abonnement, et une durée de vie indépendante des décisions d'un éditeur. TrueNAS Scale, basé sur Debian, est l'option la plus aboutie pour les débutants avancés.

## Pourquoi TrueNAS Scale ?

- Système de fichiers **ZFS** : protection contre la corruption silencieuse, snapshots, déduplication.
- Interface web complète, sans ligne de commande pour les tâches courantes.
- Applications Docker intégrées (Nextcloud, Jellyfin, Immich…).
- Gratuit, open source, mises à jour régulières.

## Choisir le matériel

| Composant | Minimum | Recommandé |
|---|---|---|
| CPU | Intel Celeron N5105 | Ryzen 5 ou Intel Core i3+ |
| RAM | 8 Go ECC (préférable) | 16–32 Go |
| Disques OS | SSD 120 Go (USB ou M.2) | 2× SSD en miroir |
| Disques données | 2× HDD | 4× HDD en RAIDZ2 |
| Réseau | 1 Gbit | 2.5 Gbit |

**Règle ECC** : ZFS détecte les erreurs mémoire avec l'ECC. Ce n'est pas obligatoire, mais fortement conseillé pour un NAS avec données importantes.

## Installer TrueNAS Scale

1. Téléchargez l'ISO sur [truenas.com](https://www.truenas.com/download-truenas-scale/).
2. Flashez sur une clé USB avec Balena Etcher.
3. Bootez, sélectionnez le SSD dédié comme disque système (jamais les disques de données).
4. Accédez à l'interface web via l'IP affichée après installation (`http://192.168.x.x`).

## Créer un pool ZFS

Dans `Storage > Create Pool` :
- **Mirror** : 2 disques, tolérance 1 panne.
- **RAIDZ1** : 3 disques minimum, tolérance 1 panne, meilleure capacité.
- **RAIDZ2** : 4 disques minimum, tolérance 2 pannes simultanées — recommandé pour données critiques.

## Configurer les partages

- **SMB (Windows)** : `Shares > Windows (SMB)`, pointez vers un dataset ZFS. Configurez les permissions ACL par utilisateur.
- **NFS (Linux/Mac)** : `Shares > Unix (NFS)`, restreignez par IP.
- **iSCSI** : pour monter un volume bloc sur un serveur ou une VM.

## Sauvegardes avec ZFS Replication

Programmez des snapshots automatiques (ex. : toutes les heures, rétention 7 jours) et répliquez vers un second NAS ou un VPS via `Data Protection > Replication Tasks`. Le transfert différentiel n'envoie que les blocs modifiés.

## Sécuriser l'accès

- Ne pas exposer l'interface web directement sur Internet : utilisez un VPN (WireGuard intégré dans TrueNAS Scale).
- Activez l'authentification à deux facteurs pour le compte admin.
- Chiffrez les datasets sensibles (`Encryption` lors de la création du dataset).
