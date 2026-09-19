"""The service: who wants what, over which channels."""

from __future__ import annotations

from dataclasses import dataclass, field

from .channels import Channel
from .notification import DeliveryResult, Notification, Priority


@dataclass
class Subscriber:
    """One person, and how they want to be reached.

    `minimum_priority` is per channel, not per person. That is the difference
    between a useful notification system and one people mute: the same user can
    want everything by email and only urgent things by SMS.
    """

    user_id: str
    #: channel name -> the address to use on that channel
    addresses: dict[str, str] = field(default_factory=dict)
    #: channel name -> the lowest priority worth sending there
    minimum_priority: dict[str, Priority] = field(default_factory=dict)
    muted: bool = False

    def wants(self, channel_name: str, priority: Priority) -> bool:
        if self.muted or channel_name not in self.addresses:
            return False
        return priority >= self.minimum_priority.get(channel_name, Priority.LOW)

    def address_for(self, channel_name: str) -> str | None:
        return self.addresses.get(channel_name)


class NotificationService:
    """Fans a notification out to whichever channels a subscriber wants.

    Observer, in the sense that matters: the service holds subscribers and
    announces to them without knowing who they are. Adding a recipient is
    registration, not a code change.
    """

    def __init__(self):
        self.channels: dict[str, Channel] = {}
        self.subscribers: dict[str, Subscriber] = {}
        self._listeners: list = []

    # -- registration -----------------------------------------------------

    def register_channel(self, channel: Channel) -> Channel:
        self.channels[channel.name] = channel
        return channel

    def subscribe(self, subscriber: Subscriber) -> Subscriber:
        self.subscribers[subscriber.user_id] = subscriber
        return subscriber

    def on_delivery(self, listener) -> None:
        """Called with every DeliveryResult, delivered or not."""
        self._listeners.append(listener)

    # -- sending ----------------------------------------------------------

    def notify(
        self,
        user_id: str,
        subject: str,
        body: str = "",
        priority: Priority = Priority.NORMAL,
        channels: list[str] | None = None,
        **metadata,
    ) -> list[DeliveryResult]:
        """Send to one subscriber over every channel they want it on."""
        subscriber = self.subscribers.get(user_id)
        if subscriber is None:
            raise KeyError(f"No subscriber {user_id!r}")

        wanted = channels if channels is not None else list(self.channels)
        results = []

        for channel_name in wanted:
            channel = self.channels.get(channel_name)
            if channel is None:
                raise KeyError(f"No channel {channel_name!r} is registered")

            if not subscriber.wants(channel_name, priority):
                continue

            notification = Notification(
                recipient=subscriber.address_for(channel_name),
                subject=subject,
                body=body,
                priority=priority,
                metadata=metadata,
            )

            if not channel.supports(notification):
                results.append(
                    DeliveryResult(
                        notification,
                        channel_name,
                        False,
                        f"{notification.recipient} is not a valid {channel_name} address",
                    )
                )
            else:
                results.append(channel.send(notification))

            for listener in self._listeners:
                listener(results[-1])

        return results

    def broadcast(
        self, subject: str, body: str = "", priority: Priority = Priority.NORMAL, **metadata
    ) -> dict[str, list[DeliveryResult]]:
        """Send to everyone subscribed."""
        return {
            user_id: self.notify(user_id, subject, body, priority, **metadata)
            for user_id in self.subscribers
        }
