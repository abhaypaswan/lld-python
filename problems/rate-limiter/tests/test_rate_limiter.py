"""Every algorithm, driven by a clock the test controls."""

import pytest
from rate_limiter import RateLimiter
from rate_limiter.algorithms import (
    FixedWindowCounter,
    SlidingWindowCounter,
    SlidingWindowLog,
    TokenBucket,
    get_algorithm,
)

ALL_ALGORITHMS = ["token-bucket", "fixed-window", "sliding-window-log", "sliding-window-counter"]


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


# -- behaviour every algorithm must share ---------------------------------


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_requests_up_to_the_limit_are_allowed(algorithm, clock):
    limiter = RateLimiter(5, 1.0, algorithm, clock=clock)

    assert all(limiter.allow("user") for _ in range(5))


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_the_request_past_the_limit_is_rejected(algorithm, clock):
    limiter = RateLimiter(5, 1.0, algorithm, clock=clock)
    for _ in range(5):
        limiter.allow("user")

    assert not limiter.allow("user")


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_clients_are_limited_independently(algorithm, clock):
    limiter = RateLimiter(2, 1.0, algorithm, clock=clock)
    limiter.allow("alice")
    limiter.allow("alice")

    assert not limiter.allow("alice")
    assert limiter.allow("bob"), "bob has used none of his own budget"


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_the_budget_comes_back_once_the_window_has_fully_passed(algorithm, clock):
    limiter = RateLimiter(3, 10.0, algorithm, clock=clock)
    for _ in range(3):
        limiter.allow("user")
    assert not limiter.allow("user")

    # Two windows, not one. SlidingWindowCounter still weights the previous
    # window for the whole of the next one, so a single window is not enough
    # for every algorithm here -- see the dedicated test below.
    clock.advance(20.1)

    assert limiter.allow("user")


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_a_rejection_says_when_to_come_back(algorithm, clock):
    limiter = RateLimiter(2, 10.0, algorithm, clock=clock)
    for _ in range(2):
        limiter.allow("user")

    decision = limiter.allow("user")

    assert not decision.allowed
    assert 0 < decision.retry_after <= 10.0


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_a_rejected_request_does_not_consume_budget(algorithm, clock):
    limiter = RateLimiter(2, 10.0, algorithm, clock=clock)
    for _ in range(2):
        limiter.allow("user")

    for _ in range(50):
        limiter.allow("user")

    # The flood must not have pushed the recovery time out.
    clock.advance(20.1)
    assert limiter.allow("user")


@pytest.mark.parametrize("algorithm", ALL_ALGORITHMS)
def test_a_limit_has_to_be_positive(algorithm):
    with pytest.raises(ValueError, match="Limit must be positive"):
        get_algorithm(algorithm)(0, 1.0)


# -- where they differ ----------------------------------------------------


def test_token_bucket_lets_an_idle_client_burst(clock):
    bucket = TokenBucket(limit=10, window=10.0)  # one token per second
    for _ in range(10):
        bucket.allow(0.0)
    assert not bucket.allow(0.0)

    # Quiet for five seconds banks five tokens.
    assert bucket.available_tokens(5.0) == pytest.approx(5.0)
    assert sum(1 for _ in range(10) if bucket.allow(5.0)) == 5


def test_token_bucket_refills_gradually_not_all_at_once():
    bucket = TokenBucket(limit=10, window=10.0)
    for _ in range(10):
        bucket.allow(0.0)

    assert bucket.available_tokens(1.0) == pytest.approx(1.0)
    assert bucket.available_tokens(3.0) == pytest.approx(3.0)


def test_token_bucket_never_banks_more_than_its_capacity():
    bucket = TokenBucket(limit=10, window=10.0)

    assert bucket.available_tokens(10_000.0) == 10


def test_capacity_separates_burst_size_from_sustained_rate():
    # 60 per minute sustained, but never more than 5 back to back.
    bucket = TokenBucket(limit=60, window=60.0, capacity=5)

    assert sum(1 for _ in range(20) if bucket.allow(0.0)) == 5


def test_a_request_bigger_than_the_bucket_is_an_error():
    bucket = TokenBucket(limit=5, window=1.0)

    with pytest.raises(ValueError, match="can never be served"):
        bucket.allow(0.0, cost=6)


def test_a_backwards_clock_does_not_mint_tokens():
    bucket = TokenBucket(limit=5, window=5.0)
    for _ in range(5):
        bucket.allow(100.0)

    assert bucket.available_tokens(50.0) == pytest.approx(0.0)


def test_fixed_window_allows_the_boundary_burst():
    # This is the known flaw, pinned down so the fix can be shown to fix it.
    window = FixedWindowCounter(limit=5, window=10.0)

    at_end_of_first = sum(1 for _ in range(5) if window.allow(9.99))
    at_start_of_next = sum(1 for _ in range(5) if window.allow(10.01))

    assert at_end_of_first + at_start_of_next == 10, "10 requests in 0.02s, limit is 5 per 10s"


def test_the_sliding_log_has_no_boundary_burst():
    log = SlidingWindowLog(limit=5, window=10.0)

    at_end_of_first = sum(1 for _ in range(5) if log.allow(9.99))
    at_start_of_next = sum(1 for _ in range(5) if log.allow(10.01))

    assert at_end_of_first == 5
    assert at_start_of_next == 0, "the window genuinely slides"


def test_the_sliding_counter_softens_the_boundary_burst():
    counter = SlidingWindowCounter(limit=5, window=10.0)

    at_end_of_first = sum(1 for _ in range(5) if counter.allow(9.99))
    at_start_of_next = sum(1 for _ in range(5) if counter.allow(10.01))

    assert at_end_of_first == 5
    assert at_start_of_next < 5, "the previous window should still weigh on the estimate"


def test_the_sliding_counter_recovers_more_slowly_than_a_fixed_window():
    """The counter errs strict, which is the safe direction for a limiter."""
    counter = SlidingWindowCounter(limit=2, window=10.0)
    fixed = FixedWindowCounter(limit=2, window=10.0)
    for _ in range(2):
        counter.allow(0.0)
        fixed.allow(0.0)

    # Just into the next window, the previous one still weighs 99%.
    assert fixed.allow(10.1).allowed
    assert not counter.allow(10.1).allowed

    # Most of the way through it, the weight has decayed enough.
    assert counter.allow(19.0).allowed


def test_the_sliding_counter_forgets_a_window_it_skipped_entirely():
    counter = SlidingWindowCounter(limit=5, window=10.0)
    for _ in range(5):
        counter.allow(0.0)

    # Jumping three windows means the previous one is long gone.
    assert counter.estimate(35.0) == 0


def test_the_sliding_log_only_remembers_allowed_requests():
    log = SlidingWindowLog(limit=2, window=10.0)
    log.allow(0.0)
    log.allow(0.0)
    for _ in range(100):
        log.allow(0.0)

    assert len(log._timestamps) == 2


# -- the limiter around them ----------------------------------------------


def test_buckets_are_created_only_for_clients_that_show_up(clock):
    limiter = RateLimiter(5, 1.0, clock=clock)
    assert limiter.tracked_clients == 0

    limiter.allow("alice")

    assert limiter.tracked_clients == 1


def test_resetting_one_client_leaves_the_others_alone(clock):
    limiter = RateLimiter(1, 10.0, clock=clock)
    limiter.allow("alice")
    limiter.allow("bob")

    limiter.reset("alice")

    assert limiter.allow("alice")
    assert not limiter.allow("bob")


def test_idle_clients_are_forgotten(clock):
    limiter = RateLimiter(5, 1.0, clock=clock)
    limiter.allow("alice")
    limiter.allow("bob")

    clock.advance(100)
    limiter.allow("alice")

    assert limiter.forget_idle(older_than=10) == 1
    assert limiter.tracked_clients == 1


def test_forgetting_faster_than_a_window_is_refused(clock):
    limiter = RateLimiter(5, 60.0, clock=clock)

    with pytest.raises(ValueError, match="reset their own"):
        limiter.forget_idle(older_than=5)


def test_cost_lets_one_request_count_for_several(clock):
    limiter = RateLimiter(10, 1.0, clock=clock)

    assert limiter.allow("user", cost=7)
    assert not limiter.allow("user", cost=7)
    assert limiter.allow("user", cost=3)


def test_an_unknown_algorithm_lists_the_known_ones():
    with pytest.raises(ValueError, match="token-bucket"):
        get_algorithm("leaky-bucket")
