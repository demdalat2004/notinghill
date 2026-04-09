"""
NotingHill — db/repo_duplicates.py
"""
import time
from .connection import get_db


def get_exact_duplicate_groups(limit=50, offset=0) -> list[dict]:
    with get_db() as con:
        groups = con.execute("""
            SELECT dg.group_id, dg.group_key, dg.item_count, dg.total_size_bytes, dg.updated_ts
            FROM duplicate_groups dg
            WHERE dg.group_type='exact' AND dg.item_count>1
            ORDER BY dg.total_size_bytes DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
        result = []
        for g in groups:
            items = con.execute("""
                SELECT i.item_id, i.file_name, i.full_path, i.size_bytes,
                       i.modified_ts, dgi.is_primary_candidate, dgi.review_status
                FROM duplicate_group_items dgi
                JOIN items i ON i.item_id=dgi.item_id
                WHERE dgi.group_id=?
            """, (g["group_id"],)).fetchall()
            d = dict(g)
            d["items"] = [dict(r) for r in items]
            result.append(d)
        return result


def get_similar_groups(group_type: str, limit=50, offset=0) -> list[dict]:
    with get_db() as con:
        groups = con.execute("""
            SELECT dg.group_id, dg.group_type, dg.item_count, dg.total_size_bytes, dg.updated_ts
            FROM duplicate_groups dg
            WHERE dg.group_type=? AND dg.item_count>1
            ORDER BY dg.item_count DESC
            LIMIT ? OFFSET ?
        """, (group_type, limit, offset)).fetchall()
        result = []
        for g in groups:
            items = con.execute("""
                SELECT i.item_id, i.file_name, i.full_path, i.size_bytes,
                       dgi.similarity_score, dgi.is_primary_candidate, dgi.review_status,
                       im.width, im.height
                FROM duplicate_group_items dgi
                JOIN items i ON i.item_id=dgi.item_id
                LEFT JOIN item_metadata im ON im.item_id=i.item_id
                WHERE dgi.group_id=?
                ORDER BY dgi.similarity_score DESC
            """, (g["group_id"],)).fetchall()
            d = dict(g)
            d["items"] = [dict(r) for r in items]
            result.append(d)
        return result


def upsert_duplicate_group(group_type: str, group_key: str, item_ids: list[int],
                           scores: dict[int, float] = None) -> int:
    now = int(time.time())
    with get_db() as con:
        existing = con.execute(
            "SELECT group_id FROM duplicate_groups WHERE group_type=? AND group_key=?",
            (group_type, group_key)
        ).fetchone()

        if existing:
            gid = existing["group_id"]
            con.execute("DELETE FROM duplicate_group_items WHERE group_id=?", (gid,))
        else:
            cur = con.execute("""
                INSERT INTO duplicate_groups(group_type,group_key,item_count,total_size_bytes,created_ts,updated_ts)
                VALUES(?,?,0,0,?,?)
            """, (group_type, group_key, now, now))
            gid = cur.lastrowid

        # Batch size lookup — one query instead of N
        if item_ids:
            placeholders = ",".join("?" * len(item_ids))
            size_rows = con.execute(
                f"SELECT item_id, COALESCE(size_bytes,0) AS sz FROM items WHERE item_id IN ({placeholders})",
                item_ids,
            ).fetchall()
            size_map = {r["item_id"]: r["sz"] for r in size_rows}
        else:
            size_map = {}

        total_size = sum(size_map.get(iid, 0) for iid in item_ids)

        con.executemany(
            "INSERT INTO duplicate_group_items(group_id,item_id,similarity_score) VALUES(?,?,?)",
            [(gid, iid, (scores or {}).get(iid, 1.0)) for iid in item_ids],
        )

        con.execute("""
            UPDATE duplicate_groups SET item_count=?,total_size_bytes=?,updated_ts=?
            WHERE group_id=?
        """, (len(item_ids), total_size, now, gid))
        con.commit()
        return gid


def update_review_status(group_item_id: int, status: str):
    with get_db() as con:
        con.execute("UPDATE duplicate_group_items SET review_status=? WHERE group_item_id=?",
                    (status, group_item_id))
        con.commit()


def get_dup_stats() -> dict:
    with get_db() as con:
        row = con.execute("""
            SELECT COUNT(DISTINCT group_id) as groups,
                   SUM(total_size_bytes) as wasted
            FROM duplicate_groups WHERE item_count>1
        """).fetchone()
        return {"groups": row["groups"] or 0, "wasted_bytes": row["wasted"] or 0}
