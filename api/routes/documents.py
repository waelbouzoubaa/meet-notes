"""POST /api/summarize-with-docs — transcript + docs → enriched report."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from typing import List

from processor import build_system_prompt
from summarize import summarize_transcript
from doc_extract import build_doc_parts

router = APIRouter()


@router.post("/summarize-with-docs")
async def summarize_with_docs(
    transcript: str = Form(...),
    template: str = Form("socle_commun"),
    extra_context: str = Form(""),
    custom_prompt: str = Form(""),
    documents: List[UploadFile] = File(default=[]),
):
    try:
        system_prompt = build_system_prompt(template, extra_context, custom_prompt)

        doc_parts = []
        for doc in documents:
            doc_bytes = await doc.read()
            doc_parts.extend(build_doc_parts(doc_bytes, doc.filename))

        report = summarize_transcript(
            transcript,
            system_prompt=system_prompt,
            doc_parts=doc_parts or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse({"report": report})
