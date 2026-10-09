"""
In-memory sliding-window rate limiter.

Limitation: state is per process. With several uvicorn workers/replicas the
effective limit is multiplied; use a shared store (e.g. Redis) or an API
gateway if you scale out.
"""
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Tuple


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, identity: str) -> Tuple[bool, int]:
        """Record a hit. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[identity]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False, max(1, int(self.window - (now - q[0])) + 1)
            q.append(now)
            if len(self._hits) > 10_000:  # bound memory
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return True, 0
