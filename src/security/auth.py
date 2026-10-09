"""
API-key authentication with simple role-based access control.

Configure keys with the SENTINEL_API_KEYS environment variable, a comma
separated list of `name:key:role` entries (role is viewer | analyst | admin):

    SENTINEL_API_KEYS="dashboard:3f9c...:viewer,ops:a81b...:analyst,root:77de...:admin"

Behaviour:
* No keys configured  -> every protected endpoint returns 503 (fail closed).
* SENTINEL_AUTH_DISABLED=true -> auth is skipped (local development only;
  a warning is logged at startup).
Keys are compared in constant time against SHA-256 digests.
"""
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

ROLE_ORDER = {"viewer": 1, "analyst": 2, "admin": 3}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class Principal:
    name: str
    role: str


def auth_disabled() -> bool:
    return os.environ.get("SENTINEL_AUTH_DISABLED", "").lower() in ("1", "true", "yes")


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def load_keys() -> Dict[str, Principal]:
    """Return {sha256(key) hex -> Principal}. Read on every call so env changes apply."""
    keys: Dict[str, Principal] = {}
    for entry in os.environ.get("SENTINEL_API_KEYS", "").split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":")
        if len(parts) != 3 or parts[2] not in ROLE_ORDER or not parts[1]:
            raise RuntimeError("SENTINEL_API_KEYS entries must look like name:key:role (viewer|analyst|admin)")
        name, key, role = parts
        keys[_digest(key).hex()] = Principal(name=name, role=role)
    return keys


def _authenticate(request: Request, provided: Optional[str]) -> Principal:
    if auth_disabled():
        return Principal(name="dev", role="admin")
    keys = load_keys()
    if not keys:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Authentication is not configured (set SENTINEL_API_KEYS)")
    if not provided:
        _count_failure("missing")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key",
                            headers={"WWW-Authenticate": "ApiKey"})
    provided_digest = _digest(provided)
    match = None
    for stored_hex, principal in keys.items():  # no early exit -> constant work per key
        if hmac.compare_digest(bytes.fromhex(stored_hex), provided_digest):
            match = principal
    if match is None:
        _count_failure("invalid")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key",
                            headers={"WWW-Authenticate": "ApiKey"})
    request.state.principal = match
    return match


def _count_failure(reason: str) -> None:
    try:
        from src.api.metrics import AUTH_FAILURES
        AUTH_FAILURES.labels(reason=reason).inc()
    except Exception:  # metrics must never break auth
        pass


def require_role(minimum: str):
    """FastAPI dependency factory enforcing a minimum role."""
    def dependency(request: Request, key: Optional[str] = Depends(api_key_header)) -> Principal:
        principal = _authenticate(request, key)
        if ROLE_ORDER[principal.role] < ROLE_ORDER[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role '{minimum}' or higher")
        return principal
    return dependency
