# Meet-Notes Agent v1.0 — Tout Gemini

Transcrit, diarise et résume vos réunions à partir d'un fichier audio, en utilisant uniquement l'API Gemini.

## Fonctionnement

```
Audio (.mp3/.wav/.m4a)  →  Gemini 2.5 Flash (transcription + diarisation)  →  Gemini 2.5 Flash (résumé)  →  Rapport .md
```

Pas de GPU, pas de modèle local, pas de dépendance lourde. Juste une clé API Gemini.

## Prérequis

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/)
- Une clé API Gemini → [Google AI Studio](https://aistudio.google.com/apikey)

## Installation

```bash
cd meet-notes-agent

# Configurer
cp .env.example .env
# → Remplir GEMINI_API_KEY dans .env

# Installer (2 dépendances seulement)
uv sync
```

## Utilisation

```bash
# Pipeline complet (transcription + résumé)
uv run main.py reunion.mp3

# Audio en anglais
uv run main.py meeting.wav --language en

# Transcription seule
uv run main.py reunion.mp3 --transcript-only

# Résumé d'un transcript existant
uv run main.py dummy.wav --skip-transcription transcripts/reunion.txt
```

## Sorties

| Dossier | Contenu |
|---------|---------|
| `transcripts/` | Transcripts horodatés avec locuteurs (`.txt`) |
| `reports/` | Rapports structurés (`.md`) |

### Exemple de transcript

```
[00:00:05] Speaker 1 : Bonjour à tous, on commence la réunion.
[00:00:12] Speaker 2 : Merci. Premier point à l'ordre du jour…
[00:01:02] Speaker 3 : J'ai quelques remarques sur le budget.
```

### Sections du rapport

Résumé, Participants, Sujets abordés, Décisions, Actions à mener, Questions ouvertes, Citations notables.

## Architecture

```
meet-notes-agent/
├── .env.example       # Clé API Gemini
├── pyproject.toml     # 2 dépendances
├── main.py            # CLI
├── transcribe.py      # Upload audio → Gemini → transcript diarisé
├── summarize.py       # Transcript → Gemini → rapport Markdown
├── transcripts/       # Transcripts bruts
└── reports/           # Rapports finaux
```

## Coûts

| Durée audio | Coût estimé (Gemini 2.5 Flash) |
|-------------|-------------------------------|
| 30 min | ~$0.01 |
| 1 heure | ~$0.02 |
| 2 heures | ~$0.04 |
| 50 réunions/mois | ~$0.50 – $1.00 |

Gemini propose un tier gratuit avec limites de débit qui peut couvrir un usage modéré.

## Comparaison avec la v0.3 (WhisperX + Pyannote)

| | v0.3 (WhisperX) | v1.0 (Tout Gemini) |
|-|-----------------|-------------------|
| GPU requis | Oui (ou CPU très lent) | Non |
| Dépendances | ~15 (PyTorch, etc.) | 2 |
| Installation | ~10 min + debug | ~30 sec |
| Espace disque | ~5 Go de modèles | ~10 Mo |
| Qualité STT | Bonne (large-v3) | Excellente |
| Diarisation | Correcte (Pyannote) | Très bonne (native) |
| Fonctionne offline | Oui | Non (API) |
| Coût | Gratuit (hors GPU) | ~$0.02/réunion |
