"""Transcribe and diarize audio using Gemini 2.5 Flash.

Sends the audio file directly to Gemini which handles both
speech-to-text and speaker identification natively.

For files longer than ~15 minutes, the audio is automatically split
into 10-minute chunks to avoid Gemini's repetition/hallucination bug
on long inputs.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"

# Files above this size (MB) are split into chunks before transcription
# Lowered from 20 to 8 MB — Gemini hallucinates on long single-file audio
CHUNK_THRESHOLD_MB = 8
# Duration of each chunk in milliseconds (5 minutes)
CHUNK_DURATION_MS = 5 * 60 * 1000

TRANSCRIPTION_PROMPT = """\
Tu es un transcripteur professionnel. Transcris intégralement cet audio en texte.

IMPORTANT : commence la transcription dès la PREMIÈRE seconde de l'audio, même s'il y a \
du silence ou du bruit au début. Ne saute aucune partie.

Règles strictes :
1. Identifie chaque locuteur distinct et attribue-lui un identifiant stable
   (Speaker 1, Speaker 2, etc.) tout au long du transcript.
2. Chaque segment doit être horodaté au format [HH:MM:SS].
3. Transcris mot pour mot — ne résume pas, ne reformule pas, ne saute rien.
4. Commence TOUJOURS par [00:00:00] même si les premières secondes sont silencieuses.
5. Si un passage est inaudible, écris [inaudible].
6. Note les éléments non-verbaux importants : [rires], [pause], [bruit de fond].
7. Ne répète JAMAIS une ligne déjà transcrite. Avance toujours dans le temps.

Format de sortie attendu (rien d'autre) :

[00:00:00] Speaker 1 : Bonjour à tous, on commence la réunion.
[00:00:12] Speaker 2 : Merci. Premier point à l'ordre du jour.
[00:00:35] Speaker 1 : D'accord, commençons par les résultats.

Transcris maintenant l'intégralité de l'audio ci-joint, de la première à la dernière seconde.
"""

TRANSCRIPTION_PROMPT_EN = """\
You are a professional transcriber. Transcribe this audio in full.

Strict rules:
1. Identify each distinct speaker and assign a stable ID
   (Speaker 1, Speaker 2, etc.) throughout the transcript.
2. Each segment must be timestamped as [HH:MM:SS].
3. Transcribe verbatim — do not summarize, rephrase, or skip anything.
4. If a passage is inaudible, write [inaudible].
5. Note important non-verbal elements: [laughter], [pause], [background noise].
6. NEVER repeat a line already transcribed. Always move forward in time.

Expected output format (nothing else):

[00:00:05] Speaker 1: Good morning everyone, let's start the meeting.
[00:00:12] Speaker 2: Thanks. First item on the agenda…
[00:00:35] Speaker 1: Alright, let's begin with the results.

Now transcribe the entire attached audio.
"""


def _get_mime_type(path: Path) -> str:
    """Infer MIME type from file extension."""
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".wma": "audio/x-ms-wma",
        ".webm": "audio/webm",
    }
    return mime_map.get(path.suffix.lower(), "audio/mpeg")


def _clean_repetitions(transcript: str, max_repeats: int = 3) -> str:
    """Remove hallucination loops: lines repeated more than max_repeats times."""
    lines = transcript.splitlines()
    cleaned: list[str] = []
    repeat_count = 0
    prev_content = None

    for line in lines:
        # Strip timestamp for comparison
        content = re.sub(r"^\[[\d:]+\]\s*", "", line).strip()
        if content == prev_content and content:
            repeat_count += 1
            if repeat_count >= max_repeats:
                continue  # drop the repeated line
        else:
            repeat_count = 0
            prev_content = content
        cleaned.append(line)

    return "\n".join(cleaned)


def _clean_hallucination_blocks(transcript: str, min_block_size: int = 5) -> str:
    """Remove Gemini hallucination blocks of the form:

    [HH:MM:SS] Speaker N : <short text>   (same timestamp, N goes up to 50-100)

    These appear when Gemini loops on a short filler word ("Oui", "Ok", "D'accord")
    and assigns incrementing speaker numbers all sharing the same timestamp.

    Detection heuristic: a run of ≥ min_block_size consecutive lines where:
      - All share the exact same timestamp, AND
      - The stripped text is very short (≤ 30 chars), AND
      - Speaker numbers are incrementing
    """
    lines = transcript.splitlines()
    result: list[str] = []
    i = 0

    ts_re = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]")

    while i < len(lines):
        line = lines[i]
        m = ts_re.match(line)
        if not m:
            result.append(line)
            i += 1
            continue

        ts = m.group(1)
        # Scan ahead: collect consecutive lines with the same timestamp
        block_start = i
        j = i
        while j < len(lines):
            lm = ts_re.match(lines[j])
            if lm and lm.group(1) == ts:
                j += 1
            else:
                break

        block = lines[block_start:j]

        # Check if this block looks like a hallucination
        if len(block) >= min_block_size:
            # All texts must be short (filler words)
            texts = [re.sub(r"^\[[\d:]+\]\s*", "", l).strip() for l in block]
            avg_len = sum(len(t) for t in texts) / len(texts)
            # If average content length is tiny, it's a hallucination block
            if avg_len <= 30:
                n_dropped = len(block) - 1
                print(f"  [HallucinationFilter] Bloc réduit : {n_dropped} lignes supprimées à [{ts}] (1 conservée, moy {avg_len:.0f} chars/ligne)")
                result.append(block[0])  # garde la première ligne au cas où c'est du vrai contenu
                i = j
                continue

        # Not a hallucination — keep the block
        result.extend(block)
        i = j

    return "\n".join(result)


def _offset_timestamps(transcript: str, offset_seconds: int) -> str:
    """Add offset_seconds to all [HH:MM:SS] timestamps in a transcript chunk."""
    if offset_seconds == 0:
        return transcript

    def shift(match: re.Match) -> str:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        total = h * 3600 + m * 60 + s + offset_seconds
        nh, rem = divmod(total, 3600)
        nm, ns = divmod(rem, 60)
        return f"[{nh:02d}:{nm:02d}:{ns:02d}]"

    return re.sub(r"\[(\d+):(\d+):(\d+)\]", shift, transcript)


def _split_audio(audio_path: Path, chunk_duration_ms: int = CHUNK_DURATION_MS) -> list[tuple[Path, int]]:
    """Split audio into 10-min MP3 chunks using pydub + ffmpeg.

    Chunks are always exported as MP3 regardless of the source format,
    because Gemini handles MP3 more reliably than M4A/AAC containers.

    Returns list of (chunk_temp_path, offset_seconds).
    Caller is responsible for deleting the temp files.
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        raise RuntimeError(
            "pydub est nécessaire pour découper les longs fichiers audio.\n"
            "Installe-le avec : uv add pydub\n"
            "Et assure-toi que ffmpeg est installé sur ton système."
        )

    ext = audio_path.suffix.lstrip(".")
    # pydub uses 'mp4' as format name for m4a/aac containers
    load_fmt = "mp4" if ext in ("m4a", "aac") else ext

    print(f"  Chargement de l'audio ({audio_path.name})…")
    audio = AudioSegment.from_file(str(audio_path), format=load_fmt)
    total_ms = len(audio)
    total_min = total_ms / 60000
    n_chunks = -(-total_ms // chunk_duration_ms)  # ceiling division
    print(f"  Durée : {total_min:.1f} min → {n_chunks} chunk(s) de {chunk_duration_ms // 60000} min")

    chunks: list[tuple[Path, int]] = []
    for i, start_ms in enumerate(range(0, total_ms, chunk_duration_ms)):
        segment = audio[start_ms : start_ms + chunk_duration_ms]
        # Always export as MP3 — most reliable format for Gemini Files API
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3",
            prefix=f"meetnotes_chunk_{i:03d}_",
        )
        segment.export(tmp.name, format="mp3", bitrate="128k")
        offset_sec = start_ms // 1000
        end_min = min(start_ms + chunk_duration_ms, total_ms) / 60000
        chunks.append((Path(tmp.name), offset_sec))
        print(f"  Chunk {i + 1}/{n_chunks} : {start_ms / 60000:.0f}–{end_min:.0f} min exporté")

    return chunks


def _transcribe_single(client: genai.Client, audio_path: Path, prompt: str, retries: int = 2) -> str:
    """Upload one audio file to Gemini and return the raw transcript text.

    Retries up to `retries` times on transient 500 errors.
    """
    mime = _get_mime_type(audio_path)

    for attempt in range(retries + 1):
        try:
            uploaded = client.files.upload(
                file=audio_path,
                config=types.UploadFileConfig(mime_type=mime),
            )

            # Wait for processing
            while uploaded.state.name == "PROCESSING":
                time.sleep(2)
                uploaded = client.files.get(name=uploaded.name)

            if uploaded.state.name == "FAILED":
                raise RuntimeError(f"Échec du traitement Gemini : {uploaded.state}")

            response = client.models.generate_content(
                model=MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_uri(file_uri=uploaded.uri, mime_type=mime),
                            types.Part.from_text(text=prompt),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(temperature=0.1),
            )

            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass

            return response.text

        except Exception as e:
            err_str = str(e)
            is_transient = "500" in err_str or "503" in err_str or "INTERNAL" in err_str
            if is_transient and attempt < retries:
                wait = 5 * (attempt + 1)
                print(f"  Erreur transitoire Gemini ({e}) — retry {attempt + 1}/{retries} dans {wait}s…")
                time.sleep(wait)
            else:
                raise


def transcribe_audio(
    audio_path: str | Path,
    language: str = "fr",
) -> tuple[str, float]:
    """Transcribe and diarize an audio file using Gemini.

    Automatically splits files > CHUNK_THRESHOLD_MB into 10-minute chunks
    to avoid Gemini's hallucination/repetition loop on long audio.

    Parameters
    ----------
    audio_path : path to an audio file (.mp3, .wav, .m4a, .ogg, .flac…)
    language   : 'fr' for French prompt, anything else for English prompt.

    Returns
    -------
    (transcript_text, elapsed_seconds)
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY manquante. Renseigne-la dans .env")

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Fichier audio introuvable : {audio_path}")

    t0 = time.perf_counter()
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = TRANSCRIPTION_PROMPT if language == "fr" else TRANSCRIPTION_PROMPT_EN

    size_mb = audio_path.stat().st_size / (1024 * 1024)
    use_chunks = size_mb > CHUNK_THRESHOLD_MB

    if use_chunks:
        print(f"[CHUNKING] Fichier {size_mb:.1f} Mo > {CHUNK_THRESHOLD_MB} Mo → découpage automatique")
        chunks = _split_audio(audio_path)
        transcripts: list[str] = []

        for idx, (chunk_path, offset_sec) in enumerate(chunks):
            print(f"\n[Chunk {idx + 1}/{len(chunks)}] Transcription (offset +{offset_sec}s)…")
            try:
                raw = _transcribe_single(client, chunk_path, prompt)
                raw = _clean_repetitions(raw)
                raw = _clean_hallucination_blocks(raw)
                adjusted = _offset_timestamps(raw, offset_sec)
                transcripts.append(adjusted)
            finally:
                chunk_path.unlink(missing_ok=True)

        full_transcript = "\n".join(transcripts)
    else:
        print(f"[1/3] Upload du fichier : {audio_path.name}")
        full_transcript = _transcribe_single(client, audio_path, prompt)
        full_transcript = _clean_repetitions(full_transcript)
        full_transcript = _clean_hallucination_blocks(full_transcript)

    elapsed = time.perf_counter() - t0
    print(f"\nTranscription terminée en {elapsed:.1f}s")
    return full_transcript, elapsed


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: uv run transcribe.py <audio_file> [language]")
        sys.exit(1)

    path = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) >= 3 else "fr"

    text, secs = transcribe_audio(path, lang)

    out_dir = Path("transcripts")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{Path(path).stem}.txt"
    out_file.write_text(text, encoding="utf-8")
    print(f"Transcript sauvegardé : {out_file}")
