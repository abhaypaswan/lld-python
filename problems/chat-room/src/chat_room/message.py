"""What travels through a room."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum

_ids = itertools.count(1)


class MessageType(Enum):
    CHAT = "chat"
    DIRECT = "direct"
    SYSTEM = "system"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Message:
    """One message. Frozen, because a delivered message is a historical fact.

    `sender` is a name rather than a User reference, and that is the point of
    the whole design: a message carries no way to reach back to the object that
    sent it. Routing is the room's job.
    """

    sender: str
    body: str
    message_type: MessageType = MessageType.CHAT
    recipient: str | None = None
    timestamp: float = 0.0
    message_id: str = field(default="")

    def __post_init__(self):
        if not self.body.strip():
            raise ValueError("A message cannot be empty")
        if self.message_type is MessageType.DIRECT and not self.recipient:
            raise ValueError("A direct message needs a recipient")

        if not self.message_id:
            object.__setattr__(self, "message_id", f"M-{next(_ids):05d}")

    def render(self) -> str:
        if self.message_type is MessageType.SYSTEM:
            return f"* {self.body}"
        if self.message_type is MessageType.DIRECT:
            return f"[{self.sender} → {self.recipient}] {self.body}"
        return f"<{self.sender}> {self.body}"

    def __str__(self) -> str:
        return self.render()


@dataclass(frozen=True)
class Delivery:
    """What happened to one message in one room.

    Returned rather than swallowed, so a caller can see that a message reached
    four people and was withheld from two -- and why. A send that silently
    does nothing is the hardest kind of chat bug to diagnose.
    """

    message: Message
    delivered_to: tuple[str, ...] = ()
    withheld_from: tuple[str, ...] = ()
    reason: str = ""

    @property
    def reach(self) -> int:
        return len(self.delivered_to)

    def __bool__(self) -> bool:
        return bool(self.delivered_to)

    def __str__(self) -> str:
        if not self.delivered_to:
            return f"not delivered ({self.reason})" if self.reason else "not delivered"
        text = f"delivered to {len(self.delivered_to)}"
        if self.withheld_from:
            text += f", withheld from {len(self.withheld_from)}"
        return text
