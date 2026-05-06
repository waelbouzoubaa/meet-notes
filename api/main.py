"""KaptNotes — FastAPI backend.

Exposes transcription, summarization and template management as REST endpoints.
Reuses all existing logic from transcribe.py, summarize.py, processor.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make parent directory importable (transcribe, summarize, processor, doc_extract)
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import transcribe, summarize, templates, documents

app = FastAPI(title="KaptNotes API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Electron app is a local client
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcribe.router, prefix="/api")
app.include_router(summarize.router,  prefix="/api")
app.include_router(templates.router,  prefix="/api")
app.include_router(documents.router,  prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "KaptNotes"}
