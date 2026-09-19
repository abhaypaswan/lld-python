"""Rate limiting, with the counting algorithm as a swappable strategy."""

from .limiter import Decision, RateLimiter

__all__ = ["RateLimiter", "Decision"]
