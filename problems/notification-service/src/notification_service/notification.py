"""What gets sent, and what comes back."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import IntEnum

_ids = itertools.count(1)


class Priority(IntEnum):
    """An IntEnum so priorities can be compared and sorted."""

    LOW = 10
    NORMAL = 20
    HIGH = 30
    URGENT = 40

    def __str__(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Notification:
    """One message, before anyone has decided how to deliver it.

    Frozen, and channel-agnostic on purpose. The same notification may go out
    over email and push at once; baking a channel into it would mean building
    it twice and letting the two copies drift.

    `dedupe_key` is what DeduplicatingChannel collapses on. Defaulting it to
    the recipient plus subject means "the same alert to the same person" is
    deduplicated by default without the caller doing anything.
    """

    recipient: str
    subject: str
    body: str = ""
    priority: Priority = Priority.NORMAL
    notification_id: str = ""
    dedupe_key: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.recipient.strip():
            raise ValueError("A notification needs a recipient")
        if not self.subject.strip():
            raise ValueError("A notification needs a subject")

        if not self.notification_id:
            object.__setattr__(self, "notification_id", f"N-{next(_ids):05d}")
        if not self.dedupe_key:
            object.__setattr__(self, "dedupe_key", f"{self.recipient}:{self.subject}")

    def __str__(self) -> str:
        return f"[{self.priority}] {self.subject} -> {self.recipient}"


@dataclass(frozen=True)
class DeliveryResult:
    """The outcome of one attempt at one channel."""

    notification: Notification
    channel: str
    delivered: bool
    detail: str = ""
    attempts: int = 1
    #: Whether trying again could plausibly succeed. A transport that timed out
    #: is retryable; a notification suppressed as a duplicate or by a rate limit
    #: is not -- it was suppressed on purpose, and retrying it just burns
    #: attempts to arrive at the same answer.
    retryable: bool = True

    def __bool__(self) -> bool:
        return self.delivered

    @property
    def suppressed(self) -> bool:
        """Deliberately not sent, as opposed to failed to send."""
        return not self.delivered and not self.retryable

    def __str__(self) -> str:
        verb = "delivered" if self.delivered else ("suppressed" if self.suppressed else "failed")
        tries = f" after {self.attempts} attempts" if self.attempts > 1 else ""
        return f"{self.channel}: {verb}{tries}" + (f" ({self.detail})" if self.detail else "")
