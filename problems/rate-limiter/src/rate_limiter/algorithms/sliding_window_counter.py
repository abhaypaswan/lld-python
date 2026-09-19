"""Sliding window counter: two buckets and a weighted estimate."""

from __future__ import annotations

import math

from .algorithm import Decision, RateLimitAlgorithm


class SlidingWindowCounter(RateLimitAlgorithm):
    """Fixed window's memory, most of sliding log's accuracy.

    Keeps a count for the current window and the previous one, then estimates
    the rate by weighting the previous window by how much of it still overlaps
    the sliding window:

        estimate = previous_count * (1 - elapsed_fraction) + current_count

    Thirty seconds into a sixty-second window, half the previous window still
    counts. That smooths out the boundary burst without storing a timestamp per
    request.

    It is an approximation, and it errs on the strict side: it assumes the
    previous window's requests were spread evenly, so a client who bunched them
    all at the start gets rejected slightly early. For rate limiting, rejecting
    a little early is the safe direction to be wrong in.
    """

    name = "sliding-window-counter"

    def __init__(self, limit: int, window: float):
        super().__init__(limit, window)
        self._window_index = 0
        self._current = 0
        self._previous = 0

    def _roll(self, index: int) -> None:
        if index == self._window_index:
            return

        # Jumping more than one window means the previous one is long gone.
        self._previous = self._current if index == self._window_index + 1 else 0
        self._current = 0
        self._window_index = index

    def estimate(self, now: float) -> float:
        index = math.floor(now / self.window)
        self._roll(index)

        elapsed = (now - index * self.window) / self.window
        return self._previous * (1 - elapsed) + self._current

    def allow(self, now: float, cost: int = 1) -> Decision:
        estimated = self.estimate(now)

        if estimated + cost > self.limit:
            index = math.floor(now / self.window)
            return Decision(
                False,
                max(0, self.limit - math.ceil(estimated)),
                max(0.0, (index + 1) * self.window - now),
            )

        self._current += cost
        return Decision(True, max(0, self.limit - math.ceil(estimated + cost)))

    def reset(self) -> None:
        self._window_index = 0
        self._current = 0
        self._previous = 0
