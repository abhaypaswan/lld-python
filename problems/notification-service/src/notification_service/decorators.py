"""Decorator: cross-cutting delivery behaviour, wrapped around any channel.

Retrying, rate limiting and deduplication apply equally to email, SMS, push and
Slack. Putting them in the channels means four copies of each; putting them in
the service means every channel gets the same policy whether it suits it or not.

As decorators, each is written once and composes with any channel and with each
other:

    RetryingChannel(RateLimitedChannel(EmailChannel(), ...), attempts=3)

Every decorator is itself a Channel, which is what makes the stacking work --
the thing being wrapped and the wrapper are the same type all the way down.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable

from .channels import Channel, DeliveryError
from .notification import DeliveryResult, Notification


class ChannelDecorator(Channel):
    """Base: forwards everything to the wrapped channel by default."""

    def __init__(self, inner: Channel):
        self.inner = inner

    @property
    def name(self) -> str:
        return self.inner.name

    def supports(self, notification: Notification) -> bool:
        return self.inner.supports(notification)

    def send(self, notification: Notification) -> DeliveryResult:
        return self.inner.send(notification)

    def unwrap(self) -> Channel:
        """The channel at the bottom of the stack."""
        channel = self.inner
        while isinstance(channel, ChannelDecorator):
            channel = channel.inner
        return channel


class RetryingChannel(ChannelDecorator):
    """Retries a failed send, backing off between attempts.

    Backoff is exponential, and `sleep` is injected so the tests do not
    actually wait. A retry decorator that calls time.sleep directly turns a
    fast suite into a slow one and usually ends up untested.
    """

    def __init__(
        self,
        inner: Channel,
        attempts: int = 3,
        backoff: float = 0.1,
        sleep: Callable[[float], None] = time.sleep,
    ):
        super().__init__(inner)
        if attempts < 1:
            raise ValueError(f"attempts must be at least 1, got {attempts}")

        self.attempts = attempts
        self.backoff = backoff
        self.sleep = sleep

    def send(self, notification: Notification) -> DeliveryResult:
        last_error = ""

        for attempt in range(1, self.attempts + 1):
            try:
                result = self.inner.send(notification)
            except DeliveryError as exc:
                last_error = str(exc)
            else:
                if result.delivered:
                    return DeliveryResult(
                        notification, result.channel, True, result.detail, attempts=attempt
                    )
                if not result.retryable:
                    # Suppressed on purpose -- a duplicate, or over a rate
                    # limit. Retrying cannot change the answer, so hand the
                    # reason straight back rather than burning the attempts.
                    return result
                last_error = result.detail

            if attempt < self.attempts:
                self.sleep(self.backoff * (2 ** (attempt - 1)))

        return DeliveryResult(
            notification, self.name, False, f"gave up after {self.attempts}: {last_error}",
            attempts=self.attempts,
        )


class RateLimitedChannel(ChannelDecorator):
    """Caps how many notifications one recipient gets per window.

    Per recipient rather than globally, because the thing being protected is
    the person, not the transport. A global cap would let one noisy recipient
    starve everyone else.
    """

    def __init__(
        self,
        inner: Channel,
        limit: int,
        window: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        super().__init__(inner)
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")

        self.limit = limit
        self.window = window
        self.clock = clock
        self._history: dict[str, deque[float]] = {}

    def send(self, notification: Notification) -> DeliveryResult:
        now = self.clock()
        recent = self._history.setdefault(notification.recipient, deque())

        while recent and recent[0] <= now - self.window:
            recent.popleft()

        if len(recent) >= self.limit:
            return DeliveryResult(
                notification, self.name, False,
                f"rate limited: {self.limit} per {self.window:g}s for {notification.recipient}",
                retryable=False,
            )

        result = self.inner.send(notification)
        if result.delivered:
            # Only successful sends count against the budget. Counting failures
            # would let an outage burn through a recipient's quota.
            recent.append(now)
        return result


class DeduplicatingChannel(ChannelDecorator):
    """Drops a notification already sent recently under the same key.

    This is what stops a flapping alert sending forty identical emails. The key
    defaults to recipient plus subject, so the common case needs no
    configuration.
    """

    def __init__(
        self,
        inner: Channel,
        window: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ):
        super().__init__(inner)
        self.window = window
        self.clock = clock
        self._seen: dict[str, float] = {}

    def send(self, notification: Notification) -> DeliveryResult:
        now = self.clock()
        last_sent = self._seen.get(notification.dedupe_key)

        if last_sent is not None and now - last_sent < self.window:
            return DeliveryResult(
                notification, self.name, False,
                f"duplicate of a notification sent {now - last_sent:.0f}s ago",
                retryable=False,
            )

        result = self.inner.send(notification)
        if result.delivered:
            self._seen[notification.dedupe_key] = now
        return result


class RecordingChannel(ChannelDecorator):
    """Keeps every result. An audit log, and what the tests assert against."""

    def __init__(self, inner: Channel):
        super().__init__(inner)
        self.results: list[DeliveryResult] = []

    def send(self, notification: Notification) -> DeliveryResult:
        result = self.inner.send(notification)
        self.results.append(result)
        return result

    @property
    def delivered(self) -> list[DeliveryResult]:
        return [r for r in self.results if r.delivered]

    @property
    def failed(self) -> list[DeliveryResult]:
        return [r for r in self.results if not r.delivered]
