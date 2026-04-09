"""
NotingHill — api/routes_images.py
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from config import THUMBNAILS_DIR
from ..db import repo_items

router = APIRouter(prefix="/api/images", tags=["images"])


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heic", ".heif"}


def _safe_item(item_id: int) -> dict:
    item = repo_items.get_item(item_id)
    if not item:
        raise HTTPException(404, "Image not found")
    if item.get("file_type_group") != "image":
        raise HTTPException(400, "Item is not an image")
    path = Path(item["full_path"])
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Image file missing")
    item["_path_obj"] = path
    return item


def _thumb_file_path(item: dict, size: int) -> Path:
    token = item.get("change_token") or "0"
    digest = hashlib.sha1(f"{item['item_id']}:{token}:{size}".encode("utf-8")).hexdigest()
    return THUMBNAILS_DIR / f"{digest}.jpg"


def _ensure_thumbnail(item: dict, size: int) -> Path:
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    thumb_path = _thumb_file_path(item, size)
    if thumb_path.exists():
        return thumb_path

    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise HTTPException(500, f"Pillow not installed: {exc}")

    source = item["_path_obj"]
    with Image.open(str(source)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        background = Image.new("RGB", (size, size), (8, 14, 22))
        x = (size - img.width) // 2
        y = (size - img.height) // 2
        background.paste(img, (x, y))
        background.save(thumb_path, format="JPEG", quality=88, optimize=True)
    return thumb_path


@router.get("")
def list_images(
    q: str = Query(default=""),
    root_id: Optional[int] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    since_ts: Optional[int] = None,
    until_ts: Optional[int] = None,
    has_gps: Optional[int] = None,
    order_by: str = "best_time_ts DESC",
    limit: int = Query(default=120, le=300),
    offset: int = 0,
):
    results = repo_items.list_images(
        q=q,
        root_id=root_id,
        min_size=min_size,
        max_size=max_size,
        since_ts=since_ts,
        until_ts=until_ts,
        has_gps=has_gps,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    return {"results": results, "count": len(results), "query": q}


@router.get("/item/{item_id}")
def get_image_item(item_id: int):
    item = _safe_item(item_id)
    item.pop("_path_obj", None)
    return item


@router.get("/thumb/{item_id}")
def get_thumbnail(item_id: int, size: int = Query(default=240, ge=64, le=1024)):
    item = _safe_item(item_id)
    thumb_path = _ensure_thumbnail(item, size)
    return FileResponse(str(thumb_path), media_type="image/jpeg")


@router.get("/original/{item_id}")
def get_original(item_id: int):
    item = _safe_item(item_id)
    path = item["_path_obj"]
    media_type = f"image/{path.suffix.lower().lstrip('.')}" if path.suffix.lower() in IMAGE_EXTS else None
    return FileResponse(str(path), media_type=media_type, filename=path.name)


@router.get("/preview/{item_id}")
def get_preview(item_id: int, max_edge: int = Query(default=1800, ge=400, le=4000)):
    item = _safe_item(item_id)
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise HTTPException(500, f"Pillow not installed: {exc}")

    path = item["_path_obj"]
    with Image.open(str(path)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True)
        buf.seek(0)
    return StreamingResponse(buf, media_type="image/jpeg")
