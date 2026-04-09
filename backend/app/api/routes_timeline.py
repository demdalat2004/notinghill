"""
NotingHill — api/routes_timeline.py
"""
from fastapi import APIRouter, Query
from typing import Optional
from ..db import repo_timeline

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("/buckets")
def get_buckets(
    zoom: str = Query(default="month", regex="^(year|month|day)$"),
    file_type: Optional[str] = None,
    since_ts: Optional[int] = None,
    until_ts: Optional[int] = None,
):
    buckets = repo_timeline.get_timeline_buckets(
        zoom=zoom, file_type_group=file_type,
        since_ts=since_ts, until_ts=until_ts
    )
    return {"buckets": buckets, "zoom": zoom}


@router.get("/items/{bucket}")
def get_bucket_items(
    bucket: str,
    zoom: str = Query(default="month", regex="^(year|month|day)$"),
    file_type: Optional[str] = None,
    limit: int = 100,
):
    items = repo_timeline.get_items_in_bucket(bucket, zoom=zoom, file_type_group=file_type, limit=limit)
    return {"items": items, "bucket": bucket}
