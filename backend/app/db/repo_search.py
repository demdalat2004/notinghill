"""
NotingHill — db/repo_search.py
FTS5-powered full-text search + filter search.
"""
from __future__ import annotations

from .connection import get_db

FTS_TABLE = "fts_items"


def fts_index_item(item_id: int, file_name: str, full_path: str,
                   extracted_text: str = "", title: str = ""):
    """Index a single item — standalone (commits internally)."""
    with get_db() as con:
        _fts_index_item_tx(con, item_id, file_name, full_path, extracted_text, title)
        con.commit()


def _fts_index_item_tx(con, item_id: int, file_name: str, full_path: str,
                       extracted_text: str = "", title: str = ""):
    """Index a single item inside an existing transaction (no commit)."""
    con.execute(f"DELETE FROM {FTS_TABLE} WHERE rowid=? OR item_id=?", (item_id, item_id))
    con.execute(
        f"""
        INSERT INTO {FTS_TABLE}(rowid, item_id, file_name, full_path, extracted_text, meta_title)
        VALUES(?,?,?,?,?,?)
        """,
        (item_id, item_id, file_name, full_path, extracted_text or "", title or ""),
    )


def fts_search(query: str, file_type_group: str = None, extension: str = None,
               root_id: int = None, min_size: int = None, max_size: int = None,
               since_ts: int = None, until_ts: int = None,
               order_by: str = "rank", limit: int = 50, offset: int = 0) -> list[dict]:
    if not query.strip():
        return []

    safe_query = query.replace('"', '""')
    clauses = ["i.is_deleted=0"]
    params: list = []

    if file_type_group:
        clauses.append("i.file_type_group=?")
        params.append(file_type_group)
    if extension:
        clauses.append("i.extension=?")
        params.append(extension)
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
        clauses.append("i.best_time_ts>=?")
        params.append(since_ts)
    if until_ts:
        clauses.append("i.best_time_ts<=?")
        params.append(until_ts)

    where_extra = (" AND " + " AND ".join(clauses)) if clauses else ""
    # Try phrase match first, then fallback to prefix/OR match
    for fts_query in (f'"{safe_query}"', safe_query):
        sql = f"""
            SELECT i.item_id, i.file_name, i.full_path, i.extension, i.file_type_group,
                   i.size_bytes, i.modified_ts, i.best_time_ts,
                   ic.content_preview,
                   snippet({FTS_TABLE}, 3, '<em>', '</em>', '...', 20) AS snippet,
                   bm25({FTS_TABLE}) AS rank
            FROM {FTS_TABLE}
            JOIN items i ON i.item_id={FTS_TABLE}.rowid
            LEFT JOIN item_content ic ON ic.item_id=i.item_id
            WHERE {FTS_TABLE} MATCH ? {where_extra}
            ORDER BY rank
            LIMIT ? OFFSET ?
        """
        params_final = [fts_query] + params + [limit, offset]
        with get_db() as con:
            try:
                rows = con.execute(sql, params_final).fetchall()
                if rows:
                    return [dict(r) for r in rows]
            except Exception:
                pass

    # Last resort: LIKE search (no FTS)
    return _like_search(query, file_type_group, extension, root_id,
                        min_size, max_size, since_ts, until_ts, limit, offset)


def _like_search(query, file_type_group, extension, root_id,
                 min_size, max_size, since_ts, until_ts, limit, offset):
    clauses = ["i.is_deleted=0", "(i.file_name LIKE ? OR ic.extracted_text LIKE ? OR i.full_path LIKE ?)"]
    params = [f"%{query}%", f"%{query}%", f"%{query}%"]
    if file_type_group:
        clauses.append("i.file_type_group=?")
        params.append(file_type_group)
    if extension:
        clauses.append("i.extension=?")
        params.append(extension)
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
        clauses.append("i.best_time_ts>=?")
        params.append(since_ts)
    if until_ts:
        clauses.append("i.best_time_ts<=?")
        params.append(until_ts)
    where = " AND ".join(clauses)
    sql = f"""
        SELECT i.item_id, i.file_name, i.full_path, i.extension, i.file_type_group,
               i.size_bytes, i.modified_ts, i.best_time_ts, ic.content_preview,
               ic.content_preview AS snippet, 0 AS rank
        FROM items i LEFT JOIN item_content ic ON ic.item_id=i.item_id
        WHERE {where}
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    with get_db() as con:
        rows = con.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
