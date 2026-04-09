"""
NotingHill — db/repo_content.py
"""
import json
import time

from .connection import get_db


def upsert_content(item_id: int, extracted_text: str, preview: str, length: int, language: str = None):
    with get_db() as con:
        _upsert_content_tx(con, item_id, extracted_text, preview, length, language)
        con.commit()


def upsert_metadata(item_id: int, meta: dict):
    with get_db() as con:
        _upsert_metadata_tx(con, item_id, meta)
        con.commit()


# ── transaction-aware variants (no commit — caller owns the transaction) ──

def _upsert_content_tx(con, item_id: int, extracted_text: str, preview: str, length: int, language: str = None):
    con.execute(
        """
        INSERT INTO item_content(item_id,extracted_text,content_preview,content_length,content_language,extracted_ts)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(item_id) DO UPDATE SET
            extracted_text=excluded.extracted_text,
            content_preview=excluded.content_preview,
            content_length=excluded.content_length,
            extracted_ts=excluded.extracted_ts
        """,
        (item_id, extracted_text, preview, length, language, int(time.time())),
    )


def _upsert_metadata_tx(con, item_id: int, meta: dict):
    has_gps = 1 if (meta.get("gps_lat") and meta.get("gps_lon")) else 0
    con.execute(
        """
        INSERT INTO item_metadata(item_id,meta_json,width,height,duration_seconds,
                                  title,artist,album,camera_model,taken_ts,has_gps)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(item_id) DO UPDATE SET
            meta_json=excluded.meta_json,
            width=excluded.width,
            height=excluded.height,
            duration_seconds=excluded.duration_seconds,
            title=excluded.title,
            artist=excluded.artist,
            album=excluded.album,
            camera_model=excluded.camera_model,
            taken_ts=excluded.taken_ts,
            has_gps=excluded.has_gps
        """,
        (
            item_id,
            json.dumps(meta, ensure_ascii=False),
            meta.get("width"),
            meta.get("height"),
            meta.get("duration_seconds"),
            meta.get("title"),
            meta.get("artist"),
            meta.get("album"),
            meta.get("camera_model") or meta.get("Model"),
            meta.get("taken_ts"),
            has_gps,
        ),
    )
