"""Thin HTTP client the dashboard uses to talk to the SentinelAI API."""
import os
from typing import Any, Dict, List, Optional

import requests

TIMEOUT = 30


class ApiError(Exception):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class SentinelClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("SENTINEL_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("SENTINEL_DASHBOARD_API_KEY", "")

    def _request(self, method: str, path: str, **kwargs) -> Any:
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        try:
            r = requests.request(method, f"{self.base_url}{path}", headers=headers,
                                 timeout=TIMEOUT, **kwargs)
        except requests.RequestException as e:
            raise ApiError(f"Cannot reach the API at {self.base_url}: {e.__class__.__name__}")
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ApiError(str(detail), r.status_code)
        return r.json()

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def status(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/status")

    def summary(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/summary")

    def metrics(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/metrics")

    def held_out_metrics(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/metrics/held-out")

    def threats(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._request("GET", "/api/v1/threats", params={"limit": limit})

    def audit_verify(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/audit/verify")

    def audit_blocks(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._request("GET", "/api/v1/audit/blocks", params={"limit": limit})

    def predict(self, filename: str, content: bytes) -> Dict[str, Any]:
        return self._request("POST", "/api/v1/predict",
                             files={"file": (filename, content, "text/csv")})
