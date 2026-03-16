"""FastAPI auth dependency — verifies Supabase JWT."""

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request

from src.db.supabase_client import get_anon_client

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    id: str
    email: Optional[str] = None


async def get_current_user(request: Request) -> AuthUser:
    """Extract and verify the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = auth_header.split(" ", 1)[1]
    try:
        response = get_anon_client().auth.get_user(token)
        user = response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return AuthUser(id=str(user.id), email=user.email)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Auth verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
