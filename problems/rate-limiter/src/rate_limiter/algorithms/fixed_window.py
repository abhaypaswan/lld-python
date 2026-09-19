"""Fixed window: one counter per aligned time bucket."""

from __future__ import annotations

import math

from .algorithm import Decision, RateLimitAlgorithm


class FixedWindowCounter(RateLimitAlgorithm):
    """The cheapest correct-ish option: a counter and a window number.

    One integer of state per client, and the reset is free -- noticing the
    window number changed is the reset.

    Its well-known flaw is the boundary burst. With a limit of 100 per minute,
    a client can send 100 requests at 11:00:59 and 100 more at 11:01:00: two
    hundred requests in two seconds, both windows technically within budget.
    SlidingWindowLog and SlidingWindowCounter both exist to fix exactly this.
    """

    name = "fixed-window"

    def __init__(self, limit: int, window: float):
        super().__init__(limit, window)
        self._window_index = 0
        self._count = 0

    def allow(self, now: float, cost: int = 1) -> Decision:
        index = math.floor(now / self.window)

        if index != self._window_index:
            self._window_index = index
            self._count = 0

        if self._count + cost > self.limit:
            window_ends_at = (index + 1) * self.window
            return Decision(False, self.limit - self._count, max(0.0, window_ends_at - now))

        self._count += cost
        return Decision(True, self.limit - self._count)

    def reset(self) -> None:
        self._window_index = 0
        self._count = 0
