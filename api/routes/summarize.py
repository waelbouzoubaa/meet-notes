"""POST /api/summarize — transcript + template → Markdown report."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from processor import build_system_prompt
from summarize import summarize_transcript

router = APIRouter()


class SummarizeRequest(BaseModel):
    transcript: str
    template: str = "socle_commun"
    extra_context: str = ""
    custom_prompt: str = ""


@router.post("/summarize")
async def summarize_endpoint(req: SummarizeRequest):
    try:
        system_prompt = build_system_prompt(req.template, req.extra_context, req.custom_prompt)
        report = summarize_transcript(req.transcript, system_prompt=system_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse({"report": report})
