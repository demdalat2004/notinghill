"""
NotingHill — services/llm_service.py
LLM settings, connectivity checks, and search-answer synthesis.
"""
from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from ..db import repo_jobs


def _get_nl2sql():
    """Lazy import to avoid circular deps."""
    from . import nl2sql_service
    return nl2sql_service


DEFAULT_LLM_SETTINGS: dict[str, str] = {
    "llm_enabled":          "0",
    "llm_provider":         "ollama",
    "llm_base_url":         "http://127.0.0.1:11434",
    "llm_model":            "gemma3:4b",
    "llm_api_key":          "",
    "llm_temperature":      "0.2",
    "llm_top_k":            "8",
    "llm_top_n_results":    "8",
    "llm_max_context_chars":"24000",
    "llm_system_prompt": (
        "You are a local file search assistant. "
        "Answer only from the retrieved file results and metadata provided below. "
        "If the results are insufficient, say so clearly. "
        "Be concise and factual. Mention item_id when citing files."
    ),
    "llm_search_mode":      "fts_plus_llm",
    "llm_auto_summarize":   "0",
}


class LLMError(Exception):
    pass


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _to_float(value: str | None, default: float) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def _normalize_base_url(value: str | None, provider: str) -> str:
    text = (value or "").strip()
    if text:
        return text.rstrip("/")
    return "http://127.0.0.1:11434" if provider == "ollama" else "http://127.0.0.1:1234"


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None,
               headers: dict[str, str] | None = None, timeout: int = 20) -> dict[str, Any]:
    body = None
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = request.Request(url=url, data=body, headers=req_headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise LLMError(f"HTTP {exc.code}: {raw[:500]}") from exc
    except error.URLError as exc:
        raise LLMError(f"Connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise LLMError("Connection timed out") from exc
    except json.JSONDecodeError as exc:
        raise LLMError("Invalid JSON response from LLM provider") from exc


def get_llm_settings() -> dict[str, Any]:
    raw = repo_jobs.get_all_settings()
    merged = {**DEFAULT_LLM_SETTINGS, **raw}
    provider = (merged.get("llm_provider") or DEFAULT_LLM_SETTINGS["llm_provider"]).strip().lower()
    base_url = _normalize_base_url(merged.get("llm_base_url"), provider)
    return {
        "llm_enabled":          _to_bool(merged.get("llm_enabled"), False),
        "llm_provider":         provider,
        "llm_base_url":         base_url,
        "llm_model":            (merged.get("llm_model") or "").strip(),
        "llm_api_key":          merged.get("llm_api_key") or "",
        "llm_temperature":      _to_float(merged.get("llm_temperature"), 0.2),
        "llm_top_k":            _to_int(merged.get("llm_top_k"), 8),
        "llm_top_n_results":    _to_int(merged.get("llm_top_n_results"), 8),
        "llm_max_context_chars":_to_int(merged.get("llm_max_context_chars"), 24000),
        "llm_system_prompt":    (merged.get("llm_system_prompt") or DEFAULT_LLM_SETTINGS["llm_system_prompt"]).strip(),
        "llm_search_mode":      (merged.get("llm_search_mode") or "fts_plus_llm").strip().lower(),
        "llm_auto_summarize":   _to_bool(merged.get("llm_auto_summarize"), False),
    }


def save_llm_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_llm_settings()
    merged = {**current, **payload}
    provider = str(merged.get("llm_provider") or "ollama").strip().lower()
    base_url = _normalize_base_url(str(merged.get("llm_base_url") or ""), provider)

    persisted: dict[str, str] = {
        "llm_enabled":          "1" if bool(merged.get("llm_enabled")) else "0",
        "llm_provider":         provider,
        "llm_base_url":         base_url,
        "llm_model":            str(merged.get("llm_model") or "").strip(),
        "llm_api_key":          str(merged.get("llm_api_key") or ""),
        "llm_temperature":      str(_to_float(str(merged.get("llm_temperature")), 0.2)),
        "llm_top_k":            str(_to_int(str(merged.get("llm_top_k")), 8)),
        "llm_top_n_results":    str(_to_int(str(merged.get("llm_top_n_results")), 8)),
        "llm_max_context_chars":str(_to_int(str(merged.get("llm_max_context_chars")), 24000)),
        "llm_system_prompt":    str(merged.get("llm_system_prompt") or DEFAULT_LLM_SETTINGS["llm_system_prompt"]).strip(),
        "llm_search_mode":      str(merged.get("llm_search_mode") or "fts_plus_llm").strip().lower(),
        "llm_auto_summarize":   "1" if bool(merged.get("llm_auto_summarize")) else "0",
    }

    for key, value in persisted.items():
        repo_jobs.set_setting(key, value)
    return get_llm_settings()


def test_connection(override: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_llm_settings()
    if override:
        settings = {**settings, **override}
    provider = str(settings.get("llm_provider") or "ollama").lower()
    base_url = _normalize_base_url(str(settings.get("llm_base_url") or ""), provider)
    model = str(settings.get("llm_model") or "").strip()
    api_key = str(settings.get("llm_api_key") or "").strip()

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if provider == "ollama":
        data = _http_json("GET", f"{base_url}/api/tags", headers=headers)
        models = [m.get("name") for m in data.get("models", []) if m.get("name")]
        return {
            "ok": True, "provider": provider, "base_url": base_url,
            "model": model, "model_found": (model in models) if model else False,
            "available_models": models[:30],
        }

    if provider in {"openai", "lmstudio"}:
        data = _http_json("GET", f"{base_url}/v1/models", headers=headers)
        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
        return {
            "ok": True, "provider": provider, "base_url": base_url,
            "model": model, "model_found": (model in models) if model else False,
            "available_models": models[:30],
        }

    raise LLMError(f"Unsupported provider: {provider}")


def build_search_context(results: list[dict], max_items: int, max_chars: int) -> str:
    chunks: list[str] = []
    remaining = max_chars
    for idx, row in enumerate(results[:max_items], start=1):
        preview = (row.get("snippet") or row.get("content_preview") or "").strip()
        preview = " ".join(preview.split())
        block = (
            f"[{idx}] item_id={row.get('item_id')}\n"
            f"file_name: {row.get('file_name') or ''}\n"
            f"full_path: {row.get('full_path') or ''}\n"
            f"extension: {row.get('extension') or ''}\n"
            f"file_type_group: {row.get('file_type_group') or ''}\n"
            f"size_bytes: {row.get('size_bytes') or 0}\n"
            f"best_time_ts: {row.get('best_time_ts') or row.get('modified_ts') or 0}\n"
            f"preview: {preview}\n"
        )
        if len(block) > remaining:
            block = block[:remaining]
        if not block:
            break
        chunks.append(block)
        remaining -= len(block)
        if remaining <= 0:
            break
    return "\n".join(chunks)


def _chat(settings: dict[str, Any], messages: list[dict[str, str]]) -> str:
    provider = str(settings.get("llm_provider") or "ollama").lower()
    base_url = _normalize_base_url(str(settings.get("llm_base_url") or ""), provider)
    model = str(settings.get("llm_model") or "").strip()
    api_key = str(settings.get("llm_api_key") or "").strip()
    temperature = float(settings.get("llm_temperature") or 0.2)

    if not model:
        raise LLMError("Missing llm_model")

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if provider == "ollama":
        data = _http_json(
            "POST", f"{base_url}/api/chat",
            payload={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            headers=headers, timeout=90,
        )
        return ((data.get("message") or {}).get("content") or "").strip()

    if provider in {"openai", "lmstudio"}:
        data = _http_json(
            "POST", f"{base_url}/v1/chat/completions",
            payload={
                "model": model,
                "messages": messages,
                "temperature": temperature,
            },
            headers=headers, timeout=90,
        )
        choices = data.get("choices") or []
        if not choices:
            return ""
        return (((choices[0] or {}).get("message") or {}).get("content") or "").strip()

    raise LLMError(f"Unsupported provider: {provider}")


def answer_search_question(question: str, results: list[dict]) -> dict[str, Any]:
    """
    Route question to the right LLM mode:
      - "nl2sql"       → Text-to-SQL pipeline (schema pre-prompt → generate SQL → execute → narrate)
      - "fts_plus_llm" → Classic FTS results → LLM narration
      - "fts_only"     → No LLM, raise immediately
    """
    settings = get_llm_settings()
    if not settings.get("llm_enabled"):
        raise LLMError("LLM is disabled")

    search_mode = str(settings.get("llm_search_mode") or "fts_plus_llm").lower()

    if search_mode == "fts_only":
        raise LLMError("LLM search mode is set to fts_only")

    # ── nl2sql mode: ignore pre-fetched FTS results, generate SQL instead ──
    if search_mode == "nl2sql":
        nl2sql = _get_nl2sql()
        result = nl2sql.nl2sql_answer(
            question=question,
            llm_chat_fn=_chat,
            llm_settings=settings,
            max_retries=2,
        )
        return {
            "answer":            result["answer"],
            "mode":              "nl2sql",
            "sql":               result.get("sql"),
            "row_count":         result.get("row_count", 0),
            "used_result_count": result.get("row_count", 0),
            "context_chars":     0,
            "provider":          settings.get("llm_provider"),
            "model":             settings.get("llm_model"),
            "error":             result.get("error"),
        }

    # ── fts_plus_llm mode: classic FTS context → LLM narration ────────────
    top_n = max(1, int(settings.get("llm_top_n_results") or 8))
    max_context_chars = max(2000, int(settings.get("llm_max_context_chars") or 24000))
    context = build_search_context(results, top_n, max_context_chars)
    if not context.strip():
        context = "(No indexed files matched this query.)"

    system_prompt = str(settings.get("llm_system_prompt") or DEFAULT_LLM_SETTINGS["llm_system_prompt"]).strip()
    user_prompt = (
        f"Question:\n{question.strip()}\n\n"
        f"Search results:\n{context}\n\n"
        "Instructions:\n"
        "- Answer only from the search results above.\n"
        "- Mention item_id when citing relevant files.\n"
        "- If the results are insufficient, say that clearly.\n"
        "- Keep the answer concise."
    )
    answer = _chat(
        settings,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    return {
        "answer":            answer,
        "mode":              search_mode,
        "used_result_count": min(len(results), top_n),
        "context_chars":     len(context),
        "provider":          settings.get("llm_provider"),
        "model":             settings.get("llm_model"),
    }
