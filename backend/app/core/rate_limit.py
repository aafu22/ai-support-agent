"""Small in-memory sliding-window rate limiter.

Good enough for a single backend instance. With several instances use a shared
store such as Redis (see README: limitations)."""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            if len(self._hits) > 10_000:  # crude memory cap
                self._hits = defaultdict(deque, {k: v for k, v in self._hits.items() if v})
            return True


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, per_minute: int):
    """FastAPI dependency factory: `Depends(rate_limit('chat', 20))`."""

    def dependency(request: Request) -> None:
        if not limiter.allow(f"{name}:{client_ip(request)}", per_minute):
            raise HTTPException(429, "Too many requests. Please slow down.", headers={"Retry-After": "60"})

    return dependency
