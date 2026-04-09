"""
NotingHill — services/search_service.py

Search modes:
  • nl2sql      — câu hỏi tự nhiên → LLM generate SQL → execute → narrate
                  Bypass FTS hoàn toàn. Xử lý được mọi loại query phức tạp.
  • fts_plus_llm — FTS keyword search → LLM tóm tắt kết quả (mode cũ)
  • fts_only    — FTS thuần, không LLM
"""
from __future__ import annotations

import time
import re

from . import llm_service
from ..db import repo_items, repo_search


ALLOWED_FILTER_KEYS = (
    "file_type_group",
    "extension",
    "root_id",
    "min_size",
    "max_size",
    "since_ts",
    "until_ts",
    "limit",
    "offset",
    "order_by",
)

_WEEK_PAT  = re.compile(r"\bthis\s+week\b|\blast\s+7\s+days?\b|\bpast\s+week\b", re.I)
_TODAY_PAT = re.compile(r"\btoday\b|\bthis\s+day\b", re.I)
_MONTH_PAT = re.compile(r"\bthis\s+month\b|\blast\s+30\s+days?\b|\bpast\s+month\b", re.I)


def _inject_temporal_filter(query: str, filters: dict) -> dict:
    if filters.get("since_ts"):
        return filters
    now = int(time.time())
    if _TODAY_PAT.search(query):
        filters = {**filters, "since_ts": now - 86_400}
    elif _WEEK_PAT.search(query):
        filters = {**filters, "since_ts": now - 7 * 86_400}
    elif _MONTH_PAT.search(query):
        filters = {**filters, "since_ts": now - 30 * 86_400}
    return filters


def search(query: str, **filters) -> list[dict]:
    """Pure keyword search — FTS or list_items fallback."""
    clean = {k: v for k, v in filters.items() if k in ALLOWED_FILTER_KEYS}
    if query.strip():
        return repo_search.fts_search(query, **clean)
    return repo_items.list_items(**clean)


def ask(query: str, **filters) -> dict:
    """
    Route câu hỏi tự nhiên đến đúng pipeline theo llm_search_mode.

    nl2sql mode (khuyến nghị):
        Câu hỏi → LLM sinh SQL từ schema pre-prompt → execute SQLite → LLM narrate
        Không dùng FTS. Hiểu được: filter theo loại file, tên, ngày, size, v.v.

    fts_plus_llm mode (cũ):
        FTS keyword search → LLM tóm tắt. Chỉ tốt với keyword search đơn giản.

    fts_only:
        Không dùng LLM, trả về FTS results thô.
    """
    effective = {k: v for k, v in filters.items() if k in ALLOWED_FILTER_KEYS}
    search_limit = max(1, min(int(effective.get("limit") or 20), 50))
    effective["limit"] = search_limit

    settings = llm_service.get_llm_settings()
    search_mode = str(settings.get("llm_search_mode") or "fts_plus_llm").lower()

    # ── nl2sql: bypass FTS, câu hỏi đi thẳng vào SQL pipeline ───────────
    if search_mode == "nl2sql" and settings.get("llm_enabled"):
        from .nl2sql_service import nl2sql_answer
        from .llm_service import _chat

        result = nl2sql_answer(
            question=query,
            llm_chat_fn=_chat,
            llm_settings=settings,
            max_retries=2,
        )
        # Trả rows về frontend để hiển thị file list
        rows = result.get("rows", [])
        return {
            "query":             query,
            "count":             len(rows),
            "results":           rows,
            "answer":            result.get("answer", ""),
            "mode":              "nl2sql",
            "sql":               result.get("sql"),
            "row_count":         result.get("row_count", 0),
            "used_result_count": result.get("row_count", 0),
            "context_chars":     0,
            "provider":          settings.get("llm_provider"),
            "model":             settings.get("llm_model"),
            "error":             result.get("error"),
            "llm":               result,
        }

    # ── fts_only: không dùng LLM ─────────────────────────────────────────
    if search_mode == "fts_only" or not settings.get("llm_enabled"):
        effective = _inject_temporal_filter(query, effective)
        results = search(query=query, **effective)
        if not results:
            browse = {k: v for k, v in effective.items() if v is not None}
            browse["order_by"] = "modified_ts DESC"
            results = repo_items.list_items(**browse)
        return {
            "query":   query,
            "count":   len(results),
            "results": results,
            "answer":  "",
            "mode":    "fts_only",
        }

    # ── fts_plus_llm: FTS → LLM narrate (mode cũ, fallback) ─────────────
    effective = _inject_temporal_filter(query, effective)
    results = search(query=query, **effective)
    if not results:
        browse = {k: v for k, v in effective.items()
                  if k in ALLOWED_FILTER_KEYS and v is not None}
        browse["order_by"] = "modified_ts DESC"
        results = repo_items.list_items(**browse)

    llm_data = llm_service.answer_search_question(query, results)
    return {
        "query":             query,
        "count":             len(results),
        "results":           results,
        "answer":            llm_data.get("answer", ""),
        "mode":              llm_data.get("mode"),
        "used_result_count": llm_data.get("used_result_count"),
        "context_chars":     llm_data.get("context_chars"),
        "provider":          llm_data.get("provider"),
        "model":             llm_data.get("model"),
        "llm":               llm_data,
    }


def get_preview(item_id: int) -> dict | None:
    item = repo_items.get_item(item_id)
    if not item:
        return None
    from ..db.connection import get_db
    with get_db() as con:
        dups = con.execute(
            """
            SELECT dgi.group_id, dg.group_type, dg.item_count
            FROM duplicate_group_items dgi
            JOIN duplicate_groups dg ON dg.group_id=dgi.group_id
            WHERE dgi.item_id=?
            """,
            (item_id,),
        ).fetchall()
    item["duplicate_info"] = [dict(d) for d in dups]
    return item
