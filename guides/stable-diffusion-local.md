---
title: Stable Diffusion en local : installer et optimiser WebUI
description: Générez des images par IA sur votre propre machine, sans abonnement ni censure imposée.
category: IA avancée
---
Stable Diffusion est un modèle de génération d'images open source qui tourne sur votre GPU. Automatic1111 WebUI est l'interface la plus complète pour l'explorer, personnaliser et automatiser.

## Prérequis matériels

- **GPU NVIDIA** avec au moins 4 Go de VRAM (8 Go recommandés pour de bons résultats en 512×512 et plus).
- **RAM système** : 16 Go minimum.
- **Stockage** : 20 Go pour le modèle de base, plus selon les extensions.
- Sur AMD : expérimental via ROCm ou DirectML (Windows), moins stable.

## Installation (Windows)

1. Installez [Python 3.10](https://www.python.org/downloads/release/python-3106/) (cochez « Add to PATH »).
2. Installez [Git](https://git-scm.com/).
3. Clonez le dépôt :
```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui
```
4. Téléchargez un modèle `.safetensors` depuis [CivitAI](https://civitai.com) ou [Hugging Face](https://huggingface.co) et placez-le dans `models/Stable-diffusion/`.
5. Lancez `webui-user.bat` — la première exécution installe automatiquement toutes les dépendances.

## Comprendre les paramètres clés

| Paramètre | Rôle | Valeur de départ |
|---|---|---|
| Steps | Nombre d'itérations de débruitage | 20–30 |
| CFG Scale | Respect du prompt (trop haut = sur-saturé) | 7 |
| Sampler | Algorithme de débruitage | DPM++ 2M Karras |
| Seed | Reproductibilité (-1 = aléatoire) | -1 |
| Résolution | Entraînement de base : 512×512 | 512×512 ou 768×768 |

## Écrire un prompt efficace

```
photo portrait d'une femme, lumière dorée, bokeh, Nikon D850, f/1.8,
hyperréaliste, très détaillé

Négatif : flou, texte, filigrane, membres supplémentaires, visage déformé
```

- Commencez par le sujet principal, puis le style, puis les détails techniques.
- Le **prompt négatif** est aussi important que le positif.
- Utilisez les parenthèses pour pondérer : `(yeux verts:1.3)` accentue ce terme de 30 %.

## Accélérer la génération

- **xFormers** : ajoutez `--xformers` dans `COMMANDLINE_ARGS` du fichier `webui-user.bat` pour +20–40 % de vitesse.
- **LCM Lora** : permet de descendre à 4–8 steps sans perte de qualité notable.
- **Tiled VAE** : activez-le dans les extensions pour générer de grandes images sans Out of Memory.

## Extensions utiles

- **ControlNet** : contrôle la pose, la profondeur, les contours à partir d'une image de référence.
- **ADetailer** : corrige automatiquement les visages et les mains après la génération initiale.
- **Ultimate SD Upscale** : agrandissement haute qualité sans artefacts.

## Gérer l'espace disque

Les modèles, embeddings et LoRAs s'accumulent vite. Créez un dossier de modèles en dehors du répertoire WebUI et pointez-y via `--ckpt-dir` pour éviter de tout déplacer à chaque mise à jour.
