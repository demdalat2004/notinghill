"""
NotingHill — services/indexing_service.py
Orchestrates scan → extract → hash → persist pipeline with DB-backed progress and resume.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from ..core import file_classifier, time_utils, job_queue
from ..db import repo_items, repo_jobs, repo_search
from ..services.extractors.text_extractor import TextExtractor
from ..services.extractors.pdf_extractor import PdfExtractor
from ..services.extractors.docx_extractor import DocxExtractor
from ..services.extractors.xlsx_extractor import XlsxExtractor
from ..services.extractors.image_extractor import ImageExtractor
from ..services.extractors.mp3_extractor import Mp3Extractor
from ..services.signatures.sha256_service import compute_sha256
from ..services.signatures.simhash_service import compute_simhash
from ..services.signatures.phash_service import compute_phash

EXTRACTORS = [
    TextExtractor(),
    PdfExtractor(),
    DocxExtractor(),
    XlsxExtractor(),
    ImageExtractor(),
    Mp3Extractor(),
]

_PROGRESS_UPDATE_EVERY = 25


def _get_extractor(path: Path):
    for ext in EXTRACTORS:
        if ext.supports(path):
            return ext
    return None



def _norm(p: str) -> str:
    """Normalize path for cross-platform comparison.
    - resolve() handles symlinks and relative paths
    - normcase() lowercases on Windows (case-insensitive FS)
    - trailing sep ensures /mnt/data != /mnt/data2
    """
    try:
        resolved = str(Path(p).resolve())
    except OSError:
        resolved = os.path.abspath(p)
    return os.path.normcase(resolved)


def _get_excluded_root_prefixes(current_root_id: int, current_root_path: str) -> list[str]:
    """
    Return normalized path prefixes of other active roots that are
    subdirectories of current_root_path.
    Works correctly on Windows (case-insensitive, backslash),
    Linux and macOS (case-sensitive, forward slash).
    """
    from ..db.connection import get_db

    # Add trailing sep so prefix check is exact at boundary:
    # /mnt/data/ will NOT match /mnt/data2/foo
    current_prefix = _norm(current_root_path) + os.sep

    excluded: list[str] = []
    with get_db() as con:
        rows = con.execute(
            "SELECT root_id, root_path FROM roots WHERE is_enabled=1 AND root_id!=?",
            (current_root_id,),
        ).fetchall()

    for row in rows:
        other_norm = _norm(row["root_path"])
        # other is inside current → exclude during scan
        if other_norm.startswith(current_prefix):
            excluded.append(other_norm + os.sep)

    return excluded


def _is_excluded(fpath: Path, excluded_prefixes: list[str]) -> bool:
    """Check if a path falls under any excluded prefix. Cross-platform safe."""
    if not excluded_prefixes:
        return False
    normalized = os.path.normcase(str(fpath))
    return any(normalized.startswith(p) for p in excluded_prefixes)


def resume_incomplete_jobs() -> list[int]:
    resumed: list[int] = []
    jobs = repo_jobs.list_resumable_jobs()
    for job in jobs:
        root_path = job.get("root_path")
        root_id = job.get("root_id")
        if not root_path or not root_id or not job.get("is_enabled", 1):
            continue

        if job.get("status") == "finalizing" and (job.get("pending_count", 0) or 0) <= 0:
            job_queue.enqueue(_try_finish_job, job["job_id"])
            resumed.append(job["job_id"])
            continue

        start_index(root_id, root_path, full_rescan=False, resume_job_id=job["job_id"])
        resumed.append(job["job_id"])
    return resumed


def start_index(root_id: int, root_path: str, full_rescan: bool = False, resume_job_id: int | None = None) -> int:
    if resume_job_id is not None:
        job_id = resume_job_id
        repo_jobs.prepare_resume(job_id)
    else:
        job_id = repo_jobs.create_job(root_id, "full_scan" if full_rescan else "incremental")

    job_queue.enqueue(_run_scan, root_id, root_path, job_id, full_rescan)
    return job_id


def _run_scan(root_id: int, root_path: str, job_id: int, full_rescan: bool) -> None:
    root = Path(root_path)
    if not root.exists():
        repo_jobs.update_job(
            job_id,
            status="error",
            note="Path not found",
            current_file="",
            finished_ts=int(time.time()),
        )
        return

    job = repo_jobs.get_job(job_id) or {}
    already_indexed = int(job.get("indexed_count", 0) or 0)
    scanned = 0
    queued_new = 0

    repo_jobs.update_job(
        job_id,
        status="running",
        note=None,
        current_file="",
        scan_complete=0,
        pending_count=0,
        queued_count=already_indexed,
        updated_ts=int(time.time()),
    )

    try:
        excluded_prefixes = _get_excluded_root_prefixes(root_id, root_path)

        for dirpath, dirnames, filenames in os.walk(root):
            # Skip entire subdirectories covered by another active root + ignored dirs
            dirnames[:] = [
                d for d in dirnames
                if not file_classifier.should_ignore(Path(dirpath) / d)
                and not _is_excluded(Path(dirpath) / d, excluded_prefixes)
            ]
            for fname in filenames:
                fpath = Path(dirpath) / fname

                # Skip files under another active root's path (cross-platform)
                if _is_excluded(fpath, excluded_prefixes):
                    continue

                if file_classifier.should_ignore(fpath):
                    continue

                scanned += 1
                if scanned == 1 or scanned % _PROGRESS_UPDATE_EVERY == 0:
                    repo_jobs.update_job(
                        job_id,
                        scanned_count=scanned,
                        current_file=str(fpath),
                    )

                if not full_rescan:
                    existing_id = repo_items.get_item_id_by_path(str(fpath))
                    if existing_id:
                        try:
                            s = fpath.stat()
                            token = f"{s.st_size}:{int(s.st_mtime)}"
                            from ..db.connection import get_db

                            with get_db() as con:
                                row = con.execute(
                                    "SELECT change_token FROM items WHERE item_id=?",
                                    (existing_id,),
                                ).fetchone()
                            if row and row["change_token"] == token:
                                continue
                        except OSError:
                            pass

                job_queue.enqueue(_process_file, root_id, str(fpath), job_id)
                queued_new += 1
                if queued_new == 1 or queued_new % _PROGRESS_UPDATE_EVERY == 0:
                    repo_jobs.update_job(
                        job_id,
                        queued_count=already_indexed + queued_new,
                        pending_count=queued_new,
                        current_file=str(fpath),
                    )

        repo_jobs.update_job(
            job_id,
            scanned_count=scanned,
            queued_count=already_indexed + queued_new,
            pending_count=queued_new,
            scan_complete=1,
            current_file="",
        )
        job_queue.enqueue(_try_finish_job, job_id)
    except Exception as exc:
        repo_jobs.update_job(
            job_id,
            status="error",
            note=str(exc),
            current_file="",
            finished_ts=int(time.time()),
        )



def _process_file(root_id: int, full_path: str, job_id: int) -> None:
    path = Path(full_path)
    try:
        s = path.stat()
    except OSError as exc:
        repo_jobs.log_error(job_id, full_path, "stat", "OS_ERROR", str(exc))
        repo_jobs.bump_job_counts(job_id, pending_delta=-1, current_file=full_path)
        _try_finish_job(job_id)
        return

    file_type_group = file_classifier.classify(path)
    times = time_utils.get_file_times(path)
    token = f"{s.st_size}:{int(s.st_mtime)}"

    item_data = {
        "root_id": root_id,
        "full_path": full_path,
        "parent_path": str(path.parent),
        "file_name": path.name,
        "extension": path.suffix.lower(),
        "mime_type": None,
        "size_bytes": s.st_size,
        "file_type_group": file_type_group,
        "indexing_status": "processing",
        "is_deleted": 0,
        "is_hidden": path.name.startswith("."),
        "is_system": 0,
        "first_seen_ts": int(time.time()),
        "last_seen_ts": int(time.time()),
        "last_indexed_ts": int(time.time()),
        "change_token": token,
        **times,
    }

    try:
        item_id = repo_items.upsert_item(item_data)
    except Exception as exc:
        repo_jobs.log_error(job_id, full_path, "db_insert", "DB_ERROR", str(exc))
        repo_jobs.bump_job_counts(job_id, pending_delta=-1, current_file=full_path)
        _try_finish_job(job_id)
        return

    extractor = _get_extractor(path)
    if extractor:
        try:
            result = extractor.extract(path)
            if result.metadata:
                from ..db import repo_content as rc
                from ..db.connection import get_db

                rc.upsert_metadata(item_id, result.metadata)
                if result.metadata.get("taken_ts"):
                    updated = time_utils.inject_metadata_time(times, result.metadata)
                    with get_db() as con:
                        con.execute(
                            """
                            UPDATE items
                            SET best_time_ts=?, best_time_source=?, best_time_confidence=?
                            WHERE item_id=?
                            """,
                            (
                                updated["best_time_ts"],
                                updated["best_time_source"],
                                updated["best_time_confidence"],
                                item_id,
                            ),
                        )
                        con.commit()

            text = result.text or ""
            preview = result.preview or text[:400]
            from ..db import repo_content as rc2

            rc2.upsert_content(item_id, text, preview, len(text), result.language)

            meta_title = (result.metadata or {}).get("title", "")
            repo_search.fts_index_item(item_id, path.name, full_path, text, meta_title)

        except Exception as exc:
            repo_jobs.log_error(job_id, full_path, "extract", "EXTRACT_ERROR", str(exc))

    try:
        sha = compute_sha256(path)
        simhash = None
        phash_val = None

        if file_type_group in ("text", "code", "pdf", "office"):
            from ..db.connection import get_db

            with get_db() as con:
                row = con.execute(
                    "SELECT extracted_text FROM item_content WHERE item_id=?",
                    (item_id,),
                ).fetchone()
            if row and row["extracted_text"]:
                simhash = compute_simhash(row["extracted_text"])

        if file_type_group == "image":
            phash_val = compute_phash(path)

        repo_items.update_hashes(item_id, sha256=sha, simhash64=simhash, phash=phash_val)
    except Exception as exc:
        repo_jobs.log_error(job_id, full_path, "hash", "HASH_ERROR", str(exc))

    repo_items.update_status(item_id, indexing_status="done")
    repo_jobs.bump_job_counts(job_id, indexed_delta=1, pending_delta=-1, current_file=full_path)
    _try_finish_job(job_id)



def _try_finish_job(job_id: int) -> None:
    if not repo_jobs.try_mark_finalizing(job_id):
        return

    try:
        from ..services.dedup_service import run_exact_dedup, run_text_dedup, run_image_dedup

        try:
            run_exact_dedup()
            run_text_dedup()
            run_image_dedup()
        except Exception as exc:
            print(f"[Dedup] Error: {exc}")

        repo_jobs.update_job(
            job_id,
            status="done",
            current_file="",
            finished_ts=int(time.time()),
        )
    except Exception as exc:
        repo_jobs.update_job(
            job_id,
            status="error",
            note=str(exc),
            current_file="",
            finished_ts=int(time.time()),
        )
