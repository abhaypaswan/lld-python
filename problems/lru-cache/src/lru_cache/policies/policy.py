"""Strategy: which key gets thrown out when the cache is full.

The cache itself never learns the rule. It tells the policy when a key is
touched and when one is added, and asks it which key to drop. Swapping LRU for
LFU is a constructor argument.

Every method here has to be O(1) for the cache to keep its promise, which is
what forces each policy to carry its own bookkeeping structure rather than
scanning the key set on eviction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EvictionPolicy(ABC):
    """Tracks usage and names a victim when space is needed."""

    name: str = "policy"

    @abstractmethod
    def record_access(self, key: Any) -> None:
        """A key was read or overwritten."""

    @abstractmethod
    def record_insert(self, key: Any) -> None:
        """A key was added to the cache for the first time."""

    @abstractmethod
    def record_removal(self, key: Any) -> None:
        """A key left the cache, by eviction or by explicit delete."""

    @abstractmethod
    def evict(self) -> Any:
        """Name and forget the key to drop. Raises KeyError when empty."""

    @abstractmethod
    def clear(self) -> None:
        """Forget everything."""

    def order(self) -> list:
        """Keys from most to least likely to be kept. For tests and display."""
        raise NotImplementedError
