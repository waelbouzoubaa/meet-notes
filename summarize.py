"""Summarize a speaker-diarized transcript using Gemini 2.5 Flash."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """\
Tu es un assistant professionnel de prise de notes de réunion.

On te fournit un transcript horodaté et segmenté par locuteur, au format :
  [HH:MM:SS] Speaker X : texte…

Produis un rapport de réunion structuré en Markdown avec les sections suivantes :

## Résumé
Un paragraphe de 3 à 5 phrases résumant l'objet et les conclusions de la réunion.

## Participants identifiés
Liste les identifiants de locuteurs présents (Speaker 1, Speaker 2…) et, si \
le contexte le permet, leur rôle supposé.

## Sujets abordés
Liste à puces des principaux sujets, avec une brève mise en contexte pour chacun.

## Décisions prises
Liste à puces des décisions validées. Si aucune, écris « Aucune décision enregistrée. »

## Actions à mener
Un tableau avec les colonnes : Action | Responsable | Échéance (si mentionnée).
Si aucune action, écris « Aucune action enregistrée. »

## Questions ouvertes
Points non résolus ou sujets nécessitant un suivi.

## Citations notables
2 à 4 citations importantes ou représentatives, attribuées au locuteur avec \
l'horodatage d'origine.

Règles :
- Sois concis mais exhaustif.
- Attribue les propos aux locuteurs identifiés dans le transcript.
- Utilise un ton professionnel.
- Ne fabrique aucune information absente du transcript.
- Réponds en français sauf si le transcript est intégralement dans une autre langue.
"""


def summarize_transcript(
    transcript: str,
    system_prompt: str | None = None,
    doc_parts: list | None = None,
) -> str:
    """Send a diarized transcript (+ optional documents) to Gemini and return the Markdown report.

    Parameters
    ----------
    transcript   : the plain-text diarized transcript
    system_prompt: override the default SYSTEM_PROMPT (e.g. a custom template)
    doc_parts    : list of google.genai types.Part objects (text/images/PDF URIs)
                   built by doc_extract.build_doc_parts()
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY manquante. Renseigne-la dans .env")

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT

    parts: list = [types.Part.from_text(f"Voici le transcript de réunion à résumer :\n\n{transcript}")]

    if doc_parts:
        parts.append(types.Part.from_text(
            "\n\n---\n\nVoici les documents présentés en séance. "
            "Utilise-les pour enrichir l'analyse et le rapport :"
        ))
        parts.extend(doc_parts)

    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            system_instruction=prompt,
            temperature=0.3,
        ),
    )
    return response.text


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: uv run summarize.py <transcript_file>")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    if not transcript_path.exists():
        print(f"Fichier introuvable : {transcript_path}")
        sys.exit(1)

    transcript = transcript_path.read_text(encoding="utf-8")
    print(f"Resume de {transcript_path.name} ({len(transcript)} caracteres)…\n")

    report = summarize_transcript(transcript)
    print(report)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / f"{transcript_path.stem}_report.md"
    report_file.write_text(report, encoding="utf-8")
    print(f"\nRapport sauvegarde : {report_file}")
