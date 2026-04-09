"""
NotingHill — services/indexing_service.py
Orchestrates scan → extract → hash → persist pipeline.

Key optimisations vs. original:
  • Incremental scan: one batch query loads ALL (path→change_token) instead of
    N per-file queries.
  • _process_file: all DB writes go into a single connection/transaction per file
    (one commit instead of ~8-9).
  • FTS index is written inside the same transaction.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from ..core import file_classifier, time_utils, job_queue
from ..db import repo_items, repo_jobs, repo_search
from ..db.connection import get_db
from ..db.repo_content import _upsert_content_tx, _upsert_metadata_tx
from ..db.repo_search import _fts_index_item_tx
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


def start_index(root_id: int, root_path: str, full_rescan: bool = False,
                resume_job_id: int | None = None) -> int:
    if resume_job_id is not None:
        job_id = resume_job_id
        repo_jobs.prepare_resume(job_id)
    else:
        job_id = repo_jobs.create_job(root_id, "full_scan" if full_rescan else "incremental")

    job_queue.enqueue(_run_scan, root_id, root_path, job_id, full_rescan)
    return job_id


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

    # ── Batch load existing change_tokens (one query, not N) ──────────────
    known_tokens: dict[str, str] = {}
    if not full_rescan:
        known_tokens = repo_items.batch_load_change_tokens(root_id)

    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d for d in dirnames
                if not file_classifier.should_ignore(Path(dirpath) / d)
            ]
            for fname in filenames:
                fpath = Path(dirpath) / fname
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
                    try:
                        s = fpath.stat()
                        token = f"{s.st_size}:{int(s.st_mtime)}"
                        if known_tokens.get(str(fpath)) == token:
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
    """
    Process one file — all DB writes committed in a single transaction.
    Order: upsert_item → extract content+metadata → hash → fts_index → status=done
    """
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
    now = int(time.time())

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
        "is_hidden": int(path.name.startswith(".")),
        "is_system": 0,
        "first_seen_ts": now,
        "last_seen_ts": now,
        "last_indexed_ts": now,
        "change_token": token,
        **times,
    }

    # ── Run extraction outside the DB transaction (CPU/IO bound) ─────────
    extractor = _get_extractor(path)
    result = None
    extract_error: str | None = None
    if extractor:
        try:
            result = extractor.extract(path)
        except Exception as exc:
            extract_error = str(exc)
            repo_jobs.log_error(job_id, full_path, "extract", "EXTRACT_ERROR", str(exc))

    # ── Compute hashes outside transaction ────────────────────────────────
    sha = None
    simhash_val = None
    phash_val = None
    try:
        sha = compute_sha256(path)

        if file_type_group in ("text", "code", "pdf", "office") and result and result.text:
            simhash_val = compute_simhash(result.text)

        if file_type_group == "image":
            phash_val = compute_phash(path)
    except Exception as exc:
        repo_jobs.log_error(job_id, full_path, "hash", "HASH_ERROR", str(exc))

    # ── Single transaction: upsert + content + metadata + fts + status ───
    try:
        with get_db() as con:
            # 1. upsert item
            item_id = repo_items.upsert_item_tx(con, item_data)

            # 2. content + metadata
            if result:
                if result.metadata:
                    _upsert_metadata_tx(con, item_id, result.metadata)

                    # Update best_time if we have a better source
                    if result.metadata.get("taken_ts"):
                        updated = time_utils.inject_metadata_time(times, result.metadata)
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

                text = result.text or ""
                preview = result.preview or text[:400]
                _upsert_content_tx(con, item_id, text, preview, len(text), result.language)

                # 3. FTS index inside same transaction
                meta_title = (result.metadata or {}).get("title", "")
                _fts_index_item_tx(con, item_id, path.name, full_path, text, meta_title)

            # 4. hashes + final status
            con.execute(
                """
                UPDATE items
                SET sha256=COALESCE(?,sha256),
                    simhash64=COALESCE(?,simhash64),
                    phash=COALESCE(?,phash),
                    indexing_status='done',
                    content_status=CASE WHEN ? IS NOT NULL THEN 'done' ELSE content_status END,
                    metadata_status=CASE WHEN ? IS NOT NULL THEN 'done' ELSE metadata_status END
                WHERE item_id=?
                """,
                (sha, simhash_val, phash_val,
                 result.text if result else None,
                 result.metadata if result else None,
                 item_id),
            )

            con.commit()

    except Exception as exc:
        repo_jobs.log_error(job_id, full_path, "db_write", "DB_ERROR", str(exc))
        repo_jobs.bump_job_counts(job_id, pending_delta=-1, error_delta=1, current_file=full_path)
        _try_finish_job(job_id)
        return

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
        # Run PRAGMA optimize + incremental_vacuum after full job
        try:
            from ..db.connection import optimize_db
            optimize_db()
        except Exception:
            pass
    except Exception as exc:
        repo_jobs.update_job(
            job_id,
            status="error",
            note=str(exc),
            current_file="",
            finished_ts=int(time.time()),
        )
