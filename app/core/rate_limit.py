"""Lightweight thread-safe in-memory sliding-window rate limiter.

Protects authentication endpoints against brute-force attacks and guards expensive
on-demand LLM calls (e.g. force_refresh=True on /predictions/course/advise-ai)
without requiring an external Redis server.
"""

import math
import threading
import time
from collections import deque

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter keyed by client IP or user identifier."""

    def __init__(self, *, max_requests: int, window_seconds: int, detail: str) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.detail = detail
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = {}

    def check(self, key: str) -> None:
        """Record a hit for key or raise 429 Too Many Requests when limit is exceeded."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = deque()
                self._buckets[key] = bucket

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(1, math.ceil(self.window_seconds - (now - bucket[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=self.detail,
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

            # Bound memory growth if many transient keys accumulate
            if len(self._buckets) > 4096:
                stale_keys = [
                    k for k, q in self._buckets.items() if not q or q[-1] <= cutoff
                ]
                for stale in stale_keys:
                    self._buckets.pop(stale, None)

    def reset(self) -> None:
        """Clear all recorded buckets (primarily for deterministic automated tests)."""
        with self._lock:
            self._buckets.clear()


def get_client_ip(request: Request) -> str:
    """Resolve client IP address for rate-limiting keys."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


login_rate_limiter = SlidingWindowRateLimiter(
    max_requests=10,
    window_seconds=60,
    detail="Too many login attempts. Please wait a minute before trying again.",
)

refresh_rate_limiter = SlidingWindowRateLimiter(
    max_requests=20,
    window_seconds=60,
    detail="Too many token refresh requests. Please try again shortly.",
)

ai_force_refresh_limiter = SlidingWindowRateLimiter(
    max_requests=3,
    window_seconds=300,
    detail="Bạn đã yêu cầu tạo lại gợi ý AI quá nhanh. Vui lòng chờ ít phút trước khi thử lại.",
)


def reset_all_rate_limiters() -> None:
    """Reset every global rate limiter instance."""
    login_rate_limiter.reset()
    refresh_rate_limiter.reset()
    ai_force_refresh_limiter.reset()
