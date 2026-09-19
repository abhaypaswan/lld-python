"""Strategy: how a single client's request budget is counted.

All four algorithms answer the same question -- may this request through right
now? -- and differ only in how they remember the recent past. That difference
is entirely a memory-versus-accuracy trade, which is what makes it a strategy
rather than a subclass of the limiter.

`now` is passed in rather than read from the clock inside. Every one of these
is a time-based algorithm, and a time-based algorithm that reads its own clock
can only be tested by sleeping.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    """The verdict on one request."""

    allowed: bool
    remaining: int
    #: Seconds until the next request would be allowed. 0 when one is allowed now.
    retry_after: float = 0.0

    def __bool__(self) -> bool:
        return self.allowed

    def __str__(self) -> str:
        if self.allowed:
            return f"allowed (remaining: {self.remaining})"
        return f"rejected (retry after {self.retry_after:.2f}s)"


class RateLimitAlgorithm(ABC):
    """Tracks one client's usage and rules on each request."""

    name: str = "algorithm"

    def __init__(self, limit: int, window: float):
        if limit <= 0:
            raise ValueError(f"Limit must be positive, got {limit}")
        if window <= 0:
            raise ValueError(f"Window must be positive, got {window}")

        self.limit = limit
        self.window = window

    @abstractmethod
    def allow(self, now: float, cost: int = 1) -> Decision:
        """Rule on a request of size `cost` arriving at `now`."""

    @abstractmethod
    def reset(self) -> None:
        """Forget all history for this client."""
