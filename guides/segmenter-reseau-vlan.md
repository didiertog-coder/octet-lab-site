---
title: Réseau local sécurisé : segmenter son réseau avec un VLAN
description: Isolez vos appareils IoT, votre NAS et vos PC avec des VLANs sur un routeur ou switch manageable.
category: Réseau & Sécurité
---
Mélanger caméras connectées, télévisions intelligentes, PC de travail et serveur personnel sur le même réseau local est un risque réel. Un appareil IoT compromis peut observer ou attaquer le reste. Les VLANs créent des cloisonnements logiques sans câblage supplémentaire.

## Ce qu'est un VLAN

Un VLAN (Virtual LAN) attribue un identifiant numérique (1 à 4094) à des ports ou des connexions Wi-Fi. Les appareils du VLAN 10 ne voient pas ceux du VLAN 20, même s'ils partagent le même switch physique. Le routeur décide quels flux transitent d'un VLAN à l'autre.

## Matériel nécessaire

- **Switch manageable** : TP-Link TL-SG108E (~35 €), Netgear GS308E (~45 €) ou équivalent.
- **Routeur avec support VLAN** : pfSense (logiciel libre sur PC), OPNsense, OpenWRT ou routeur Ubiquiti.
- **Point d'accès Wi-Fi multi-SSID** (facultatif) : Unifi, TP-Link EAP, ou OpenWRT.

## Architecture recommandée

| VLAN | Nom | Contenu | Accès Internet |
|---|---|---|---|
| 1 | Admin | Routeur, switch | Non |
| 10 | Maison | PC, téléphones | Oui |
| 20 | IoT | Caméras, ampoules | Oui (restreint) |
| 30 | Serveurs | NAS, VM, IA locale | Non (ou filtré) |

## Configurer sur pfSense / OPNsense

1. **Créer les interfaces VLAN** : `Interfaces > Assignments > VLANs`, ajoutez chaque VLAN avec son tag sur l'interface LAN.
2. **Attribuer et activer** : assignez chaque VLAN à une interface virtuelle, activez-la, définissez une plage IP (ex. `192.168.20.1/24` pour IoT).
3. **Serveur DHCP** : activez un serveur DHCP par VLAN.
4. **Règles de pare-feu** : bloquez le trafic inter-VLAN par défaut. Autorisez uniquement ce qui est nécessaire (ex. : le VLAN Maison peut accéder au NAS sur le port 443 seulement).

## Configurer le switch manageable

Sur le switch, taggez chaque port selon le VLAN auquel l'appareil branché appartient. Le port relié au routeur doit être configuré en **trunk** (tagged pour tous les VLANs).

## Vérifier l'isolation

Depuis un appareil IoT, essayez de pinguer un PC du VLAN Maison : la requête doit échouer. Utilisez `nmap -sn 192.168.10.0/24` depuis le VLAN IoT pour confirmer qu'aucun hôte du réseau principal n'est visible.

## Bonnes pratiques

- Changez les credentials par défaut de tous les équipements réseau.
- Activez les mises à jour automatiques du firmware du routeur si disponibles.
- Journalisez les connexions inter-VLAN pour détecter les anomalies.
- Désactivez UPnP, surtout sur le segment IoT.
