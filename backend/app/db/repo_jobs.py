"""
NotingHill — db/repo_jobs.py
Persistent job state for indexing and resume.
"""
from __future__ import annotations

import time
from typing import Optional

from .connection import get_db


_PROGRESS_FIELDS = {
    "status",
    "scanned_count",
    "queued_count",
    "indexed_count",
    "skipped_count",
    "error_count",
    "pending_count",
    "scan_complete",
    "current_file",
    "finished_ts",
    "updated_ts",
    "note",
}


def create_job(root_id: int, job_type: str) -> int:
    now = int(time.time())
    with get_db() as con:
        cur = con.execute(
            """
            INSERT INTO index_jobs(
                root_id, job_type, status, started_ts, updated_ts,
                scanned_count, queued_count, indexed_count, skipped_count,
                error_count, pending_count, scan_complete, current_file
            )
            VALUES(?, ?, 'running', ?, ?, 0, 0, 0, 0, 0, 0, 0, '')
            """,
            (root_id, job_type, now, now),
        )
        con.commit()
        return cur.lastrowid



def update_job(job_id: int, **kwargs) -> None:
    payload = {k: v for k, v in kwargs.items() if k in _PROGRESS_FIELDS}
    if not payload:
        return

    payload.setdefault("updated_ts", int(time.time()))
    sets = ", ".join(f"{k}=?" for k in payload)
    values = list(payload.values())

    with get_db() as con:
        con.execute(f"UPDATE index_jobs SET {sets} WHERE job_id=?", values + [job_id])
        con.commit()



def bump_job_counts(
    job_id: int,
    *,
    indexed_delta: int = 0,
    skipped_delta: int = 0,
    error_delta: int = 0,
    pending_delta: int = 0,
    current_file: Optional[str] = None,
) -> None:
    now = int(time.time())
    with get_db() as con:
        con.execute(
            """
            UPDATE index_jobs
            SET indexed_count = indexed_count + ?,
                skipped_count = skipped_count + ?,
                error_count = error_count + ?,
                pending_count = CASE
                    WHEN pending_count + ? < 0 THEN 0
                    ELSE pending_count + ?
                END,
                current_file = COALESCE(?, current_file),
                updated_ts = ?
            WHERE job_id = ?
            """,
            (
                indexed_delta,
                skipped_delta,
                error_delta,
                pending_delta,
                pending_delta,
                current_file,
                now,
                job_id,
            ),
        )
        con.commit()



def log_error(job_id: int, full_path: str, stage: str, error_code: str, message: str) -> None:
    now = int(time.time())
    with get_db() as con:
        con.execute(
            """
            INSERT INTO index_job_errors(job_id, full_path, stage, error_code, error_message, created_ts)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (job_id, full_path, stage, error_code, message, now),
        )
        con.execute(
            "UPDATE index_jobs SET error_count = error_count + 1, updated_ts = ? WHERE job_id = ?",
            (now, job_id),
        )
        con.commit()



def get_job(job_id: int) -> Optional[dict]:
    with get_db() as con:
        row = con.execute(
            """
            SELECT j.*, r.root_path, r.root_label, r.is_enabled
            FROM index_jobs j
            LEFT JOIN roots r ON r.root_id = j.root_id
            WHERE j.job_id = ?
            """,
            (job_id,),
        ).fetchone()
        return dict(row) if row else None



def get_active_jobs() -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            """
            SELECT j.*, r.root_path, r.root_label
            FROM index_jobs j
            LEFT JOIN roots r ON r.root_id = j.root_id
            WHERE j.status IN ('running', 'pending', 'finalizing')
            ORDER BY j.started_ts DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]



def get_recent_jobs(limit: int = 20) -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            """
            SELECT j.*, r.root_path, r.root_label
            FROM index_jobs j
            LEFT JOIN roots r ON r.root_id = j.root_id
            ORDER BY j.job_id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]



def get_job_errors(job_id: int, limit: int = 100) -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            """
            SELECT *
            FROM index_job_errors
            WHERE job_id = ?
            ORDER BY created_ts DESC
            LIMIT ?
            """,
            (job_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]



def list_resumable_jobs() -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            """
            SELECT j.*, r.root_path, r.root_label, r.is_enabled
            FROM index_jobs j
            LEFT JOIN roots r ON r.root_id = j.root_id
            WHERE j.status IN ('running', 'pending', 'finalizing')
            ORDER BY j.job_id ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]



def prepare_resume(job_id: int) -> None:
    now = int(time.time())
    with get_db() as con:
        con.execute(
            """
            UPDATE index_jobs
            SET status = 'running',
                finished_ts = NULL,
                pending_count = 0,
                scan_complete = 0,
                queued_count = indexed_count,
                current_file = '',
                updated_ts = ?,
                note = COALESCE(note, '')
            WHERE job_id = ?
            """,
            (now, job_id),
        )
        con.commit()



def try_mark_finalizing(job_id: int) -> bool:
    now = int(time.time())
    with get_db() as con:
        cur = con.execute(
            """
            UPDATE index_jobs
            SET status = 'finalizing', updated_ts = ?
            WHERE job_id = ?
              AND status = 'running'
              AND scan_complete = 1
              AND pending_count = 0
            """,
            (now, job_id),
        )
        con.commit()
        return cur.rowcount > 0



def build_progress(job: dict | None) -> dict:
    if not job:
        return {}
    return {
        "status": job.get("status") or "pending",
        "scanned": job.get("scanned_count", 0) or 0,
        "queued": job.get("queued_count", 0) or 0,
        "indexed": job.get("indexed_count", 0) or 0,
        "skipped": job.get("skipped_count", 0) or 0,
        "errors": job.get("error_count", 0) or 0,
        "pending": job.get("pending_count", 0) or 0,
        "scan_complete": job.get("scan_complete", 0) or 0,
        "current_file": job.get("current_file") or "",
        "updated_ts": job.get("updated_ts") or 0,
    }


# ── roots ──────────────────────────────────────────────────────────────────

def add_root(root_path: str, label: str | None = None) -> int:
    now = int(time.time())
    with get_db() as con:
        cur = con.execute(
            """
            INSERT OR IGNORE INTO roots(root_path, root_label, is_enabled, created_ts, updated_ts)
            VALUES(?, ?, 1, ?, ?)
            """,
            (root_path, label or root_path, now, now),
        )
        con.commit()
        if cur.lastrowid:
            return cur.lastrowid
        row = con.execute("SELECT root_id FROM roots WHERE root_path = ?", (root_path,)).fetchone()
        return row["root_id"]



def list_roots() -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            """
            SELECT r.*, COUNT(i.item_id) AS file_count
            FROM roots r
            LEFT JOIN items i ON i.root_id = r.root_id AND i.is_deleted = 0
            GROUP BY r.root_id
            ORDER BY r.created_ts DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]



def toggle_root(root_id: int, enabled: bool) -> None:
    with get_db() as con:
        con.execute(
            "UPDATE roots SET is_enabled = ?, updated_ts = ? WHERE root_id = ?",
            (1 if enabled else 0, int(time.time()), root_id),
        )
        con.commit()



def delete_root(root_id: int) -> None:
    with get_db() as con:
        con.execute("UPDATE items SET is_deleted = 1 WHERE root_id = ?", (root_id,))
        con.execute("DELETE FROM roots WHERE root_id = ?", (root_id,))
        con.commit()


# ── settings ───────────────────────────────────────────────────────────────

def get_setting(key: str) -> Optional[str]:
    with get_db() as con:
        row = con.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key = ?",
            (key,),
        ).fetchone()
        return row["setting_value"] if row else None



def set_setting(key: str, value: str) -> None:
    now = int(time.time())
    with get_db() as con:
        con.execute(
            """
            INSERT INTO app_settings(setting_key, setting_value, updated_ts)
            VALUES(?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_ts = excluded.updated_ts
            """,
            (key, value, now),
        )
        con.commit()



def get_all_settings() -> dict:
    with get_db() as con:
        rows = con.execute("SELECT setting_key, setting_value FROM app_settings").fetchall()
        return {r["setting_key"]: r["setting_value"] for r in rows}
