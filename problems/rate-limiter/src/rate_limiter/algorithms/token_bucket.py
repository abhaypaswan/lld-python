"""Token bucket: refill continuously, spend a token per request."""

from __future__ import annotations

from .algorithm import Decision, RateLimitAlgorithm


class TokenBucket(RateLimitAlgorithm):
    """The one that deliberately permits bursts.

    Tokens accumulate at `limit / window` per second up to a ceiling. A request
    spends one. A client who has been quiet banks tokens and can then spend
    them all at once, which is usually what you want from an API limiter: idle
    users should not be punished for being idle.

    Nothing is scheduled. Tokens are computed lazily from the elapsed time on
    each call, so an idle client costs nothing to maintain -- which matters
    when there are millions of them.

    `capacity` separates burst size from sustained rate. Leave it at `limit`
    for the usual behaviour; lower it to allow 100/minute sustained but never
    more than 10 at once.
    """

    name = "token-bucket"

    def __init__(self, limit: int, window: float, capacity: int | None = None):
        super().__init__(limit, window)
        self.capacity = limit if capacity is None else capacity
        if self.capacity <= 0:
            raise ValueError(f"Capacity must be positive, got {self.capacity}")

        self.refill_rate = limit / window
        self._tokens = float(self.capacity)
        self._last_refill: float | None = None

    def _refill(self, now: float) -> None:
        if self._last_refill is None:
            self._last_refill = now
            return

        elapsed = now - self._last_refill
        if elapsed <= 0:
            # A clock that went backwards must not mint tokens.
            self._last_refill = now
            return

        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def allow(self, now: float, cost: int = 1) -> Decision:
        self._refill(now)

        if cost > self.capacity:
            raise ValueError(
                f"A request costing {cost} can never be served by a bucket "
                f"holding at most {self.capacity}"
            )

        if self._tokens < cost:
            shortfall = cost - self._tokens
            return Decision(False, int(self._tokens), shortfall / self.refill_rate)

        self._tokens -= cost
        return Decision(True, int(self._tokens))

    def available_tokens(self, now: float) -> float:
        self._refill(now)
        return self._tokens

    def reset(self) -> None:
        self._tokens = float(self.capacity)
        self._last_refill = None
