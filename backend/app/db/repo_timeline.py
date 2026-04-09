"""
NotingHill — db/repo_timeline.py
"""
from .connection import get_db


def get_timeline_buckets(zoom: str = "month", since_ts: int = None, until_ts: int = None,
                         file_type_group: str = None) -> list[dict]:
    if zoom == "year":
        fmt = "%Y"
    elif zoom == "day":
        fmt = "%Y-%m-%d"
    else:
        fmt = "%Y-%m"

    clauses = ["is_deleted=0", "best_time_ts IS NOT NULL"]
    params = []
    if since_ts:
        clauses.append("best_time_ts>=?"); params.append(since_ts)
    if until_ts:
        clauses.append("best_time_ts<=?"); params.append(until_ts)
    if file_type_group:
        clauses.append("file_type_group=?"); params.append(file_type_group)

    where = " AND ".join(clauses)
    sql = f"""
        SELECT strftime('{fmt}', best_time_ts, 'unixepoch') AS bucket,
               COUNT(*) AS file_count,
               SUM(size_bytes) AS total_size,
               MIN(best_time_ts) AS bucket_start,
               MAX(best_time_ts) AS bucket_end
        FROM items WHERE {where}
        GROUP BY bucket ORDER BY bucket DESC
    """
    with get_db() as con:
        rows = con.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_items_in_bucket(bucket: str, zoom: str = "month",
                        file_type_group: str = None, limit: int = 100) -> list[dict]:
    if zoom == "year":
        fmt = "%Y"
    elif zoom == "day":
        fmt = "%Y-%m-%d"
    else:
        fmt = "%Y-%m"

    clauses = [f"strftime('{fmt}', best_time_ts, 'unixepoch')=?", "is_deleted=0"]
    params = [bucket]
    if file_type_group:
        clauses.append("file_type_group=?"); params.append(file_type_group)

    where = " AND ".join(clauses)
    sql = f"""
        SELECT item_id, file_name, full_path, extension, file_type_group,
               size_bytes, best_time_ts, modified_ts
        FROM items WHERE {where}
        ORDER BY best_time_ts DESC LIMIT ?
    """
    params.append(limit)
    with get_db() as con:
        rows = con.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
