"""Supabase client helpers."""

import logging
from typing import Any, Optional

from supabase import Client, create_client

from src.config import settings

logger = logging.getLogger(__name__)

_service_client: Optional[Client] = None
_anon_client: Optional[Client] = None


def service() -> Client:
    """Service-role client — bypasses RLS."""
    global _service_client
    if _service_client is None:
        _service_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _service_client


def anon() -> Client:
    """Anon-key client — used for verifying JWTs."""
    global _anon_client
    if _anon_client is None:
        _anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    return _anon_client


def _first(result) -> Optional[dict[str, Any]]:
    if result and result.data:
        return result.data[0] if isinstance(result.data, list) else result.data
    return None


# ── Profile ──────────────────────────────────────────────────

def get_profile(user_id: str) -> Optional[dict[str, Any]]:
    return _first(
        service().table("profiles").select("*").eq("id", user_id).limit(1).execute()
    )


def upsert_profile(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    data["id"] = user_id
    return _first(service().table("profiles").upsert(data).execute()) or {}


# ── Search Criteria ──────────────────────────────────────────

def get_criteria(user_id: str) -> Optional[dict[str, Any]]:
    return _first(
        service().table("search_criteria").select("*").eq("user_id", user_id).limit(1).execute()
    )


def upsert_criteria(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    data["user_id"] = user_id
    return _first(
        service().table("search_criteria").upsert(data, on_conflict="user_id").execute()
    ) or {}


def get_all_criteria() -> list[dict[str, Any]]:
    """Used by the background agent to iterate through every user."""
    return service().table("search_criteria").select("*").execute().data or []


# ── Jobs ─────────────────────────────────────────────────────

def get_jobs(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    return (
        service().table("jobs").select("*")
        .eq("user_id", user_id).order("created_at", desc=True).limit(limit)
        .execute().data or []
    )


def get_jobs_filtered(
    user_id: str,
    added_by: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    q = (
        service().table("jobs").select("*")
        .eq("user_id", user_id).order("created_at", desc=True).limit(limit)
    )
    if added_by:
        q = q.eq("added_by", added_by)
    if date_from:
        q = q.gte("created_at", date_from)
    if date_to:
        q = q.lte("created_at", date_to)
    return q.execute().data or []


def get_job(user_id: str, job_id: str) -> Optional[dict[str, Any]]:
    return _first(
        service().table("jobs").select("*")
        .eq("id", job_id).eq("user_id", user_id).limit(1).execute()
    )


def upsert_job(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    data["user_id"] = user_id
    return _first(
        service().table("jobs").upsert(data, on_conflict="user_id,title,company,url").execute()
    ) or {}


def update_job(user_id: str, job_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return _first(
        service().table("jobs").update(data)
        .eq("id", job_id).eq("user_id", user_id).execute()
    ) or {}


def delete_job(user_id: str, job_id: str) -> None:
    service().table("jobs").delete().eq("id", job_id).eq("user_id", user_id).execute()


def job_exists(user_id: str, title: str, company: str, url: str) -> bool:
    result = (
        service().table("jobs").select("id")
        .eq("user_id", user_id).eq("title", title).eq("company", company)
        .eq("url", url or "").limit(1).execute()
    )
    return bool(result.data)


# ── Agent runs ───────────────────────────────────────────────

def insert_agent_run(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    data["user_id"] = user_id
    try:
        return _first(service().table("agent_runs").insert(data).execute()) or {}
    except Exception as e:
        logger.warning(f"insert_agent_run failed: {e}")
        return {}


def update_agent_run(run_id: str, data: dict[str, Any]) -> None:
    try:
        service().table("agent_runs").update(data).eq("id", run_id).execute()
    except Exception as e:
        logger.warning(f"update_agent_run failed: {e}")


def get_latest_agent_run(user_id: str) -> Optional[dict[str, Any]]:
    try:
        return _first(
            service().table("agent_runs").select("*")
            .eq("user_id", user_id).order("started_at", desc=True).limit(1).execute()
        )
    except Exception as e:
        logger.warning(f"get_latest_agent_run failed: {e}")
        return None
