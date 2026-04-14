"""Meet-Notes Agent v1.0 — CLI entry point.

Pipeline: audio file → Gemini (transcription + diarisation) → Gemini (résumé) → rapport .md

Usage:
    uv run main.py reunion.mp3
    uv run main.py meeting.wav --language en
    uv run main.py reunion.m4a --transcript-only
    uv run main.py dummy.wav --skip-transcription transcripts/reunion.txt
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from transcribe import transcribe_audio
from summarize import summarize_transcript


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="meet-notes",
        description="Transcrit et résume une réunion à partir d'un fichier audio.",
    )
    p.add_argument(
        "audio",
        type=Path,
        help="Chemin vers le fichier audio (.mp3, .wav, .m4a, .ogg, .flac…)",
    )
    p.add_argument(
        "--language", "-l",
        default="fr",
        help="Langue du transcript : fr (défaut) ou en.",
    )
    p.add_argument(
        "--transcript-only",
        action="store_true",
        help="Ne faire que la transcription (pas de résumé).",
    )
    p.add_argument(
        "--skip-transcription",
        type=Path,
        default=None,
        metavar="TRANSCRIPT",
        help="Passer directement un transcript existant au résumé.",
    )
    return p


def cli(argv: list[str] | None = None) -> None:
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    t_global = time.perf_counter()

    # ── Resolve or build transcript ──────────────────────────────────────
    if args.skip_transcription:
        transcript_path = args.skip_transcription
        if not transcript_path.exists():
            print(f"Fichier transcript introuvable : {transcript_path}")
            sys.exit(1)
        transcript = transcript_path.read_text(encoding="utf-8")
        stem = transcript_path.stem
        print(f"Transcription ignoree — lecture de {transcript_path.name}")
    else:
        if not args.audio.exists():
            print(f"Fichier audio introuvable : {args.audio}")
            sys.exit(1)

        size_mb = args.audio.stat().st_size / (1024 * 1024)
        print(f"Fichier  : {args.audio.name} ({size_mb:.1f} Mo)")
        print(f"Langue   : {args.language}")
        print()

        transcript, elapsed = transcribe_audio(args.audio, args.language)

        # Save raw transcript
        out_dir = Path("transcripts")
        out_dir.mkdir(exist_ok=True)
        stem = args.audio.stem
        transcript_file = out_dir / f"{stem}.txt"
        transcript_file.write_text(transcript, encoding="utf-8")
        print(f"\nTranscript sauvegarde : {transcript_file}")

    if args.transcript_only:
        print("Mode transcript-only — pas de resume.")
        return

    # ── Summarize ────────────────────────────────────────────────────────
    print("\nGeneration du resume…")
    report = summarize_transcript(transcript)

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    report_file = reports_dir / f"{stem}_report.md"
    report_file.write_text(report, encoding="utf-8")

    elapsed_total = time.perf_counter() - t_global
    print(f"\nRapport sauvegarde : {report_file}")
    print(f"Temps total : {elapsed_total:.1f}s")


if __name__ == "__main__":
    cli()
