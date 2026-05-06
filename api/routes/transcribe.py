"""POST /api/transcribe — receive audio file, return diarized transcript."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from transcribe import transcribe_audio

router = APIRouter()


@router.post("/transcribe")
async def transcribe_endpoint(
    audio: UploadFile = File(...),
    language: str = Form("fr"),
    engine: str = Form("assemblyai"),
):
    suffix = Path(audio.filename).suffix or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)

    try:
        transcript, elapsed = transcribe_audio(tmp_path, language=language, engine=engine)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    return JSONResponse({"transcript": transcript, "elapsed": round(elapsed, 2)})
