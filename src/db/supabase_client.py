"""Supabase client helpers for DB operations."""

import logging
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from src.config.settings import config

logger = logging.getLogger(__name__)

_service_client: Optional[Client] = None
_anon_client: Optional[Client] = None


def get_service_client() -> Client:
    """Service-role client — bypasses RLS. Used for server-side DB operations."""
    global _service_client
    if _service_client is None:
        _service_client = create_client(
            config.app.supabase_url,
            config.app.supabase_service_role_key,
        )
    return _service_client


def get_anon_client() -> Client:
    """Anon-key client — used for JWT verification via auth.get_user()."""
    global _anon_client
    if _anon_client is None:
        _anon_client = create_client(
            config.app.supabase_url,
            config.app.supabase_anon_key,
        )
    return _anon_client


def _first_or_none(result) -> Optional[Dict[str, Any]]:
    """Safely get the first row from a query result, or None."""
    if result and result.data:
        return result.data[0] if isinstance(result.data, list) and result.data else result.data
    return None


# ── Profile ──────────────────────────────────────────────────

def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    result = (
        get_service_client()
        .table("profiles")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return _first_or_none(result)


def upsert_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    data["id"] = user_id
    result = (
        get_service_client()
        .table("profiles")
        .upsert(data)
        .execute()
    )
    return _first_or_none(result) or {}


# ── Search Criteria ──────────────────────────────────────────

def get_criteria(user_id: str) -> Optional[Dict[str, Any]]:
    result = (
        get_service_client()
        .table("search_criteria")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return _first_or_none(result)


def upsert_criteria(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    data["user_id"] = user_id
    result = (
        get_service_client()
        .table("search_criteria")
        .upsert(data, on_conflict="user_id")
        .execute()
    )
    return _first_or_none(result) or {}


# ── Jobs ─────────────────────────────────────────────────────

def get_jobs(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    query = (
        get_service_client()
        .table("jobs")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data or []


def get_job(user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
    result = (
        get_service_client()
        .table("jobs")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return _first_or_none(result)


def insert_job(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    data["user_id"] = user_id
    result = (
        get_service_client()
        .table("jobs")
        .insert(data)
        .execute()
    )
    return _first_or_none(result) or {}


def update_job(user_id: str, job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    result = (
        get_service_client()
        .table("jobs")
        .update(data)
        .eq("id", job_id)
        .eq("user_id", user_id)
        .execute()
    )
    return _first_or_none(result) or {}


def upsert_job(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update — uses (user_id, title, company, url) as conflict key."""
    data["user_id"] = user_id
    result = (
        get_service_client()
        .table("jobs")
        .upsert(data, on_conflict="user_id,title,company,url")
        .execute()
    )
    return _first_or_none(result) or {}
