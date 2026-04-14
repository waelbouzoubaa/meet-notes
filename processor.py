"""Central processing brain for Meet Notes.

Handles two source types:
  - "audio"  → upload audio file to Gemini → transcription + diarisation → report
  - "teams"  → plain-text transcript from Teams API → report only

Public API
----------
list_templates()            → list of template names
load_template(name)         → system prompt string
extract_speakers(transcript) → list of unique "Speaker X" IDs
apply_speaker_names(...)    → replaced transcript
process_meeting(...)        → (transcript, report)
save_output(...)            → saved file path
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

from transcribe import transcribe_audio
from summarize import summarize_transcript

TEMPLATES_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path(__file__).parent / "reports"


# ── Template helpers ──────────────────────────────────────────────────────────

def list_templates() -> list[str]:
    """Return sorted list of template names (without .txt extension)."""
    if not TEMPLATES_DIR.exists():
        return []
    names = sorted(p.stem for p in TEMPLATES_DIR.glob("*.txt"))
    return names + ["custom"]


def load_template(name: str) -> str:
    """Load a prompt from templates/<name>.txt. Raises FileNotFoundError if missing."""
    path = TEMPLATES_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Template introuvable : {path}")
    return path.read_text(encoding="utf-8")


def save_template(name: str, content: str) -> None:
    """Persist a custom template to disk."""
    TEMPLATES_DIR.mkdir(exist_ok=True)
    (TEMPLATES_DIR / f"{name}.txt").write_text(content, encoding="utf-8")


# ── Speaker helpers ───────────────────────────────────────────────────────────

def extract_speakers(transcript: str) -> list[str]:
    """Extract unique speaker IDs from a diarized transcript (ordered by first appearance)."""
    pattern = re.compile(r"\[[\d:]+\]\s+(Speaker \d+)\s*[:\-]", re.MULTILINE)
    seen: set[str] = set()
    unique: list[str] = []
    for match in pattern.finditer(transcript):
        sid = match.group(1)
        if sid not in seen:
            seen.add(sid)
            unique.append(sid)
    return unique


def apply_speaker_names(transcript: str, speaker_map: dict[str, str]) -> str:
    """Replace generic Speaker IDs with real names throughout the transcript."""
    result = transcript
    # Sort by speaker number descending to avoid "Speaker 1" replacing inside "Speaker 10"
    for speaker_id in sorted(speaker_map.keys(), key=lambda s: -int(re.search(r"\d+", s).group())):
        real_name = speaker_map[speaker_id].strip()
        if real_name:
            result = result.replace(speaker_id, real_name)
    return result


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_system_prompt(template_name: str, extra_context: str = "", custom_prompt: str = "") -> str:
    """Assemble the final system prompt from a template + optional user context."""
    if template_name == "custom":
        base = custom_prompt.strip() or "Tu es un assistant de réunion professionnel. Résume le transcript fourni."
    else:
        base = load_template(template_name)

    if extra_context.strip():
        header = (
            "## Contexte fourni par l'utilisateur\n"
            f"{extra_context.strip()}\n\n"
            "Tiens compte de ce contexte pour personnaliser l'analyse et le rapport.\n\n"
            "---\n\n"
        )
        return header + base
    return base


# ── Core pipeline ─────────────────────────────────────────────────────────────

def process_meeting(
    source_type: Literal["audio", "teams"],
    content,                        # Path for "audio", str for "teams"
    template_name: str,
    language: str = "fr",
    extra_context: str = "",
    speaker_map: dict[str, str] | None = None,
    custom_prompt: str = "",
) -> tuple[str, str]:
    """Full pipeline: source → transcript → (optional renaming) → report.

    Returns
    -------
    (transcript, report) — both as plain strings
    """
    # ── Step 1 : Transcript ───────────────────────────────────────────────
    if source_type == "audio":
        transcript, _ = transcribe_audio(content, language)
    elif source_type == "teams":
        transcript = str(content)
    else:
        raise ValueError(f"source_type inconnu : {source_type!r}")

    # ── Step 2 : Speaker renaming ─────────────────────────────────────────
    if speaker_map:
        transcript = apply_speaker_names(transcript, speaker_map)

    # ── Step 3 : Report generation ────────────────────────────────────────
    system_prompt = build_system_prompt(template_name, extra_context, custom_prompt)
    report = summarize_transcript(transcript, system_prompt=system_prompt)

    return transcript, report


# ── Output / save helpers ─────────────────────────────────────────────────────

def save_output(
    content: str,
    stem: str,
    output_type: Literal["transcript", "report"],
    source_label: Literal["AUTO", "MANUAL"] = "MANUAL",
    extra_dir: Path | None = None,
) -> Path:
    """Save content to the reports/ (or transcripts/) folder.

    Parameters
    ----------
    content      : text to write
    stem         : base file name without extension
    output_type  : "transcript" → .txt, "report" → .md
    source_label : prefix added to the file name ([AUTO] or [MANUAL])
    extra_dir    : if set, also copies the file there (e.g. OneDrive sync folder)

    Returns
    -------
    Path to the saved file
    """
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    ext = ".txt" if output_type == "transcript" else ".md"
    subfolder = "transcripts" if output_type == "transcript" else "reports"

    out_dir = Path(__file__).parent / subfolder
    out_dir.mkdir(exist_ok=True)

    filename = f"[{source_label}] {date_prefix}_{stem}{ext}"
    out_path = out_dir / filename
    out_path.write_text(content, encoding="utf-8")

    if extra_dir:
        extra_dir = Path(extra_dir)
        extra_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, extra_dir / filename)

    return out_path
