"""GET /api/templates — list and manage report templates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from processor import list_templates, load_template, save_template

router = APIRouter()


@router.get("/templates")
def get_templates():
    return JSONResponse({"templates": list_templates()})


@router.get("/templates/{name}")
def get_template(name: str):
    try:
        content = load_template(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Template '{name}' introuvable")
    return JSONResponse({"name": name, "content": content})


class SaveTemplateRequest(BaseModel):
    name: str
    content: str


@router.post("/templates")
def post_template(req: SaveTemplateRequest):
    save_template(req.name, req.content)
    return JSONResponse({"saved": req.name})
