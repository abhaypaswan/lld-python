"""The cache: a plain map, plus a policy that decides who gets thrown out."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .policies import EvictionPolicy, get_policy

MISSING = object()


@dataclass
class CacheStats:
    """Hit rate and eviction count. The numbers you actually tune against."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def __str__(self) -> str:
        return (
            f"hits={self.hits} misses={self.misses} "
            f"evictions={self.evictions} expirations={self.expirations} "
            f"hit_rate={self.hit_rate:.0%}"
        )


@dataclass
class Entry:
    value: Any
    expires_at: float | None = None

    def is_expired(self, now: float) -> bool:
        return self.expires_at is not None and now >= self.expires_at


class Cache:
    """A fixed-capacity key/value store.

    The map holds the data; the policy holds the ordering. Keeping them apart
    is what lets the same cache be LRU, LFU or FIFO without a single branch in
    this file.

    `clock` is injected so the TTL tests do not have to sleep.
    """

    def __init__(
        self,
        capacity: int,
        policy: EvictionPolicy | str = "lru",
        default_ttl: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        if capacity <= 0:
            raise ValueError(f"Capacity must be positive, got {capacity}")

        self.capacity = capacity
        self.policy = get_policy(policy) if isinstance(policy, str) else policy
        self.default_ttl = default_ttl
        self.clock = clock
        self.stats = CacheStats()
        self._entries: dict[Any, Entry] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, key: Any) -> bool:
        entry = self._entries.get(key)
        return entry is not None and not entry.is_expired(self.clock())

    def get(self, key: Any, default: Any = None) -> Any:
        entry = self._entries.get(key)

        if entry is None:
            self.stats.misses += 1
            return default

        if entry.is_expired(self.clock()):
            # An expired entry is a miss, not a hit -- and it is dropped now
            # rather than left to occupy space until eviction reaches it.
            self._discard(key)
            self.stats.expirations += 1
            self.stats.misses += 1
            return default

        self.stats.hits += 1
        self.policy.record_access(key)
        return entry.value

    def put(self, key: Any, value: Any, ttl: float | None = MISSING) -> None:
        ttl = self.default_ttl if ttl is MISSING else ttl
        expires_at = self.clock() + ttl if ttl is not None else None

        if key in self._entries:
            # Overwriting is not an insert. Capacity does not change, so no
            # eviction is needed -- getting this wrong throws out a live key
            # on every update.
            self._entries[key] = Entry(value, expires_at)
            self.policy.record_access(key)
            return

        if len(self._entries) >= self.capacity:
            self._evict_one()

        self._entries[key] = Entry(value, expires_at)
        self.policy.record_insert(key)

    def delete(self, key: Any) -> bool:
        """Remove a key. Returns whether it was there."""
        if key not in self._entries:
            return False
        self._discard(key)
        return True

    def clear(self) -> None:
        self._entries.clear()
        self.policy.clear()

    def keys(self) -> list:
        """Keys from most to least likely to survive the next eviction."""
        return [key for key in self.policy.order() if key in self._entries]

    # -- internals --------------------------------------------------------

    def _evict_one(self) -> Any:
        """Make room for one entry.

        Expired keys are cheaper to lose than live ones, so they go first. Only
        when nothing has expired do we ask the policy for a live victim.
        """
        now = self.clock()
        expired = [key for key, entry in self._entries.items() if entry.is_expired(now)]
        if expired:
            for key in expired:
                self._discard(key)
                self.stats.expirations += 1
            return expired[0]

        victim = self.policy.evict()
        del self._entries[victim]
        self.stats.evictions += 1
        return victim

    def _discard(self, key: Any) -> None:
        self._entries.pop(key, None)
        self.policy.record_removal(key)
