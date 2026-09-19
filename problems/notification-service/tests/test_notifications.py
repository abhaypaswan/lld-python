"""Channels, the decorators around them, and what stacking order does."""

import pytest

from notification_service import (
    Channel,
    DeduplicatingChannel,
    EmailChannel,
    Notification,
    NotificationService,
    Priority,
    PushChannel,
    RateLimitedChannel,
    RecordingChannel,
    RetryingChannel,
    SlackChannel,
    SMSChannel,
    Subscriber,
)
from notification_service.channels import DeliveryError, get_channel
from notification_service.notification import DeliveryResult


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FlakyChannel(Channel):
    """Fails a set number of times, then succeeds."""

    name = "flaky"

    def __init__(self, failures: int = 0, always_fail: bool = False):
        self.failures = failures
        self.always_fail = always_fail
        self.calls = 0

    def send(self, notification):
        self.calls += 1
        if self.always_fail or self.calls <= self.failures:
            raise DeliveryError(f"transport down (call {self.calls})")
        return DeliveryResult(notification, self.name, True)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def note():
    return Notification("alice@example.com", "Deploy finished")


@pytest.fixture
def no_sleep():
    return lambda _: None


# -- notifications --------------------------------------------------------


def test_a_notification_gets_an_id(note):
    assert note.notification_id.startswith("N-")


def test_the_dedupe_key_defaults_to_recipient_and_subject(note):
    assert note.dedupe_key == "alice@example.com:Deploy finished"


def test_a_notification_needs_a_recipient():
    with pytest.raises(ValueError, match="needs a recipient"):
        Notification("", "Subject")


def test_a_notification_needs_a_subject():
    with pytest.raises(ValueError, match="needs a subject"):
        Notification("alice@example.com", "  ")


def test_priorities_compare():
    assert Priority.LOW < Priority.NORMAL < Priority.HIGH < Priority.URGENT


# -- channels -------------------------------------------------------------


def test_email_only_accepts_addresses_with_an_at_sign():
    channel = EmailChannel(transport=lambda n: None)

    assert channel.supports(Notification("alice@example.com", "Hi"))
    assert not channel.supports(Notification("+15551234", "Hi"))


def test_sms_only_accepts_phone_numbers():
    channel = SMSChannel(transport=lambda n: None)

    assert channel.supports(Notification("+1-555-1234", "Hi"))
    assert not channel.supports(Notification("alice@example.com", "Hi"))


def test_slack_only_accepts_channels_and_handles():
    channel = SlackChannel(transport=lambda n: None)

    assert channel.supports(Notification("#alerts", "Hi"))
    assert not channel.supports(Notification("alerts", "Hi"))


def test_sms_reports_truncation_rather_than_doing_it_silently():
    channel = SMSChannel(transport=lambda n: None)
    long_note = Notification("+15551234", "Alert", "x" * 300)

    assert "160 chars" in channel.send(long_note).detail


def test_an_unknown_channel_lists_the_known_ones():
    with pytest.raises(ValueError, match="email, push"):
        get_channel("carrier-pigeon")


# -- retry ----------------------------------------------------------------


def test_a_transient_failure_is_retried(no_sleep):
    flaky = FlakyChannel(failures=2)
    channel = RetryingChannel(flaky, attempts=3, sleep=no_sleep)

    result = channel.send(Notification("alice@example.com", "Hi"))

    assert result.delivered
    assert result.attempts == 3


def test_retrying_gives_up_after_the_last_attempt(no_sleep):
    flaky = FlakyChannel(always_fail=True)
    channel = RetryingChannel(flaky, attempts=3, sleep=no_sleep)

    result = channel.send(Notification("alice@example.com", "Hi"))

    assert not result.delivered
    assert "gave up after 3" in result.detail
    assert flaky.calls == 3, "it must not keep trying forever"


def test_a_first_time_success_is_not_retried(no_sleep):
    flaky = FlakyChannel(failures=0)
    RetryingChannel(flaky, attempts=3, sleep=no_sleep).send(
        Notification("alice@example.com", "Hi")
    )

    assert flaky.calls == 1


def test_backoff_grows_between_attempts():
    waits = []
    RetryingChannel(
        FlakyChannel(always_fail=True), attempts=4, backoff=1.0, sleep=waits.append
    ).send(Notification("alice@example.com", "Hi"))

    assert waits == [1.0, 2.0, 4.0]


def test_retrying_needs_at_least_one_attempt():
    with pytest.raises(ValueError, match="at least 1"):
        RetryingChannel(FlakyChannel(), attempts=0)


# -- rate limiting --------------------------------------------------------


def test_rate_limiting_stops_the_flood(clock):
    inner = EmailChannel(transport=lambda n: None)
    channel = RateLimitedChannel(inner, limit=2, window=60, clock=clock)
    note = Notification("alice@example.com", "Hi")

    assert channel.send(note).delivered
    assert channel.send(note).delivered
    assert not channel.send(note).delivered
    assert len(inner.sent) == 2


def test_the_budget_returns_after_the_window(clock):
    channel = RateLimitedChannel(
        EmailChannel(transport=lambda n: None), limit=1, window=60, clock=clock
    )
    note = Notification("alice@example.com", "Hi")
    channel.send(note)

    clock.advance(61)

    assert channel.send(note).delivered


def test_one_noisy_recipient_does_not_starve_the_others(clock):
    channel = RateLimitedChannel(
        EmailChannel(transport=lambda n: None), limit=1, window=60, clock=clock
    )
    channel.send(Notification("alice@example.com", "Hi"))

    assert channel.send(Notification("bob@example.com", "Hi")).delivered


def test_a_failed_send_does_not_burn_the_budget(clock, no_sleep):
    """An outage must not consume a recipient's quota."""
    channel = RateLimitedChannel(
        FlakyChannel(always_fail=True), limit=2, window=60, clock=clock
    )
    channel = RetryingChannel(channel, attempts=1, sleep=no_sleep)
    note = Notification("alice@example.com", "Hi")

    for _ in range(5):
        channel.send(note)

    inner = channel.inner
    assert len(inner._history.get("alice@example.com", [])) == 0


# -- deduplication --------------------------------------------------------


def test_the_same_alert_twice_is_sent_once(clock):
    inner = EmailChannel(transport=lambda n: None)
    channel = DeduplicatingChannel(inner, window=300, clock=clock)

    channel.send(Notification("alice@example.com", "Disk full"))
    result = channel.send(Notification("alice@example.com", "Disk full"))

    assert not result.delivered
    assert "duplicate" in result.detail
    assert len(inner.sent) == 1


def test_a_different_subject_is_not_a_duplicate(clock):
    inner = EmailChannel(transport=lambda n: None)
    channel = DeduplicatingChannel(inner, window=300, clock=clock)

    channel.send(Notification("alice@example.com", "Disk full"))
    channel.send(Notification("alice@example.com", "Disk recovered"))

    assert len(inner.sent) == 2


def test_the_same_subject_to_someone_else_is_not_a_duplicate(clock):
    inner = EmailChannel(transport=lambda n: None)
    channel = DeduplicatingChannel(inner, window=300, clock=clock)

    channel.send(Notification("alice@example.com", "Disk full"))
    channel.send(Notification("bob@example.com", "Disk full"))

    assert len(inner.sent) == 2


def test_the_duplicate_window_expires(clock):
    inner = EmailChannel(transport=lambda n: None)
    channel = DeduplicatingChannel(inner, window=300, clock=clock)
    channel.send(Notification("alice@example.com", "Disk full"))

    clock.advance(301)
    channel.send(Notification("alice@example.com", "Disk full"))

    assert len(inner.sent) == 2


# -- stacking -------------------------------------------------------------


def test_decorators_compose(clock, no_sleep):
    inner = EmailChannel(transport=lambda n: None)
    channel = RetryingChannel(
        RateLimitedChannel(
            DeduplicatingChannel(inner, window=300, clock=clock),
            limit=5, window=60, clock=clock,
        ),
        attempts=2, sleep=no_sleep,
    )

    channel.send(Notification("alice@example.com", "Hi"))
    channel.send(Notification("alice@example.com", "Hi"))

    assert len(inner.sent) == 1, "dedup still applies through two other wrappers"


def test_a_decorator_keeps_the_wrapped_channels_identity(clock):
    channel = RetryingChannel(RateLimitedChannel(EmailChannel(), 5, 60, clock=clock))

    assert channel.name == "email"
    assert isinstance(channel.unwrap(), EmailChannel)


def test_order_matters_retry_outside_the_limiter(clock, no_sleep):
    """Retrying outside the limiter means each retry is re-checked against it."""
    flaky = FlakyChannel(failures=2)
    limited = RateLimitedChannel(flaky, limit=1, window=60, clock=clock)
    channel = RetryingChannel(limited, attempts=3, sleep=no_sleep)

    result = channel.send(Notification("alice@example.com", "Hi"))

    assert result.delivered
    assert flaky.calls == 3


def test_order_matters_retry_inside_the_limiter(clock, no_sleep):
    """Retrying inside means the limiter sees one send, not three attempts."""
    flaky = FlakyChannel(failures=2)
    retried = RetryingChannel(flaky, attempts=3, sleep=no_sleep)
    channel = RateLimitedChannel(retried, limit=1, window=60, clock=clock)

    assert channel.send(Notification("alice@example.com", "Hi")).delivered
    # The single logical send used the whole budget, retries included.
    assert not channel.send(Notification("alice@example.com", "Hi")).delivered


# -- the service ----------------------------------------------------------


@pytest.fixture
def service():
    svc = NotificationService()
    svc.register_channel(EmailChannel(transport=lambda n: None))
    svc.register_channel(SMSChannel(transport=lambda n: None))
    svc.register_channel(PushChannel(transport=lambda n: None))
    return svc


@pytest.fixture
def alice(service):
    return service.subscribe(
        Subscriber(
            "alice",
            addresses={"email": "alice@example.com", "sms": "+15551234", "push": "device-1"},
            minimum_priority={"sms": Priority.URGENT},
        )
    )


def test_a_notification_goes_to_every_channel_the_user_wants(service, alice):
    results = service.notify("alice", "Deploy finished")

    assert {r.channel for r in results} == {"email", "push"}


def test_a_per_channel_threshold_is_respected(service, alice):
    results = service.notify("alice", "Everything is on fire", priority=Priority.URGENT)

    assert "sms" in {r.channel for r in results}


def test_a_muted_subscriber_gets_nothing(service, alice):
    alice.muted = True

    assert service.notify("alice", "Deploy finished", priority=Priority.URGENT) == []


def test_a_caller_can_name_the_channels(service, alice):
    results = service.notify("alice", "Deploy finished", channels=["email"])

    assert [r.channel for r in results] == ["email"]


def test_an_address_a_channel_cannot_use_fails_cleanly(service):
    service.subscribe(Subscriber("bob", addresses={"email": "not-an-email"}))

    result = service.notify("bob", "Hi")[0]

    assert not result.delivered
    assert "not a valid email address" in result.detail


def test_an_unknown_subscriber_is_an_error(service):
    with pytest.raises(KeyError, match="No subscriber"):
        service.notify("nobody", "Hi")


def test_an_unregistered_channel_is_an_error(service, alice):
    with pytest.raises(KeyError, match="No channel 'fax'"):
        service.notify("alice", "Hi", channels=["fax"])


def test_listeners_hear_about_every_delivery(service, alice):
    seen = []
    service.on_delivery(seen.append)

    service.notify("alice", "Deploy finished")

    assert len(seen) == 2


def test_broadcast_reaches_everyone(service, alice):
    service.subscribe(Subscriber("bob", addresses={"email": "bob@example.com"}))

    results = service.broadcast("Maintenance tonight")

    assert set(results) == {"alice", "bob"}


def test_the_recording_channel_separates_wins_from_losses(clock):
    recorder = RecordingChannel(
        DeduplicatingChannel(EmailChannel(transport=lambda n: None), clock=clock)
    )
    recorder.send(Notification("alice@example.com", "Hi"))
    recorder.send(Notification("alice@example.com", "Hi"))

    assert len(recorder.delivered) == 1
    assert len(recorder.failed) == 1


# -- suppressed is not the same as failed ---------------------------------


def test_a_duplicate_is_suppressed_not_failed(clock):
    channel = DeduplicatingChannel(EmailChannel(transport=lambda n: None), clock=clock)
    note = Notification("alice@example.com", "Hi")
    channel.send(note)

    result = channel.send(note)

    assert result.suppressed
    assert not result.retryable


def test_a_rate_limited_send_is_suppressed_not_failed(clock):
    channel = RateLimitedChannel(
        EmailChannel(transport=lambda n: None), limit=1, window=60, clock=clock
    )
    note = Notification("alice@example.com", "Hi")
    channel.send(note)

    assert channel.send(note).suppressed


def test_a_transport_failure_is_retryable_not_suppressed(no_sleep):
    result = RetryingChannel(
        FlakyChannel(always_fail=True), attempts=1, sleep=no_sleep
    ).send(Notification("alice@example.com", "Hi"))

    assert not result.suppressed


def test_retry_does_not_re_attempt_a_deliberate_suppression(clock, no_sleep):
    """Retrying a duplicate burns attempts to arrive at the same answer."""
    inner = EmailChannel(transport=lambda n: None)
    counted = RecordingChannel(inner)
    channel = RetryingChannel(
        DeduplicatingChannel(counted, window=300, clock=clock), attempts=3, sleep=no_sleep
    )
    note = Notification("alice@example.com", "Hi")
    channel.send(note)

    result = channel.send(note)

    assert result.attempts == 1, "a suppressed send must not be retried"
    assert len(counted.results) == 1


def test_retry_still_retries_a_genuine_failure(no_sleep):
    flaky = FlakyChannel(failures=2)

    assert RetryingChannel(flaky, attempts=3, sleep=no_sleep).send(
        Notification("alice@example.com", "Hi")
    ).delivered
    assert flaky.calls == 3
