"""
NotingHill — db/repo_items.py
CRUD operations for the items table.
"""
from __future__ import annotations

import json
from typing import Optional

from .connection import get_db


def _parse_meta_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def upsert_item(data: dict) -> int:
    """Insert-or-update a single item. Returns item_id in one round-trip."""
    sql = """
    INSERT INTO items (
        root_id, full_path, parent_path, file_name, extension, mime_type,
        size_bytes, created_ts, modified_ts, accessed_ts,
        best_time_ts, best_time_source, best_time_confidence,
        file_type_group, indexing_status,
        is_deleted, is_hidden, is_system,
        first_seen_ts, last_seen_ts, last_indexed_ts, change_token
    ) VALUES (
        :root_id,:full_path,:parent_path,:file_name,:extension,:mime_type,
        :size_bytes,:created_ts,:modified_ts,:accessed_ts,
        :best_time_ts,:best_time_source,:best_time_confidence,
        :file_type_group,:indexing_status,
        :is_deleted,:is_hidden,:is_system,
        :first_seen_ts,:last_seen_ts,:last_indexed_ts,:change_token
    )
    ON CONFLICT(full_path) DO UPDATE SET
        size_bytes=excluded.size_bytes,
        modified_ts=excluded.modified_ts,
        accessed_ts=excluded.accessed_ts,
        best_time_ts=excluded.best_time_ts,
        best_time_source=excluded.best_time_source,
        indexing_status=excluded.indexing_status,
        last_seen_ts=excluded.last_seen_ts,
        last_indexed_ts=excluded.last_indexed_ts,
        change_token=excluded.change_token,
        is_deleted=0
    RETURNING item_id
    """
    with get_db() as con:
        row = con.execute(sql, data).fetchone()
        # RETURNING gives us the id regardless of INSERT vs UPDATE path
        return row["item_id"]


def upsert_item_tx(con, data: dict) -> int:
    """Same as upsert_item but uses an existing connection (for batched transactions)."""
    sql = """
    INSERT INTO items (
        root_id, full_path, parent_path, file_name, extension, mime_type,
        size_bytes, created_ts, modified_ts, accessed_ts,
        best_time_ts, best_time_source, best_time_confidence,
        file_type_group, indexing_status,
        is_deleted, is_hidden, is_system,
        first_seen_ts, last_seen_ts, last_indexed_ts, change_token
    ) VALUES (
        :root_id,:full_path,:parent_path,:file_name,:extension,:mime_type,
        :size_bytes,:created_ts,:modified_ts,:accessed_ts,
        :best_time_ts,:best_time_source,:best_time_confidence,
        :file_type_group,:indexing_status,
        :is_deleted,:is_hidden,:is_system,
        :first_seen_ts,:last_seen_ts,:last_indexed_ts,:change_token
    )
    ON CONFLICT(full_path) DO UPDATE SET
        size_bytes=excluded.size_bytes,
        modified_ts=excluded.modified_ts,
        accessed_ts=excluded.accessed_ts,
        best_time_ts=excluded.best_time_ts,
        best_time_source=excluded.best_time_source,
        indexing_status=excluded.indexing_status,
        last_seen_ts=excluded.last_seen_ts,
        last_indexed_ts=excluded.last_indexed_ts,
        change_token=excluded.change_token,
        is_deleted=0
    RETURNING item_id
    """
    row = con.execute(sql, data).fetchone()
    return row["item_id"]


def get_item_id_by_path(full_path: str) -> Optional[int]:
    with get_db() as con:
        row = con.execute("SELECT item_id FROM items WHERE full_path=?", (full_path,)).fetchone()
        return row["item_id"] if row else None


def batch_load_change_tokens(root_id: int) -> dict[str, str]:
    """
    Load all (full_path → change_token) for a root in one query.
    Used by incremental scan to avoid N per-file round-trips.
    """
    with get_db() as con:
        rows = con.execute(
            "SELECT full_path, change_token FROM items WHERE root_id=? AND is_deleted=0",
            (root_id,),
        ).fetchall()
    return {row["full_path"]: row["change_token"] for row in rows}


def get_item(item_id: int) -> Optional[dict]:
    with get_db() as con:
        row = con.execute(
            """
            SELECT i.*, ic.extracted_text, ic.content_preview, ic.content_length,
                   im.meta_json, im.width, im.height, im.duration_seconds,
                   im.title, im.artist, im.album, im.camera_model, im.taken_ts
            FROM items i
            LEFT JOIN item_content ic ON ic.item_id=i.item_id
            LEFT JOIN item_metadata im ON im.item_id=i.item_id
            WHERE i.item_id=?
            """,
            (item_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        meta = _parse_meta_json(data.get("meta_json"))
        if meta:
            data["meta"] = meta
            data["gps_lat"] = meta.get("gps_lat")
            data["gps_lon"] = meta.get("gps_lon")
            data["gps_text"] = meta.get("gps_text")
            data["date_time_original"] = meta.get("DateTimeOriginal")
            data["camera_model"] = data.get("camera_model") or meta.get("camera_model") or meta.get("Model")
        return data


def mark_deleted(full_path: str):
    with get_db() as con:
        con.execute("UPDATE items SET is_deleted=1 WHERE full_path=?", (full_path,))
        con.commit()


def update_hashes(item_id: int, sha256: str = None, simhash64: str = None, phash: str = None):
    with get_db() as con:
        con.execute(
            """
            UPDATE items SET sha256=COALESCE(?,sha256),
            simhash64=COALESCE(?,simhash64), phash=COALESCE(?,phash)
            WHERE item_id=?
            """,
            (sha256, simhash64, phash, item_id),
        )
        con.commit()


def update_status(
    item_id: int,
    indexing_status: str = None,
    content_status: str = None,
    metadata_status: str = None,
    error_code: str = None,
    error_message: str = None,
):
    with get_db() as con:
        con.execute(
            """
            UPDATE items SET
                indexing_status=COALESCE(?,indexing_status),
                content_status=COALESCE(?,content_status),
                metadata_status=COALESCE(?,metadata_status),
                error_code=COALESCE(?,error_code),
                error_message=COALESCE(?,error_message)
            WHERE item_id=?
            """,
            (indexing_status, content_status, metadata_status, error_code, error_message, item_id),
        )
        con.commit()


def get_stats() -> dict:
    with get_db() as con:
        total = con.execute("SELECT COUNT(*) as c, SUM(size_bytes) as s FROM items WHERE is_deleted=0").fetchone()
        by_type = con.execute(
            """
            SELECT file_type_group, COUNT(*) as cnt, SUM(size_bytes) as sz
            FROM items WHERE is_deleted=0
            GROUP BY file_type_group
            """
        ).fetchall()
        errors = con.execute("SELECT COUNT(*) as c FROM items WHERE error_code IS NOT NULL AND is_deleted=0").fetchone()
        return {
            "total_files": total["c"],
            "total_size": total["s"] or 0,
            "by_type": [dict(r) for r in by_type],
            "errors": errors["c"],
        }


def list_items(
    root_id: int = None,
    file_type_group: str = None,
    extension: str = None,
    min_size: int = None,
    max_size: int = None,
    since_ts: int = None,
    until_ts: int = None,
    is_deleted: int = 0,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "modified_ts DESC",
) -> list[dict]:
    clauses = ["i.is_deleted=?"]
    params: list = [is_deleted]

    if root_id:
        clauses.append("i.root_id=?")
        params.append(root_id)
    if file_type_group:
        clauses.append("i.file_type_group=?")
        params.append(file_type_group)
    if extension:
        clauses.append("i.extension=?")
        params.append(extension)
    if min_size is not None:
        clauses.append("i.size_bytes>=?")
        params.append(min_size)
    if max_size is not None:
        clauses.append("i.size_bytes<=?")
        params.append(max_size)
    if since_ts:
        clauses.append("i.best_time_ts>=?")
        params.append(since_ts)
    if until_ts:
        clauses.append("i.best_time_ts<=?")
        params.append(until_ts)

    where = " AND ".join(clauses)
    allowed_orders = {
        "modified_ts DESC", "modified_ts ASC", "size_bytes DESC",
        "size_bytes ASC", "file_name ASC", "best_time_ts DESC",
    }
    if order_by not in allowed_orders:
        order_by = "modified_ts DESC"

    sql = f"""
        SELECT i.item_id, i.file_name, i.full_path, i.extension, i.file_type_group,
               i.size_bytes, i.modified_ts, i.best_time_ts, i.sha256,
               ic.content_preview
        FROM items i
        LEFT JOIN item_content ic ON ic.item_id=i.item_id
        WHERE {where}
        ORDER BY i.{order_by}
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    with get_db() as con:
        rows = con.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_recent_items(limit: int = 20) -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            """
            SELECT item_id, file_name, full_path, extension,
                   file_type_group, size_bytes, last_indexed_ts
            FROM items WHERE is_deleted=0
            ORDER BY last_indexed_ts DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_images(
    q: str = "",
    root_id: int = None,
    min_size: int = None,
    max_size: int = None,
    since_ts: int = None,
    until_ts: int = None,
    has_gps: int | None = None,
    order_by: str = "best_time_ts DESC",
    limit: int = 120,
    offset: int = 0,
) -> list[dict]:
    clauses = ["i.is_deleted=0", "i.file_type_group='image'"]
    params: list = []

    if q:
        like = f"%{q}%"
        clauses.append(
            "(i.file_name LIKE ? OR i.full_path LIKE ? OR COALESCE(im.title,'') LIKE ?"
            " OR COALESCE(im.camera_model,'') LIKE ?)"
        )
        params.extend([like, like, like, like])
    if root_id:
        clauses.append("i.root_id=?")
        params.append(root_id)
    if min_size is not None:
        clauses.append("i.size_bytes>=?")
        params.append(min_size)
    if max_size is not None:
        clauses.append("i.size_bytes<=?")
        params.append(max_size)
    if since_ts:
        clauses.append("COALESCE(im.taken_ts, i.best_time_ts, i.modified_ts) >= ?")
        params.append(since_ts)
    if until_ts:
        clauses.append("COALESCE(im.taken_ts, i.best_time_ts, i.modified_ts) <= ?")
        params.append(until_ts)
    # Use indexed has_gps column instead of LIKE on JSON blob
    if has_gps == 1:
        clauses.append("im.has_gps=1")

    allowed_orders = {
        "best_time_ts DESC": "COALESCE(im.taken_ts, i.best_time_ts, i.modified_ts) DESC, i.item_id DESC",
        "best_time_ts ASC":  "COALESCE(im.taken_ts, i.best_time_ts, i.modified_ts) ASC, i.item_id ASC",
        "modified_ts DESC":  "i.modified_ts DESC, i.item_id DESC",
        "modified_ts ASC":   "i.modified_ts ASC, i.item_id ASC",
        "size_bytes DESC":   "i.size_bytes DESC, i.item_id DESC",
        "size_bytes ASC":    "i.size_bytes ASC, i.item_id ASC",
        "file_name ASC":     "i.file_name ASC, i.item_id ASC",
        "file_name DESC":    "i.file_name DESC, i.item_id DESC",
    }
    order_sql = allowed_orders.get(order_by, allowed_orders["best_time_ts DESC"])

    where = " AND ".join(clauses)
    sql = f"""
        SELECT i.item_id, i.root_id, i.file_name, i.full_path, i.parent_path, i.extension,
               i.file_type_group, i.size_bytes, i.created_ts, i.modified_ts, i.best_time_ts,
               i.sha256, i.phash,
               im.width, im.height, im.camera_model, im.taken_ts, im.meta_json, im.has_gps,
               COALESCE(im.taken_ts, i.best_time_ts, i.modified_ts) AS sort_time_ts
        FROM items i
        LEFT JOIN item_metadata im ON im.item_id = i.item_id
        WHERE {where}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]

    with get_db() as con:
        rows = con.execute(sql, params).fetchall()

    results: list[dict] = []
    for row in rows:
        data = dict(row)
        meta = _parse_meta_json(data.get("meta_json"))
        data["gps_lat"] = meta.get("gps_lat")
        data["gps_lon"] = meta.get("gps_lon")
        data["gps_text"] = meta.get("gps_text")
        data["meta"] = meta
        results.append(data)
    return results
