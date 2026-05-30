"""Token-bucket rate limiter stored in-memory per client IP."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

from agentapi.models import RateLimitConfig


class RateLimiter:
    """Simple sliding-window rate limiter keyed by client IP."""

    def __init__(self, config: RateLimitConfig) -> None:
        self.rpm = config.requests_per_minute
        self._windows: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float) -> None:
        cutoff = now - 60.0
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]

    def check(self, key: str) -> None:
        """Raise 429 if the client has exceeded the limit."""
        now = time.monotonic()
        self._prune(key, now)
        if len(self._windows[key]) >= self.rpm:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.rpm} requests per minute.",
            )
        self._windows[key].append(now)

    def remaining(self, key: str) -> int:
        """Return the number of requests remaining in the current window."""
        now = time.monotonic()
        self._prune(key, now)
        return max(0, self.rpm - len(self._windows[key]))


def create_rate_limit_dependency(config: RateLimitConfig):
    """Create a FastAPI dependency that enforces rate limiting."""
    limiter = RateLimiter(config)

    async def rate_limit(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        limiter.check(client_ip)

    return rate_limit
