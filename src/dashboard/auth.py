"""
Dashboard login (pure functions, no Streamlit imports so they are unit-testable).

Configuration (environment):
  DASHBOARD_PASSWORD        shared password for the dashboard (required)
  DASHBOARD_AUTH_DISABLED   "true" skips the login (local development only)

Fails closed: with no password configured and auth not explicitly disabled,
nobody can log in. Limitation: this is one shared password with per-session
throttling. For anything beyond a small team, put the dashboard behind a
reverse proxy / SSO.
"""
import hashlib
import hmac
import os

MAX_FREE_ATTEMPTS = 3


def auth_disabled() -> bool:
    return os.environ.get("DASHBOARD_AUTH_DISABLED", "").lower() in ("1", "true", "yes")


def is_configured() -> bool:
    return bool(os.environ.get("DASHBOARD_PASSWORD"))


def check_password(candidate: str) -> bool:
    expected = os.environ.get("DASHBOARD_PASSWORD", "")
    if not expected or not candidate:
        return False
    a = hashlib.sha256(candidate.encode()).digest()
    b = hashlib.sha256(expected.encode()).digest()
    return hmac.compare_digest(a, b)


def backoff_seconds(failed_attempts: int) -> int:
    """Delay to impose after N consecutive failures in a session (capped at 30 s)."""
    if failed_attempts < MAX_FREE_ATTEMPTS:
        return 0
    return min(30, 2 ** (failed_attempts - MAX_FREE_ATTEMPTS + 1))
