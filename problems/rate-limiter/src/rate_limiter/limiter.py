"""The limiter: one algorithm instance per client, created on demand."""

from __future__ import annotations

import time
from collections.abc import Callable

from .algorithms import Decision, RateLimitAlgorithm, get_algorithm


class RateLimiter:
    """Applies a rate limit per client key.

    The key is whatever you limit by -- a user id, an API key, an IP. The
    limiter does not care, which is why it is a plain hashable rather than a
    type of its own.

    Buckets are created lazily on first sight of a key. That is the right
    default: a service with a million registered users but a thousand active
    ones should hold a thousand buckets, not a million.
    """

    def __init__(
        self,
        limit: int,
        window: float,
        algorithm: str | type[RateLimitAlgorithm] = "token-bucket",
        clock: Callable[[], float] = time.monotonic,
        **algorithm_kwargs,
    ):
        self.limit = limit
        self.window = window
        self.clock = clock
        self.algorithm_class = get_algorithm(algorithm) if isinstance(algorithm, str) else algorithm
        self.algorithm_kwargs = algorithm_kwargs
        self._buckets: dict[object, RateLimitAlgorithm] = {}
        self._last_seen: dict[object, float] = {}

    def bucket_for(self, key: object, now: float | None = None) -> RateLimitAlgorithm:
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = self.algorithm_class(self.limit, self.window, **self.algorithm_kwargs)
            self._buckets[key] = bucket

        self._last_seen[key] = self.clock() if now is None else now
        return bucket

    def allow(self, key: object, cost: int = 1, now: float | None = None) -> Decision:
        """Rule on one request from `key`."""
        now = self.clock() if now is None else now
        return self.bucket_for(key, now).allow(now, cost)

    def reset(self, key: object | None = None) -> None:
        """Clear one client's history, or everyone's."""
        if key is None:
            self._buckets.clear()
            self._last_seen.clear()
        else:
            self._buckets.pop(key, None)
            self._last_seen.pop(key, None)

    def forget_idle(self, older_than: float, now: float | None = None) -> int:
        """Drop buckets for clients not seen in `older_than` seconds.

        Without something like this the bucket map is an unbounded leak: every
        key ever seen keeps a bucket forever. Production implementations
        usually hand this job to a TTL on the backing store instead.

        Dropping a bucket resets that client's budget, so `older_than` must be
        at least one window -- otherwise a client could clear their own limit
        by pausing briefly.
        """
        if older_than < self.window:
            raise ValueError(
                f"Forgetting after {older_than}s would let a client reset their own "
                f"limit by pausing; it must be at least one window ({self.window}s)"
            )

        now = self.clock() if now is None else now
        stale = [key for key, seen in self._last_seen.items() if now - seen > older_than]

        for key in stale:
            del self._buckets[key]
            del self._last_seen[key]
        return len(stale)

    @property
    def tracked_clients(self) -> int:
        return len(self._buckets)
