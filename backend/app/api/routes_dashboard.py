"""
NotingHill — api/routes_dashboard.py
"""
from fastapi import APIRouter
from ..db import repo_items, repo_duplicates, repo_jobs
from ..core import job_queue

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard():
    stats = repo_items.get_stats()
    dup_stats = repo_duplicates.get_dup_stats()
    recent = repo_items.get_recent_items(15)
    active_jobs = repo_jobs.get_active_jobs()
    roots = repo_jobs.list_roots()
    progress = job_queue.get_all_progress()

    # Insights
    insights = []
    if dup_stats["groups"] > 0:
        wasted_gb = dup_stats["wasted_bytes"] / (1024**3)
        insights.append({
            "type": "warning",
            "icon": "⚠",
            "text": f"{dup_stats['groups']} duplicate groups found — {wasted_gb:.1f} GB reclaimable",
            "action": "duplicates",
        })
    if stats["errors"] > 0:
        insights.append({
            "type": "error",
            "icon": "✕",
            "text": f"{stats['errors']} files failed to index",
            "action": "indexing",
        })

    # Enrich jobs with live progress
    for j in active_jobs:
        j["progress"] = progress.get(j["job_id"], {})

    return {
        "stats": stats,
        "dup_stats": dup_stats,
        "recent_files": recent,
        "active_jobs": active_jobs,
        "roots": roots,
        "insights": insights,
        "queue_size": job_queue.queue_size(),
    }
