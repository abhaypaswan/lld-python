"""First In First Out: drop whatever was added first, reads notwithstanding."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .policy import EvictionPolicy


class FIFOPolicy(EvictionPolicy):
    """Insertion order only.

    The one-line difference from LRU: `record_access` does nothing. Reading a
    key does not buy it any more time. Worth having next to LRU because it
    makes the thing LRU actually adds very easy to see.
    """

    name = "fifo"

    def __init__(self):
        self._keys: OrderedDict[Any, None] = OrderedDict()

    def record_access(self, key: Any) -> None:
        pass

    def record_insert(self, key: Any) -> None:
        self._keys.setdefault(key, None)

    def record_removal(self, key: Any) -> None:
        self._keys.pop(key, None)

    def evict(self) -> Any:
        if not self._keys:
            raise KeyError("Nothing to evict: the policy is tracking no keys")
        key, _ = self._keys.popitem(last=False)
        return key

    def clear(self) -> None:
        self._keys.clear()

    def order(self) -> list:
        return list(reversed(self._keys))
