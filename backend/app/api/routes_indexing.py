"""
NotingHill — api/routes_indexing.py
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import job_queue
from ..db import repo_jobs
from ..services import indexing_service

router = APIRouter(prefix="/api/index", tags=["indexing"])


class AddRootRequest(BaseModel):
    root_path: str
    label: Optional[str] = None
    start_now: bool = True


class ReindexRequest(BaseModel):
    full_rescan: bool = False


@router.get("/roots")
def list_roots():
    return {"roots": repo_jobs.list_roots()}


@router.get("/pick-folder")
def pick_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        try:
            selected = filedialog.askdirectory(mustexist=True)
        finally:
            root.destroy()

        return {"path": selected or ""}
    except Exception as exc:
        raise HTTPException(500, f"Unable to open folder dialog: {exc}")


@router.post("/roots")
def add_root(req: AddRootRequest):
    import os

    if not os.path.isdir(req.root_path):
        raise HTTPException(400, f"Path not found or not a directory: {req.root_path}")
    root_id = repo_jobs.add_root(req.root_path, req.label)
    job_id = None
    if req.start_now:
        job_id = indexing_service.start_index(root_id, req.root_path)
    return {"root_id": root_id, "job_id": job_id}


@router.delete("/roots/{root_id}")
def remove_root(root_id: int):
    repo_jobs.delete_root(root_id)
    return {"ok": True}


@router.post("/roots/{root_id}/toggle")
def toggle_root(root_id: int, enabled: bool = True):
    repo_jobs.toggle_root(root_id, enabled)
    return {"ok": True}


@router.post("/roots/{root_id}/reindex")
def reindex(root_id: int, req: ReindexRequest = ReindexRequest()):
    roots = repo_jobs.list_roots()
    root = next((r for r in roots if r["root_id"] == root_id), None)
    if not root:
        raise HTTPException(404, "Root not found")
    job_id = indexing_service.start_index(root_id, root["root_path"], req.full_rescan)
    return {"job_id": job_id}


@router.get("/jobs")
def get_jobs():
    active = repo_jobs.get_active_jobs()
    recent = repo_jobs.get_recent_jobs(20)
    for job in active:
        job["progress"] = repo_jobs.build_progress(job)
    for job in recent:
        job["progress"] = repo_jobs.build_progress(job)
    return {"active": active, "recent": recent, "queue_size": job_queue.queue_size()}


@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    job = repo_jobs.get_job(job_id)
    if not job:
        raise HTTPException(404)
    job["progress"] = repo_jobs.build_progress(job)
    job["errors"] = repo_jobs.get_job_errors(job_id, 50)
    return job


@router.get("/jobs/{job_id}/progress")
def job_progress(job_id: int):
    job = repo_jobs.get_job(job_id)
    if not job:
        raise HTTPException(404)
    return repo_jobs.build_progress(job)
