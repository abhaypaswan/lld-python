"""Sliding window log: keep every timestamp, count what is still in range."""

from __future__ import annotations

from collections import deque

from .algorithm import Decision, RateLimitAlgorithm


class SlidingWindowLog(RateLimitAlgorithm):
    """Exactly correct, and the most expensive.

    No boundary burst is possible because the window genuinely slides: the
    question is always "how many in the last N seconds", not "how many in this
    bucket".

    The cost is memory proportional to the limit -- one timestamp per allowed
    request per client. At a limit of 10,000 across a million clients that is
    not a viable amount of state, which is what SlidingWindowCounter trades
    away.
    """

    name = "sliding-window-log"

    def __init__(self, limit: int, window: float):
        super().__init__(limit, window)
        self._timestamps: deque[float] = deque()

    def allow(self, now: float, cost: int = 1) -> Decision:
        cutoff = now - self.window
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

        if len(self._timestamps) + cost > self.limit:
            # The oldest timestamp is the one whose expiry frees a slot.
            oldest = self._timestamps[0]
            return Decision(False, self.limit - len(self._timestamps), oldest + self.window - now)

        self._timestamps.extend([now] * cost)
        return Decision(True, self.limit - len(self._timestamps))

    def reset(self) -> None:
        self._timestamps.clear()
