PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;

-- ============================================================
-- 1. roots — indexed source folders
-- ============================================================
CREATE TABLE IF NOT EXISTS roots (
  root_id    INTEGER PRIMARY KEY AUTOINCREMENT,
  root_path  TEXT NOT NULL UNIQUE,
  root_label TEXT,
  is_enabled INTEGER NOT NULL DEFAULT 1,
  created_ts INTEGER NOT NULL,
  updated_ts INTEGER NOT NULL
);

-- ============================================================
-- 2. items — one row per file
-- ============================================================
CREATE TABLE IF NOT EXISTS items (
  item_id             INTEGER PRIMARY KEY AUTOINCREMENT,
  root_id             INTEGER NOT NULL,
  full_path           TEXT NOT NULL UNIQUE,
  parent_path         TEXT,
  file_name           TEXT NOT NULL,
  extension           TEXT,
  mime_type           TEXT,

  size_bytes          INTEGER,
  created_ts          INTEGER,
  modified_ts         INTEGER,
  accessed_ts         INTEGER,

  best_time_ts        INTEGER,
  best_time_source    TEXT,
  best_time_confidence REAL,

  sha256              TEXT,
  simhash64           TEXT,
  phash               TEXT,

  file_type_group     TEXT,
  content_status      TEXT DEFAULT 'pending',
  metadata_status     TEXT DEFAULT 'pending',
  indexing_status     TEXT DEFAULT 'pending',

  is_deleted          INTEGER NOT NULL DEFAULT 0,
  is_hidden           INTEGER NOT NULL DEFAULT 0,
  is_system           INTEGER NOT NULL DEFAULT 0,

  first_seen_ts       INTEGER,
  last_seen_ts        INTEGER,
  last_indexed_ts     INTEGER,

  change_token        TEXT,
  error_code          TEXT,
  error_message       TEXT,

  FOREIGN KEY (root_id) REFERENCES roots(root_id)
);

CREATE INDEX IF NOT EXISTS idx_items_root_id         ON items(root_id);
CREATE INDEX IF NOT EXISTS idx_items_extension       ON items(extension);
CREATE INDEX IF NOT EXISTS idx_items_file_type_group ON items(file_type_group);
CREATE INDEX IF NOT EXISTS idx_items_size_bytes      ON items(size_bytes);
CREATE INDEX IF NOT EXISTS idx_items_modified_ts     ON items(modified_ts);
CREATE INDEX IF NOT EXISTS idx_items_best_time_ts    ON items(best_time_ts);
CREATE INDEX IF NOT EXISTS idx_items_sha256          ON items(sha256);
CREATE INDEX IF NOT EXISTS idx_items_simhash64       ON items(simhash64);
CREATE INDEX IF NOT EXISTS idx_items_phash           ON items(phash);
CREATE INDEX IF NOT EXISTS idx_items_parent_path     ON items(parent_path);
CREATE INDEX IF NOT EXISTS idx_items_is_deleted      ON items(is_deleted);

-- ============================================================
-- 3. item_content — extracted text
-- ============================================================
CREATE TABLE IF NOT EXISTS item_content (
  item_id           INTEGER PRIMARY KEY,
  extracted_text    TEXT,
  content_preview   TEXT,
  content_length    INTEGER,
  content_language  TEXT,
  extracted_ts      INTEGER,
  FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
);

-- ============================================================
-- 4. item_metadata — structured metadata
-- ============================================================
CREATE TABLE IF NOT EXISTS item_metadata (
  item_id           INTEGER PRIMARY KEY,
  meta_json         TEXT,
  width             INTEGER,
  height            INTEGER,
  duration_seconds  REAL,
  title             TEXT,
  artist            TEXT,
  album             TEXT,
  camera_model      TEXT,
  taken_ts          INTEGER,
  FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
);

-- ============================================================
-- 5. search index support
-- ============================================================
CREATE VIRTUAL TABLE IF NOT EXISTS fts_items USING fts5(
  item_id UNINDEXED,
  file_name,
  full_path,
  extracted_text,
  meta_title,
  tokenize = 'unicode61'
);

-- ============================================================
-- 6. duplicate groups
-- ============================================================
CREATE TABLE IF NOT EXISTS duplicate_groups (
  group_id          INTEGER PRIMARY KEY AUTOINCREMENT,
  group_type        TEXT NOT NULL,
  fingerprint       TEXT,
  created_ts        INTEGER NOT NULL,
  item_count        INTEGER NOT NULL DEFAULT 0,
  total_size_bytes  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS duplicate_group_items (
  group_item_id         INTEGER PRIMARY KEY AUTOINCREMENT,
  group_id              INTEGER NOT NULL,
  item_id               INTEGER NOT NULL,
  similarity_score      REAL,
  is_primary_candidate  INTEGER NOT NULL DEFAULT 0,
  review_status         TEXT DEFAULT 'pending',
  FOREIGN KEY (group_id) REFERENCES duplicate_groups(group_id) ON DELETE CASCADE,
  FOREIGN KEY (item_id)  REFERENCES items(item_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dup_groups_type      ON duplicate_groups(group_type);
CREATE INDEX IF NOT EXISTS idx_dup_group_items_gid  ON duplicate_group_items(group_id);
CREATE INDEX IF NOT EXISTS idx_dup_group_items_iid  ON duplicate_group_items(item_id);

-- ============================================================
-- 7. timeline events
-- ============================================================
CREATE TABLE IF NOT EXISTS timeline_events (
  event_id           INTEGER PRIMARY KEY AUTOINCREMENT,
  bucket_key         TEXT NOT NULL,
  bucket_zoom        TEXT NOT NULL,
  event_time_ts      INTEGER NOT NULL,
  event_label        TEXT,
  item_count         INTEGER NOT NULL DEFAULT 0,
  total_size_bytes   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS timeline_event_items (
  event_item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id           INTEGER NOT NULL,
  item_id            INTEGER NOT NULL,
  FOREIGN KEY (event_id) REFERENCES timeline_events(event_id) ON DELETE CASCADE,
  FOREIGN KEY (item_id)  REFERENCES items(item_id) ON DELETE CASCADE
);

-- ============================================================
-- 8. index_jobs
-- ============================================================
CREATE TABLE IF NOT EXISTS index_jobs (
  job_id          INTEGER PRIMARY KEY AUTOINCREMENT,
  root_id         INTEGER,
  job_type        TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  started_ts      INTEGER,
  finished_ts     INTEGER,
  updated_ts      INTEGER,
  scanned_count   INTEGER NOT NULL DEFAULT 0,
  queued_count    INTEGER NOT NULL DEFAULT 0,
  indexed_count   INTEGER NOT NULL DEFAULT 0,
  skipped_count   INTEGER NOT NULL DEFAULT 0,
  error_count     INTEGER NOT NULL DEFAULT 0,
  pending_count   INTEGER NOT NULL DEFAULT 0,
  scan_complete   INTEGER NOT NULL DEFAULT 0,
  current_file    TEXT,
  note            TEXT,
  FOREIGN KEY (root_id) REFERENCES roots(root_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_status   ON index_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_root_id  ON index_jobs(root_id);

-- ============================================================
-- 9. index_job_errors
-- ============================================================
CREATE TABLE IF NOT EXISTS index_job_errors (
  error_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id         INTEGER NOT NULL,
  full_path      TEXT NOT NULL,
  stage          TEXT,
  error_code     TEXT,
  error_message  TEXT,
  created_ts     INTEGER NOT NULL,
  FOREIGN KEY (job_id) REFERENCES index_jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_errors_job ON index_job_errors(job_id);

-- ============================================================
-- 10. app_settings
-- ============================================================
CREATE TABLE IF NOT EXISTS app_settings (
  setting_key    TEXT PRIMARY KEY,
  setting_value  TEXT,
  updated_ts     INTEGER NOT NULL
);

INSERT OR IGNORE INTO app_settings VALUES ('theme',               'dark',  strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('language',            'en',    strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('ocr_enabled',         '0',     strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('max_extract_size_mb', '50',    strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('ignored_extensions',  '.tmp,.log,.lock,.DS_Store', strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('ignored_paths',       '.git,.svn,node_modules,__pycache__', strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('auto_rescan_minutes', '60',    strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('port',                '7878',  strftime('%s','now'));

INSERT OR IGNORE INTO app_settings VALUES ('llm_enabled',         '0',     strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_provider',        'ollama', strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_base_url',        'http://127.0.0.1:11434', strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_model',           'gemma3:4b', strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_api_key',         '',      strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_temperature',     '0.2',   strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_top_k',           '8',     strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_top_n_results',   '8',     strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_max_context_chars','24000',strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_system_prompt',   'You answer questions about the user''s indexed local files. Use only the supplied search results. If the results are insufficient, say so clearly. Be concise and factual.', strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_search_mode',     'fts_plus_llm', strftime('%s','now'));
INSERT OR IGNORE INTO app_settings VALUES ('llm_auto_summarize',  '0',     strftime('%s','now'));

-- ============================================================
-- 11. saved_searches
-- ============================================================
CREATE TABLE IF NOT EXISTS saved_searches (
  saved_search_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name            TEXT NOT NULL,
  query_text      TEXT,
  filters_json    TEXT,
  created_ts      INTEGER NOT NULL,
  updated_ts      INTEGER NOT NULL
);
