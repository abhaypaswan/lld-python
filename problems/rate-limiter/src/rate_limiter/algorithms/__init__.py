from .algorithm import Decision, RateLimitAlgorithm
from .fixed_window import FixedWindowCounter
from .sliding_window_counter import SlidingWindowCounter
from .sliding_window_log import SlidingWindowLog
from .token_bucket import TokenBucket

ALGORITHMS: dict[str, type[RateLimitAlgorithm]] = {
    TokenBucket.name: TokenBucket,
    FixedWindowCounter.name: FixedWindowCounter,
    SlidingWindowLog.name: SlidingWindowLog,
    SlidingWindowCounter.name: SlidingWindowCounter,
}


def get_algorithm(name: str) -> type[RateLimitAlgorithm]:
    try:
        return ALGORITHMS[name]
    except KeyError:
        known = ", ".join(sorted(ALGORITHMS))
        raise ValueError(f"{name!r} is not a rate limit algorithm. Try one of: {known}") from None


__all__ = [
    "RateLimitAlgorithm",
    "Decision",
    "TokenBucket",
    "FixedWindowCounter",
    "SlidingWindowLog",
    "SlidingWindowCounter",
    "ALGORITHMS",
    "get_algorithm",
]
