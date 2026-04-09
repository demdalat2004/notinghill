"""
NotingHill — api/routes_duplicates.py
"""
from fastapi import APIRouter, Query
from ..db import repo_duplicates

router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])


@router.get("/exact")
def exact_duplicates(limit: int = 50, offset: int = 0):
    groups = repo_duplicates.get_exact_duplicate_groups(limit, offset)
    stats = repo_duplicates.get_dup_stats()
    return {"groups": groups, "stats": stats}


@router.get("/similar-text")
def similar_text(limit: int = 50, offset: int = 0):
    groups = repo_duplicates.get_similar_groups("similar_text", limit, offset)
    return {"groups": groups}


@router.get("/similar-images")
def similar_images(limit: int = 50, offset: int = 0):
    groups = repo_duplicates.get_similar_groups("similar_image", limit, offset)
    return {"groups": groups}


@router.post("/review/{group_item_id}")
def mark_reviewed(group_item_id: int, status: str = "reviewed"):
    repo_duplicates.update_review_status(group_item_id, status)
    return {"ok": True}


@router.get("/stats")
def dup_stats():
    return repo_duplicates.get_dup_stats()
