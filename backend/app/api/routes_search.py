"""
NotingHill — api/routes_search.py
"""
from __future__ import annotations

import mimetypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from ..db import repo_items
from ..services import llm_service, search_service

router = APIRouter(prefix="/api/search", tags=["search"])

TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
    ".yaml", ".yml", ".xml", ".html", ".css", ".scss", ".sql", ".csv", ".log",
    ".ini", ".cfg", ".toml", ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs",
    ".php", ".rb", ".sh", ".bat", ".ps1",
}


class AskRequest(BaseModel):
    q: str
    file_type: Optional[str] = None
    extension: Optional[str] = None
    root_id: Optional[int] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    since_ts: Optional[int] = None
    until_ts: Optional[int] = None
    order_by: str = "rank"
    limit: int = 12
    offset: int = 0


def _safe_item(item_id: int) -> dict:
    item = repo_items.get_item(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    path = Path(item["full_path"])
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "File missing")
    item["_path_obj"] = path
    return item


def _guess_media_type(path: Path, fallback: str = "application/octet-stream") -> str:
    media_type, _ = mimetypes.guess_type(str(path))
    if not media_type:
        ext = path.suffix.lower()
        if ext == ".md":
            media_type = "text/markdown"
        elif ext == ".csv":
            media_type = "text/csv"
        elif ext == ".json":
            media_type = "application/json"
        elif ext in {".yaml", ".yml"}:
            media_type = "text/yaml"
        else:
            media_type = fallback
    return media_type


@router.get("")
def search(
    q: str = Query(default=""),
    file_type: Optional[str] = None,
    extension: Optional[str] = None,
    root_id: Optional[int] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    since_ts: Optional[int] = None,
    until_ts: Optional[int] = None,
    order_by: str = "rank",
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    results = search_service.search(
        query=q,
        file_type_group=file_type,
        extension=extension,
        root_id=root_id,
        min_size=min_size,
        max_size=max_size,
        since_ts=since_ts,
        until_ts=until_ts,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    return {"results": results, "count": len(results), "query": q}


@router.post("/ask")
def ask(req: AskRequest):
    try:
        return search_service.ask(
            query=req.q,
            file_type_group=req.file_type,
            extension=req.extension,
            root_id=req.root_id,
            min_size=req.min_size,
            max_size=req.max_size,
            since_ts=req.since_ts,
            until_ts=req.until_ts,
            order_by=req.order_by,
            limit=req.limit,
            offset=req.offset,
        )
    except llm_service.LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/item/{item_id}")
def get_item(item_id: int):
    item = search_service.get_preview(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return item


@router.get("/raw/{item_id}")
def get_raw_file(item_id: int, download: int = 0):
    item = _safe_item(item_id)
    path = item["_path_obj"]
    media_type = _guess_media_type(path)
    headers = None
    if not download:
        headers = {"Content-Disposition": f'inline; filename="{path.name}"'}
    return FileResponse(
        str(path),
        media_type=media_type,
        filename=path.name if download else None,
        headers=headers,
    )


@router.get("/text/{item_id}")
def get_text_preview(item_id: int, max_chars: int = Query(default=50000, ge=500, le=200000)):
    item = _safe_item(item_id)
    extracted = item.get("extracted_text")
    if extracted:
        return PlainTextResponse(extracted[:max_chars], media_type="text/plain; charset=utf-8")

    path = item["_path_obj"]
    if path.suffix.lower() not in TEXT_EXTS:
        raise HTTPException(400, "Text preview not available")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(max_chars)
        return PlainTextResponse(text, media_type="text/plain; charset=utf-8")
    except Exception as exc:
        raise HTTPException(500, f"Unable to read text preview: {exc}")


@router.post("/open/{item_id}")
def open_file(item_id: int):
    item = _safe_item(item_id)
    path = str(item["_path_obj"])
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/reveal/{item_id}")
def reveal_file(item_id: int):
    item = _safe_item(item_id)
    path = str(item["_path_obj"])
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", path], shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", str(Path(path).parent)])
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
