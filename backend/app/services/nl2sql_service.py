"""
NotingHill — services/nl2sql_service.py
========================================
Natural-language → SQL pipeline.

Flow:
  1. Build system prompt with full schema + column semantics + example Q→SQL pairs
  2. Send user question to LLM → get back a SELECT statement
  3. Validate SQL (read-only, whitelist tables, no dangerous keywords)
  4. Execute against SQLite → get rows
  5. Send rows back to LLM for natural-language answer
  6. Return { answer, sql, rows, row_count, ... }

Design decisions:
  • Two-turn LLM call: first generates SQL, second narrates results.
    Keeps SQL clean and answer readable — single-turn "give SQL + answer"
    produces worse SQL and worse prose simultaneously.
  • SQL validator is strict: SELECT only, whitelisted tables, banned keywords.
    If LLM generates invalid SQL → return error with the raw SQL for debugging.
  • Max 200 rows returned to LLM for narration (context window safety).
  • All timestamps in DB are Unix epoch (INTEGER). The prompt explains this
    and provides strftime() helpers so LLM knows how to filter by date.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from ..db.connection import get_db


# ══════════════════════════════════════════════════════════════════════════
# SCHEMA PRE-PROMPT
# Describes every queryable table, column semantics, and value enumerations.
# ══════════════════════════════════════════════════════════════════════════

_CURRENT_TS_PLACEHOLDER = "__CURRENT_TS__"   # replaced at call time

SCHEMA_PROMPT = """
You are a SQLite query assistant for NotingHill, a local file indexing app.
Convert the user's natural-language question into a single valid SQLite SELECT statement.

════════════════════════════════════════════
DATABASE SCHEMA
════════════════════════════════════════════

-- Indexed source folders
CREATE TABLE roots (
  root_id    INTEGER PRIMARY KEY,
  root_path  TEXT,       -- absolute path on disk, e.g. "C:/Users/phong/Documents"
  root_label TEXT,       -- human-readable label set by user
  is_enabled INTEGER     -- 1 = active, 0 = disabled
);

-- One row per indexed file
CREATE TABLE items (
  item_id             INTEGER PRIMARY KEY,
  root_id             INTEGER,          -- FK → roots.root_id
  full_path           TEXT,             -- absolute file path
  parent_path         TEXT,             -- parent directory
  file_name           TEXT,             -- filename with extension
  extension           TEXT,             -- lowercase, e.g. ".pdf", ".jpg", ".docx"
  mime_type           TEXT,

  size_bytes          INTEGER,          -- file size
  created_ts          INTEGER,          -- Unix epoch (seconds)
  modified_ts         INTEGER,          -- Unix epoch (seconds)
  accessed_ts         INTEGER,          -- Unix epoch (seconds)

  best_time_ts        INTEGER,          -- best-guess timestamp (EXIF > mtime > ctime)
  best_time_source    TEXT,             -- "exif", "mtime", "ctime"

  sha256              TEXT,             -- hex SHA-256 hash
  simhash64           TEXT,             -- 64-bit text similarity hash (hex)
  phash               TEXT,             -- perceptual hash for images (hex)

  -- file_type_group values: "image", "video", "audio", "pdf", "office",
  --   "text", "code", "archive", "font", "other"
  file_type_group     TEXT,

  content_status      TEXT,             -- "done", "pending", "error"
  indexing_status     TEXT,             -- "done", "processing", "error"

  is_deleted          INTEGER,          -- 1 = file removed from disk
  is_hidden           INTEGER,          -- 1 = hidden file/dir
  first_seen_ts       INTEGER,
  last_seen_ts        INTEGER,
  last_indexed_ts     INTEGER,          -- when NotingHill last processed it

  error_code          TEXT,
  error_message       TEXT
);

-- Extracted text content
CREATE TABLE item_content (
  item_id           INTEGER PRIMARY KEY,  -- FK → items.item_id
  extracted_text    TEXT,                 -- full extracted text
  content_preview   TEXT,                 -- first ~400 chars
  content_length    INTEGER,              -- char count of extracted_text
  content_language  TEXT                  -- detected language code, e.g. "en"
);

-- Structured metadata (images, audio, video)
CREATE TABLE item_metadata (
  item_id          INTEGER PRIMARY KEY,   -- FK → items.item_id
  width            INTEGER,               -- image/video width px
  height           INTEGER,               -- image/video height px
  duration_seconds REAL,                  -- audio/video duration
  title            TEXT,                  -- ID3 title / document title
  artist           TEXT,                  -- ID3 artist
  album            TEXT,                  -- ID3 album
  camera_model     TEXT,                  -- EXIF camera model
  taken_ts         INTEGER,               -- EXIF DateTimeOriginal as Unix epoch
  meta_json        TEXT                   -- full metadata as JSON blob
);

-- Duplicate groups
CREATE TABLE duplicate_groups (
  group_id         INTEGER PRIMARY KEY,
  group_type       TEXT,       -- "exact", "similar_text", "similar_image"
  group_key        TEXT,       -- sha256 for exact; cluster key for similar
  item_count       INTEGER,
  total_size_bytes INTEGER
);

CREATE TABLE duplicate_group_items (
  group_item_id        INTEGER PRIMARY KEY,
  group_id             INTEGER,  -- FK → duplicate_groups.group_id
  item_id              INTEGER,  -- FK → items.item_id
  similarity_score     REAL,     -- 0.0–1.0, 1.0 = identical
  is_primary_candidate INTEGER,  -- 1 = suggested file to keep
  review_status        TEXT      -- "pending", "kept", "deleted"
);

-- FTS5 full-text search (use MATCH, not LIKE)
CREATE VIRTUAL TABLE fts_items USING fts5(
  item_id UNINDEXED,
  file_name,
  full_path,
  extracted_text,
  meta_title
);

════════════════════════════════════════════
TIMESTAMP HELPERS
════════════════════════════════════════════
All *_ts columns are Unix epoch integers (seconds since 1970-01-01 UTC).
Current time = {CURRENT_TS} (Unix epoch).

Useful expressions:
  -- Files modified in the last 7 days:
  WHERE modified_ts >= {CURRENT_TS} - 7*86400

  -- Files from this month:
  WHERE strftime('%Y-%m', modified_ts, 'unixepoch') = strftime('%Y-%m', 'now')

  -- Human-readable date from timestamp:
  strftime('%Y-%m-%d', modified_ts, 'unixepoch') AS date_modified

  -- Files larger than 10 MB:
  WHERE size_bytes > 10*1024*1024

  -- Human-readable size:
  ROUND(size_bytes / 1048576.0, 2) AS size_mb

════════════════════════════════════════════
QUERY RULES
════════════════════════════════════════════
1. Always add WHERE is_deleted = 0 unless explicitly asked about deleted files.
2. Limit results: use LIMIT 50 unless the question asks for counts/aggregates.
3. For text search use fts_items MATCH, e.g.:
     SELECT i.* FROM fts_items f JOIN items i ON i.item_id = f.item_id
     WHERE f MATCH 'invoice' AND i.is_deleted = 0
4. JOIN item_content ic ON ic.item_id = i.item_id  (for extracted text)
5. JOIN item_metadata im ON im.item_id = i.item_id  (for EXIF/audio metadata)
6. Never use DELETE, UPDATE, INSERT, DROP, ALTER, ATTACH, PRAGMA.
7. Return only the SQL statement — no explanation, no markdown, no code fences.

════════════════════════════════════════════
EXAMPLE QUESTION → SQL PAIRS
════════════════════════════════════════════

Q: How many files were indexed this week?
SQL:
SELECT COUNT(*) AS file_count
FROM items
WHERE is_deleted = 0
  AND last_indexed_ts >= {CURRENT_TS} - 7*86400;

Q: Show me the 10 largest PDF files.
SQL:
SELECT item_id, file_name, full_path,
       ROUND(size_bytes / 1048576.0, 2) AS size_mb
FROM items
WHERE is_deleted = 0 AND extension = '.pdf'
ORDER BY size_bytes DESC
LIMIT 10;

Q: What images were taken with a Canon camera?
SQL:
SELECT i.item_id, i.file_name, i.full_path,
       im.camera_model, im.taken_ts,
       strftime('%Y-%m-%d', im.taken_ts, 'unixepoch') AS taken_date
FROM items i
JOIN item_metadata im ON im.item_id = i.item_id
WHERE i.is_deleted = 0
  AND i.file_type_group = 'image'
  AND im.camera_model LIKE '%Canon%'
ORDER BY im.taken_ts DESC
LIMIT 50;

Q: Summarize files indexed this week by type.
SQL:
SELECT file_type_group,
       COUNT(*) AS file_count,
       ROUND(SUM(size_bytes) / 1048576.0, 1) AS total_mb
FROM items
WHERE is_deleted = 0
  AND last_indexed_ts >= {CURRENT_TS} - 7*86400
GROUP BY file_type_group
ORDER BY file_count DESC;

Q: Which documents contain the word "invoice"?
SQL:
SELECT i.item_id, i.file_name, i.full_path,
       i.file_type_group, i.size_bytes
FROM fts_items f
JOIN items i ON i.item_id = f.item_id
WHERE f MATCH 'invoice'
  AND i.is_deleted = 0
LIMIT 50;

Q: Find duplicate files wasting the most space.
SQL:
SELECT dg.group_type, dg.item_count,
       ROUND(dg.total_size_bytes / 1048576.0, 2) AS wasted_mb,
       GROUP_CONCAT(i.file_name, ' | ') AS file_names
FROM duplicate_groups dg
JOIN duplicate_group_items dgi ON dgi.group_id = dg.group_id
JOIN items i ON i.item_id = dgi.item_id
WHERE i.is_deleted = 0
GROUP BY dg.group_id
ORDER BY dg.total_size_bytes DESC
LIMIT 20;

Q: What are the most recently modified Excel files?
SQL:
SELECT item_id, file_name, full_path,
       ROUND(size_bytes / 1024.0, 1) AS size_kb,
       strftime('%Y-%m-%d %H:%M', modified_ts, 'unixepoch') AS modified_at
FROM items
WHERE is_deleted = 0 AND extension = '.xlsx'
ORDER BY modified_ts DESC
LIMIT 20;

Q: How much total storage do my MP3 files use?
SQL:
SELECT COUNT(*) AS track_count,
       ROUND(SUM(size_bytes) / 1073741824.0, 3) AS total_gb
FROM items
WHERE is_deleted = 0 AND extension = '.mp3';

Q: Show me photos with GPS data.
SQL:
SELECT i.item_id, i.file_name, i.full_path,
       im.camera_model,
       strftime('%Y-%m-%d', im.taken_ts, 'unixepoch') AS taken_date,
       json_extract(im.meta_json, '$.gps_lat') AS lat,
       json_extract(im.meta_json, '$.gps_lon') AS lon
FROM items i
JOIN item_metadata im ON im.item_id = i.item_id
WHERE i.is_deleted = 0
  AND i.file_type_group = 'image'
  AND im.has_gps = 1
ORDER BY im.taken_ts DESC
LIMIT 50;
Q: images related to Phong
SQL:
SELECT i.item_id, i.file_name, i.full_path,
       i.size_bytes, i.best_time_ts,
       im.width, im.height, im.camera_model,
       strftime('%Y-%m-%d', COALESCE(im.taken_ts, i.best_time_ts, i.modified_ts), 'unixepoch') AS date
FROM items i
LEFT JOIN item_metadata im ON im.item_id = i.item_id
WHERE i.is_deleted = 0
  AND i.file_type_group = 'image'
  AND (
    i.file_name LIKE '%phong%'
    OR i.full_path LIKE '%phong%'
    OR i.full_path LIKE '%Phong%'
  )
ORDER BY COALESCE(im.taken_ts, i.best_time_ts, i.modified_ts) DESC
LIMIT 50;

Q: find files with "bao gia" in the name
SQL:
SELECT item_id, file_name, full_path,
       file_type_group, extension,
       ROUND(size_bytes / 1024.0, 1) AS size_kb,
       strftime('%Y-%m-%d', modified_ts, 'unixepoch') AS modified_at
FROM items
WHERE is_deleted = 0
  AND (
    file_name LIKE '%bao gia%'
    OR file_name LIKE '%bao-gia%'
    OR file_name LIKE '%baogía%'
  )
ORDER BY modified_ts DESC
LIMIT 50;

Q: show me all videos longer than 10 minutes
SQL:
SELECT i.item_id, i.file_name, i.full_path,
       ROUND(im.duration_seconds / 60.0, 1) AS duration_min,
       ROUND(i.size_bytes / 1048576.0, 1) AS size_mb
FROM items i
JOIN item_metadata im ON im.item_id = i.item_id
WHERE i.is_deleted = 0
  AND i.file_type_group IN ('video', 'audio')
  AND im.duration_seconds > 600
ORDER BY im.duration_seconds DESC
LIMIT 50;

Q: what files are in the 2026 folder?
SQL:
SELECT item_id, file_name, full_path, file_type_group, extension,
       ROUND(size_bytes / 1024.0, 1) AS size_kb
FROM items
WHERE is_deleted = 0
  AND full_path LIKE '%/2026/%' OR full_path LIKE '%\\2026\\%'
ORDER BY modified_ts DESC
LIMIT 100;
""".strip()


# ══════════════════════════════════════════════════════════════════════════
# SQL VALIDATOR
# ══════════════════════════════════════════════════════════════════════════

_ALLOWED_TABLES = {
    "items", "roots", "item_content", "item_metadata",
    "duplicate_groups", "duplicate_group_items", "fts_items",
    "index_jobs",
}

_BANNED_KEYWORDS = re.compile(
    r"\b(DELETE|UPDATE|INSERT|DROP|ALTER|ATTACH|DETACH|PRAGMA|"
    r"CREATE|REPLACE|UPSERT|VACUUM|REINDEX|ANALYZE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

_SQL_EXTRACT = re.compile(
    r"```(?:sql)?\s*([\s\S]+?)```|"   # ```sql ... ``` or ``` ... ```
    r"(SELECT[\s\S]+?)(?:;|\Z)",       # bare SELECT ... ;
    re.IGNORECASE,
)


def _extract_sql(raw: str) -> str:
    """Pull SELECT statement out of LLM response (strips markdown fences)."""
    raw = raw.strip()
    # Remove markdown fences
    m = re.search(r"```(?:sql)?\s*([\s\S]+?)```", raw, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Find first SELECT
    m = re.search(r"(SELECT\b[\s\S]+)", raw, re.IGNORECASE)
    if m:
        sql = m.group(1).strip()
        # Strip trailing prose after semicolon
        if ";" in sql:
            sql = sql[:sql.index(";") + 1]
        return sql
    return raw


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Returns (ok, error_message).
    Rejects anything that isn't a read-only SELECT.
    """
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT statements are allowed."
    m = _BANNED_KEYWORDS.search(sql)
    if m:
        return False, f"Forbidden keyword: {m.group(0)}"
    return True, ""


# ══════════════════════════════════════════════════════════════════════════
# EXECUTION
# ══════════════════════════════════════════════════════════════════════════

_MAX_ROWS_TO_LLM = 200
_MAX_ROWS_HARD   = 500


def execute_sql(sql: str) -> tuple[list[dict], str | None]:
    """
    Execute validated SQL. Returns (rows, error).
    rows is capped at _MAX_ROWS_HARD.
    """
    try:
        with get_db() as con:
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            raw  = cur.fetchmany(_MAX_ROWS_HARD)
            rows = [dict(zip(cols, row)) for row in raw]
        return rows, None
    except Exception as exc:
        return [], str(exc)


# ══════════════════════════════════════════════════════════════════════════
# NARRATION PROMPT
# ══════════════════════════════════════════════════════════════════════════

def _build_narration_prompt(question: str, sql: str, rows: list[dict]) -> str:
    rows_preview = rows[:_MAX_ROWS_TO_LLM]
    rows_json = json.dumps(rows_preview, ensure_ascii=False, default=str, indent=2)
    truncated = len(rows) > _MAX_ROWS_TO_LLM

    note = f"\n(Showing {_MAX_ROWS_TO_LLM} of {len(rows)} rows)" if truncated else ""

    return (
        f"The user asked: {question}\n\n"
        f"SQL executed:\n{sql}\n\n"
        f"Results ({len(rows_preview)} rows){note}:\n{rows_json}\n\n"
        "Instructions:\n"
        "- Answer the user's question directly using the data above.\n"
        "- Be concise. Use numbers and file names from the results.\n"
        "- Format lists as bullet points if there are multiple items.\n"
        "- If results are empty, say no matching files were found.\n"
        "- Do not mention SQL or technical details unless asked.\n"
        "- size_bytes → convert to KB/MB/GB for readability.\n"
        "- *_ts values are Unix timestamps → show as human dates.\n"
    )


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def build_schema_prompt(current_ts: int | None = None) -> str:
    """Return the schema system prompt with current timestamp injected."""
    ts = current_ts or int(time.time())
    return SCHEMA_PROMPT.replace("{CURRENT_TS}", str(ts))


def nl2sql_answer(
    question: str,
    llm_chat_fn,           # callable: (settings, messages) -> str
    llm_settings: dict,
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Full pipeline: question → SQL → execute → narrate.

    Returns:
    {
      "answer":    str,          # natural-language answer
      "sql":       str,          # SQL that was executed
      "rows":      list[dict],   # raw query results
      "row_count": int,
      "error":     str | None,   # set if SQL validation/execution failed
      "mode":      "nl2sql",
    }
    """
    now = int(time.time())
    system_prompt = build_schema_prompt(now)

    # ── Turn 1: Generate SQL ──────────────────────────────────────────────
    sql_raw = ""
    sql     = ""
    last_error = ""

    for attempt in range(max_retries):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question},
        ]
        if attempt > 0 and last_error:
            # Give LLM the error so it can self-correct
            messages.append({
                "role": "assistant",
                "content": sql_raw,
            })
            messages.append({
                "role": "user",
                "content": (
                    f"That SQL caused an error: {last_error}\n"
                    "Please fix it and return only the corrected SELECT statement."
                ),
            })

        sql_raw = llm_chat_fn(llm_settings, messages)
        sql = _extract_sql(sql_raw)

        ok, val_err = validate_sql(sql)
        if not ok:
            last_error = val_err
            continue

        rows, exec_err = execute_sql(sql)
        if exec_err:
            last_error = exec_err
            continue

        # Success — break retry loop
        last_error = ""
        break
    else:
        # All retries exhausted
        return {
            "answer":    f"I could not generate a valid SQL query. Last error: {last_error}",
            "sql":       sql,
            "rows":      [],
            "row_count": 0,
            "error":     last_error,
            "mode":      "nl2sql",
        }

    # ── Turn 2: Narrate results ───────────────────────────────────────────
    narration_prompt = _build_narration_prompt(question, sql, rows)
    answer = llm_chat_fn(
        llm_settings,
        [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for NotingHill, a local file manager. "
                    "Answer the user's question clearly and concisely based on the data provided."
                ),
            },
            {"role": "user", "content": narration_prompt},
        ],
    )

    return {
        "answer":    answer,
        "sql":       sql,
        "rows":      rows,
        "row_count": len(rows),
        "error":     None,
        "mode":      "nl2sql",
    }
