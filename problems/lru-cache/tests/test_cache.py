"""Eviction behaviour, which is the entire point of the problem."""

import pytest
from lru_cache import Cache
from lru_cache.policies import LFUPolicy, get_policy


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


# -- LRU ------------------------------------------------------------------


def test_the_least_recently_used_key_is_evicted():
    cache = Cache(2, "lru")
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")  # a is now the most recent
    cache.put("c", 3)  # so b goes

    assert "b" not in cache
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_reading_a_key_protects_it_from_eviction():
    cache = Cache(3, "lru")
    for key in "abc":
        cache.put(key, key)

    for _ in range(5):
        cache.get("a")
    cache.put("d", "d")

    assert "a" in cache
    assert "b" not in cache, "the oldest untouched key should go"


def test_overwriting_a_key_does_not_evict_anything():
    cache = Cache(2, "lru")
    cache.put("a", 1)
    cache.put("b", 2)

    cache.put("a", 99)

    assert len(cache) == 2
    assert cache.stats.evictions == 0, "an update is not an insert"
    assert cache.get("a") == 99


def test_overwriting_counts_as_using_the_key():
    cache = Cache(2, "lru")
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 99)  # a is now the most recent
    cache.put("c", 3)

    assert "b" not in cache
    assert "a" in cache


def test_the_cache_never_grows_past_its_capacity():
    cache = Cache(3, "lru")

    for i in range(100):
        cache.put(i, i)

    assert len(cache) == 3
    assert cache.keys() == [99, 98, 97]


# -- FIFO -----------------------------------------------------------------


def test_fifo_ignores_reads():
    cache = Cache(2, "fifo")
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")  # makes no difference under FIFO
    cache.put("c", 3)

    assert "a" not in cache, "FIFO evicts by insertion order, not use"
    assert "b" in cache


# -- LFU ------------------------------------------------------------------


def test_lfu_evicts_the_least_used_key():
    cache = Cache(2, "lfu")
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    cache.get("a")  # a has been used 3 times, b once
    cache.put("c", 3)

    assert "b" not in cache
    assert "a" in cache


def test_lfu_breaks_frequency_ties_by_recency():
    cache = Cache(2, "lfu")
    cache.put("a", 1)
    cache.put("b", 2)  # both on frequency 1
    cache.put("c", 3)

    assert "a" not in cache, "the older of the two tied keys should go"
    assert "b" in cache


def test_lfu_tracks_the_minimum_frequency_without_scanning():
    policy = LFUPolicy()
    for key in "abc":
        policy.record_insert(key)

    policy.record_access("a")
    policy.record_access("b")
    policy.record_access("c")  # every key is now on frequency 2

    assert policy.evict() == "a", "the minimum should have stepped up to 2"


def test_lfu_frequency_survives_an_overwrite():
    cache = Cache(2, "lfu")
    cache.put("a", 1)
    cache.get("a")
    cache.put("a", 2)

    assert cache.policy.frequency_of("a") == 3


# -- TTL ------------------------------------------------------------------


def test_an_expired_key_reads_as_a_miss(clock):
    cache = Cache(4, default_ttl=10, clock=clock)
    cache.put("a", 1)

    clock.advance(11)

    assert cache.get("a") is None
    assert cache.stats.expirations == 1


def test_an_unexpired_key_still_reads(clock):
    cache = Cache(4, default_ttl=10, clock=clock)
    cache.put("a", 1)

    clock.advance(9)

    assert cache.get("a") == 1


def test_a_per_key_ttl_overrides_the_default(clock):
    cache = Cache(4, default_ttl=10, clock=clock)
    cache.put("short", 1, ttl=2)
    cache.put("forever", 2, ttl=None)

    clock.advance(5)

    assert cache.get("short") is None
    assert cache.get("forever") == 2


def test_expired_keys_are_dropped_before_live_ones(clock):
    cache = Cache(2, "lru", clock=clock)
    cache.put("stale", 1, ttl=5)
    cache.put("fresh", 2, ttl=None)

    clock.advance(6)
    cache.put("new", 3)

    assert "fresh" in cache, "a live key should not be evicted while a dead one sits there"
    assert "new" in cache
    assert cache.stats.evictions == 0


def test_reading_an_expired_key_frees_its_slot(clock):
    cache = Cache(2, default_ttl=5, clock=clock)
    cache.put("a", 1)
    clock.advance(6)

    cache.get("a")

    assert len(cache) == 0, "reading an expired key should drop it, not leave it taking up space"


# -- odds and ends --------------------------------------------------------


def test_delete_reports_whether_the_key_was_there():
    cache = Cache(2)
    cache.put("a", 1)

    assert cache.delete("a") is True
    assert cache.delete("a") is False


def test_a_deleted_key_is_no_longer_a_candidate_for_eviction():
    cache = Cache(2, "lru")
    cache.put("a", 1)
    cache.put("b", 2)
    cache.delete("a")
    cache.put("c", 3)

    assert "b" in cache, "deleting a should have freed the slot"
    assert "c" in cache


def test_stats_track_hits_and_misses():
    cache = Cache(2)
    cache.put("a", 1)
    cache.get("a")
    cache.get("a")
    cache.get("nope")

    assert (cache.stats.hits, cache.stats.misses) == (2, 1)
    assert cache.stats.hit_rate == pytest.approx(2 / 3)


def test_clear_empties_the_policy_too():
    cache = Cache(2, "lru")
    cache.put("a", 1)
    cache.clear()
    cache.put("b", 2)
    cache.put("c", 3)

    assert len(cache) == 2
    assert "a" not in cache


def test_capacity_has_to_be_positive():
    with pytest.raises(ValueError, match="must be positive"):
        Cache(0)


def test_an_unknown_policy_lists_the_known_ones():
    with pytest.raises(ValueError, match="fifo, lfu, lru"):
        get_policy("random")


def test_evicting_from_an_empty_policy_is_an_error():
    with pytest.raises(KeyError, match="Nothing to evict"):
        get_policy("lru").evict()
