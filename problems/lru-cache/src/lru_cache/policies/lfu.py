"""Least Frequently Used: drop whatever has been touched fewest times."""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from typing import Any

from .policy import EvictionPolicy


class LFUPolicy(EvictionPolicy):
    """Frequency buckets, with the minimum frequency tracked as we go.

    The naive LFU keeps a count per key and scans for the minimum on eviction,
    which is O(n). Here, keys are grouped into an ordered bucket per frequency
    and `_min_frequency` is maintained incrementally, so eviction is O(1).

    `_min_frequency` only ever moves in two ways: it resets to 1 on any insert,
    and it steps up by exactly one when the bucket it points at empties out
    because its last key was promoted. That is why no search is needed.

    Ties inside a bucket break by recency, which is why the buckets are
    OrderedDicts rather than sets.
    """

    name = "lfu"

    def __init__(self):
        self._frequencies: dict[Any, int] = {}
        self._buckets: dict[int, OrderedDict] = defaultdict(OrderedDict)
        self._min_frequency = 0

    def record_access(self, key: Any) -> None:
        frequency = self._frequencies.get(key)
        if frequency is None:
            return

        del self._buckets[frequency][key]
        if not self._buckets[frequency]:
            del self._buckets[frequency]
            if self._min_frequency == frequency:
                self._min_frequency += 1

        self._frequencies[key] = frequency + 1
        self._buckets[frequency + 1][key] = None

    def record_insert(self, key: Any) -> None:
        if key in self._frequencies:
            self.record_access(key)
            return

        self._frequencies[key] = 1
        self._buckets[1][key] = None
        self._min_frequency = 1

    def record_removal(self, key: Any) -> None:
        frequency = self._frequencies.pop(key, None)
        if frequency is None:
            return

        bucket = self._buckets.get(frequency)
        if bucket is not None:
            bucket.pop(key, None)
            if not bucket:
                del self._buckets[frequency]

    def evict(self) -> Any:
        bucket = self._buckets.get(self._min_frequency)
        if not bucket:
            raise KeyError("Nothing to evict: the policy is tracking no keys")

        key, _ = bucket.popitem(last=False)
        if not bucket:
            del self._buckets[self._min_frequency]

        del self._frequencies[key]
        return key

    def frequency_of(self, key: Any) -> int:
        return self._frequencies.get(key, 0)

    def clear(self) -> None:
        self._frequencies.clear()
        self._buckets.clear()
        self._min_frequency = 0

    def order(self) -> list:
        return sorted(self._frequencies, key=lambda k: -self._frequencies[k])
