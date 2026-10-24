---
title: Fine-tuner un LLM open source sur ses propres données
description: Adaptez Llama, Mistral ou Qwen à votre domaine en quelques heures avec LoRA et Unsloth.
category: IA avancée
---
Le fine-tuning permet de spécialiser un modèle de langage sur un vocabulaire, un style ou une tâche précise sans repartir de zéro. Grâce aux adaptateurs LoRA, le coût en VRAM et en temps est désormais accessible sur une carte grand public.

## Comprendre LoRA

LoRA (Low-Rank Adaptation) n'entraîne pas tout le réseau : il ajoute de petites matrices d'adaptation à certaines couches. Résultat : on n'entraîne que 1 à 5 % des paramètres, la mémoire GPU nécessaire chute de 70 à 90 % et le modèle de base reste intact.

## Prérequis matériels

| VRAM disponible | Modèle conseillé |
|---|---|
| 8 Go | Llama 3.1 8B (4-bit) |
| 12–16 Go | Mistral Nemo 12B (4-bit) |
| 24 Go | Qwen2.5 14B (4-bit) |

Un GPU NVIDIA avec support CUDA est requis. Sur AMD, utilisez ROCm 5.7+.

## Préparer ses données

La qualité prime sur la quantité. Un format `instruction / réponse` par paire convient à la plupart des cas.

```json
{"instruction": "Résume ce texte en deux phrases.", "output": "Résumé concis ici."}
```

- Minimum recommandé : 200 à 500 exemples de bonne qualité.
- Nettoyez les doublons et les réponses hors sujet.
- Séparez 10 % des données pour la validation.

## Pipeline avec Unsloth

[Unsloth](https://github.com/unslothai/unsloth) accélère l'entraînement de 2× et réduit la VRAM requise.

```bash
pip install unsloth
```

```python
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
	"unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
	max_seq_length=2048, load_in_4bit=True
)
model = FastLanguageModel.get_peft_model(
	model, r=16, target_modules=["q_proj","v_proj"],
	lora_alpha=16, lora_dropout=0.05
)
```

Entraînez ensuite avec `SFTTrainer` de la bibliothèque `trl`, en passant votre dataset Hugging Face ou un fichier JSON local.

## Évaluer et exporter

- Surveillez la `eval_loss` : elle doit diminuer sans stagner ni remonter.
- Exportez en GGUF pour Ollama : `llama.cpp/convert.py --outtype q4_k_m`.
- Testez avec plusieurs prompts hors dataset avant de valider.

## Pièges courants

- **Surapprentissage** : trop d'epochs sur peu de données → la perte de validation remonte.
- **Oubli catastrophique** : trop d'exemples très différents du domaine de base → le modèle perd ses capacités générales.
- **Format instable** : vérifiez que votre template de prompt correspond exactement à celui du modèle de base.
