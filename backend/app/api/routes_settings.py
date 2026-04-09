"""
NotingHill — api/routes_settings.py
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import repo_jobs
from ..services import llm_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    key: str
    value: str


class LLMSettingsUpdate(BaseModel):
    llm_enabled: Optional[bool] = None
    llm_provider: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_temperature: Optional[float] = None
    llm_top_k: Optional[int] = None
    llm_top_n_results: Optional[int] = None
    llm_max_context_chars: Optional[int] = None
    llm_system_prompt: Optional[str] = None
    llm_search_mode: Optional[str] = None
    llm_auto_summarize: Optional[bool] = None


@router.get("")
def get_all():
    return repo_jobs.get_all_settings()


@router.post("")
def update(req: SettingUpdate):
    repo_jobs.set_setting(req.key, req.value)
    return {"ok": True, "key": req.key}


@router.get("/llm")
def get_llm_settings():
    return llm_service.get_llm_settings()


@router.post("/llm")
def save_llm_settings(req: LLMSettingsUpdate):
    payload = req.model_dump(exclude_none=True)
    return {"ok": True, "settings": llm_service.save_llm_settings(payload)}


@router.post("/llm/test")
def test_llm_settings(req: LLMSettingsUpdate | None = None):
    payload = req.model_dump(exclude_none=True) if req else None
    try:
        data = llm_service.test_connection(payload)
        return data
    except llm_service.LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{key}")
def get_one(key: str):
    val = repo_jobs.get_setting(key)
    return {"key": key, "value": val}
