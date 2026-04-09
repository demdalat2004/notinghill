"""
NotingHill — db/connection.py
SQLite connection manager — optimized for 500K+ files on Windows.

Changes vs original:
  • page_size=8192 (better for large text/blob rows)
  • cache_size=-131072 (128 MB — doubled)
  • mmap_size=536870912 (512 MB)
  • wal_autocheckpoint=2000 (fewer checkpoint stalls under heavy write load)
  • busy_timeout=5000 ms (prevents "database is locked" on multi-thread access)
  • New composite + partial indexes for 500K-row queries
  • optimize_db() helper — runs PRAGMA optimize + incremental_vacuum
"""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

_local = threading.local()
DB_PATH: Path | None = None


_INDEX_JOB_MIGRATIONS = [
    ("pending_count",  "ALTER TABLE index_jobs ADD COLUMN pending_count INTEGER NOT NULL DEFAULT 0"),
    ("scan_complete",  "ALTER TABLE index_jobs ADD COLUMN scan_complete INTEGER NOT NULL DEFAULT 0"),
    ("current_file",   "ALTER TABLE index_jobs ADD COLUMN current_file TEXT"),
    ("updated_ts",     "ALTER TABLE index_jobs ADD COLUMN updated_ts INTEGER"),
]

_COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    ("duplicate_groups", "group_key",
     "ALTER TABLE duplicate_groups ADD COLUMN group_key TEXT"),
    ("item_metadata", "has_gps",
     "ALTER TABLE item_metadata ADD COLUMN has_gps INTEGER NOT NULL DEFAULT 0"),
]

_INDEX_MIGRATIONS: list[tuple[str, str]] = [
    ("idx_item_metadata_has_gps",
     "CREATE INDEX IF NOT EXISTS idx_item_metadata_has_gps ON item_metadata(has_gps)"),
    ("idx_item_metadata_taken_ts",
     "CREATE INDEX IF NOT EXISTS idx_item_metadata_taken_ts ON item_metadata(taken_ts)"),
    ("idx_dup_groups_key",
     "CREATE INDEX IF NOT EXISTS idx_dup_groups_key ON duplicate_groups(group_type, group_key)"),
    ("idx_items_content_status",
     "CREATE INDEX IF NOT EXISTS idx_items_content_status ON items(content_status)"),
    ("idx_items_indexing_status",
     "CREATE INDEX IF NOT EXISTS idx_items_indexing_status ON items(indexing_status)"),
    # Composite indexes — critical for 500K-row queries
    ("idx_items_root_deleted",
     "CREATE INDEX IF NOT EXISTS idx_items_root_deleted ON items(root_id, is_deleted)"),
    ("idx_items_type_deleted",
     "CREATE INDEX IF NOT EXISTS idx_items_type_deleted ON items(file_type_group, is_deleted)"),
    ("idx_items_deleted_modified",
     "CREATE INDEX IF NOT EXISTS idx_items_deleted_modified ON items(is_deleted, modified_ts DESC)"),
    # Partial/covering indexes for dedup hash loads
    ("idx_items_simhash_cover",
     "CREATE INDEX IF NOT EXISTS idx_items_simhash_cover ON items(is_deleted, simhash64) WHERE simhash64 IS NOT NULL"),
    ("idx_items_phash_cover",
     "CREATE INDEX IF NOT EXISTS idx_items_phash_cover ON items(is_deleted, file_type_group, phash) WHERE phash IS NOT NULL"),
    ("idx_items_sha256_cover",
     "CREATE INDEX IF NOT EXISTS idx_items_sha256_cover ON items(is_deleted, sha256) WHERE sha256 IS NOT NULL"),
]


def init_db(db_path: Path) -> None:
    global DB_PATH
    DB_PATH = db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).parent / "schema.sql"
    with _connect(db_path) as con:
        con.executescript(schema_path.read_text(encoding="utf-8"))
        _apply_migrations(con)
        con.commit()


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(path), check_same_thread=False, timeout=30.0)
    con.row_factory = sqlite3.Row

    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA page_size=8192")
    con.execute("PRAGMA cache_size=-131072")       # 128 MB page cache
    con.execute("PRAGMA mmap_size=536870912")      # 512 MB memory-mapped I/O
    con.execute("PRAGMA temp_store=MEMORY")
    con.execute("PRAGMA wal_autocheckpoint=2000")  # fewer checkpoint stalls
    con.execute("PRAGMA busy_timeout=5000")        # 5s retry on lock

    return con


def _column_exists(con: sqlite3.Connection, table: str, column: str) -> bool:
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _index_exists(con: sqlite3.Connection, index_name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,),
    ).fetchone()
    return row is not None


def _apply_migrations(con: sqlite3.Connection) -> None:
    for column_name, sql in _INDEX_JOB_MIGRATIONS:
        if not _column_exists(con, "index_jobs", column_name):
            con.execute(sql)
    for table, column, sql in _COLUMN_MIGRATIONS:
        if not _column_exists(con, table, column):
            con.execute(sql)
    for index_name, sql in _INDEX_MIGRATIONS:
        if not _index_exists(con, index_name):
            con.execute(sql)


@contextmanager
def get_db():
    """Thread-local connection context manager."""
    if not hasattr(_local, "con") or _local.con is None:
        _local.con = _connect(DB_PATH)
    try:
        yield _local.con
    except Exception:
        _local.con.rollback()
        raise


def close_thread_db() -> None:
    if hasattr(_local, "con") and _local.con:
        _local.con.close()
        _local.con = None


def optimize_db() -> None:
    """
    Run PRAGMA optimize + incremental_vacuum.
    Call after a full index job completes.
    """
    with get_db() as con:
        con.execute("PRAGMA optimize")
        con.execute("PRAGMA incremental_vacuum(1000)")
        con.commit()
