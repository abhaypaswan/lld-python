"""The real delivery mechanisms.

Each channel does one thing: hand a notification to a transport. No retrying,
no rate limiting, no deduplication -- those are decorators, and keeping them out
of here is what lets any of them apply to any channel.

The transport itself is injected. In production that is an SMTP client or a
vendor SDK; in the tests it is a list. A channel that constructs its own
transport can only be tested by standing that transport up.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from .notification import DeliveryResult, Notification


class DeliveryError(Exception):
    """The transport refused or failed. Retrying may help."""


class Channel(ABC):
    """One way of reaching someone."""

    name: str = "channel"

    @abstractmethod
    def send(self, notification: Notification) -> DeliveryResult:
        """Attempt delivery once. Raises DeliveryError on a retryable failure."""

    def supports(self, notification: Notification) -> bool:
        """Whether this channel can carry this notification at all."""
        return True

    def _ok(self, notification: Notification, detail: str = "") -> DeliveryResult:
        return DeliveryResult(notification, self.name, True, detail)


class _TransportChannel(Channel):
    """Shared plumbing for the channels that just hand off to a transport."""

    def __init__(self, transport: Callable[[Notification], None] | None = None):
        self.transport = transport if transport is not None else self._default_transport
        self.sent: list[Notification] = []

    def _default_transport(self, notification: Notification) -> None:
        """Stands in for a real client so the demo runs with no credentials."""
        print(f"  [{self.name}] {notification.subject} -> {notification.recipient}")

    def send(self, notification: Notification) -> DeliveryResult:
        self.transport(notification)
        self.sent.append(notification)
        return self._ok(notification)


class EmailChannel(_TransportChannel):
    name = "email"

    def supports(self, notification: Notification) -> bool:
        return "@" in notification.recipient


class SMSChannel(_TransportChannel):
    """Texts. Length-limited, which is a real constraint and not a detail."""

    name = "sms"
    max_length = 160

    def supports(self, notification: Notification) -> bool:
        return notification.recipient.replace("+", "").replace("-", "").isdigit()

    def send(self, notification: Notification) -> DeliveryResult:
        text = f"{notification.subject} {notification.body}".strip()
        if len(text) > self.max_length:
            # Truncating is a product decision, so it is visible in the result
            # rather than happening silently.
            text = text[: self.max_length - 1] + "…"

        self.transport(notification)
        self.sent.append(notification)
        return self._ok(notification, f"{len(text)} chars")


class PushChannel(_TransportChannel):
    name = "push"


class SlackChannel(_TransportChannel):
    name = "slack"

    def supports(self, notification: Notification) -> bool:
        return notification.recipient.startswith(("#", "@"))


CHANNELS: dict[str, type[Channel]] = {
    EmailChannel.name: EmailChannel,
    SMSChannel.name: SMSChannel,
    PushChannel.name: PushChannel,
    SlackChannel.name: SlackChannel,
}


def get_channel(name: str, **kwargs) -> Channel:
    """Factory: build a channel by name."""
    try:
        return CHANNELS[name](**kwargs)
    except KeyError:
        known = ", ".join(sorted(CHANNELS))
        raise ValueError(f"{name!r} is not a channel. Try one of: {known}") from None
