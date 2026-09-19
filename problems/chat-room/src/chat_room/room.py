"""Mediator: the room, which is the only thing that knows who is in it."""

from __future__ import annotations

import time
from collections.abc import Callable

from .message import Delivery, Message, MessageType
from .user import User


class NotInRoom(Exception):
    """The user is not a member of this room."""


class Moderated(Exception):
    """The room refused the message."""


class ChatRoom:
    """Routes messages between members, who never address each other directly.

    This is where Mediator differs from Observer, and the difference is worth
    stating plainly:

    - **Observer** is one-to-many notification. The subject broadcasts; it does
      not decide who gets what, and it has no opinion about the content.
    - **Mediator** is many-to-many coordination, and it *has logic*. This room
      checks membership, applies blocks, enforces moderation, skips the sender,
      and holds the transcript. None of that belongs on a Subject.

    Every rule below lives here for the same reason: it concerns a relationship
    between two participants, and neither participant should own it.
    """

    def __init__(
        self,
        name: str,
        history_limit: int = 500,
        clock: Callable[[], float] = time.time,
    ):
        self.name = name
        self.history_limit = history_limit
        self.clock = clock

        self._members: dict[str, User] = {}
        self.history: list[Message] = []
        #: Words the room rejects outright. A stand-in for real moderation.
        self.banned_words: set[str] = set()
        self._muted: set[str] = set()

    # -- membership -------------------------------------------------------

    def join(self, user: User) -> Delivery:
        if user.name in self._members:
            raise ValueError(f"{user.name} is already in {self.name}")

        self._members[user.name] = user
        user._rooms.append(self)

        # The joiner sees the backlog but not their own arrival notice, which
        # is the ordering every chat client uses.
        self._replay_history(user)
        return self._announce(f"{user.name} joined {self.name}", exclude=user.name)

    def leave(self, user: User) -> Delivery:
        if user.name not in self._members:
            raise NotInRoom(f"{user.name} is not in {self.name}")

        del self._members[user.name]
        if self in user._rooms:
            user._rooms.remove(self)

        return self._announce(f"{user.name} left {self.name}")

    @property
    def members(self) -> list[str]:
        return sorted(self._members)

    @property
    def online_members(self) -> list[str]:
        return sorted(name for name, user in self._members.items() if user.online)

    def __contains__(self, name: str) -> bool:
        return name in self._members

    def __len__(self) -> int:
        return len(self._members)

    # -- moderation -------------------------------------------------------

    def mute(self, name: str) -> None:
        self._muted.add(name)

    def unmute(self, name: str) -> None:
        self._muted.discard(name)

    def ban_word(self, word: str) -> None:
        self.banned_words.add(word.lower())

    # -- sending ----------------------------------------------------------

    def send(self, sender: User, body: str) -> Delivery:
        """Broadcast to everyone else in the room."""
        self._require_member(sender)

        message = Message(sender.name, body, MessageType.CHAT, timestamp=self.clock())
        refusal = self._refuse(sender, message)
        if refusal is not None:
            return refusal

        self._record(message)
        return self._fan_out(message, exclude=sender.name)

    def send_direct(self, sender: User, recipient: str, body: str) -> Delivery:
        """Send to one member. Still routed by the room, never user to user."""
        self._require_member(sender)

        if recipient not in self._members:
            raise NotInRoom(f"{recipient} is not in {self.name}")

        message = Message(
            sender.name, body, MessageType.DIRECT, recipient=recipient, timestamp=self.clock()
        )
        refusal = self._refuse(sender, message)
        if refusal is not None:
            return refusal

        # Direct messages stay out of the room transcript. Putting them in is a
        # privacy bug, and an easy one to ship, since every other path records.
        target = self._members[recipient]
        if target.has_blocked(sender.name):
            return Delivery(message, withheld_from=(recipient,), reason=f"{recipient} blocked you")

        target.receive(message)
        return Delivery(message, delivered_to=(recipient,))

    def _refuse(self, sender: User, message: Message) -> Delivery | None:
        if sender.name in self._muted:
            return Delivery(message, reason=f"{sender.name} is muted in {self.name}")

        lowered = message.body.lower()
        hit = next((word for word in self.banned_words if word in lowered), None)
        if hit is not None:
            return Delivery(message, reason=f"message blocked ({hit!r} is not allowed here)")

        return None

    def _fan_out(self, message: Message, exclude: str | None = None) -> Delivery:
        delivered, withheld = [], []

        for name, member in self._members.items():
            if name == exclude:
                continue
            if member.has_blocked(message.sender):
                # The block belongs to the recipient, but only the room is in a
                # position to apply it -- the sender must not learn who blocked
                # them, and the recipient never sees the message at all.
                withheld.append(name)
                continue

            member.receive(message)
            delivered.append(name)

        return Delivery(message, tuple(sorted(delivered)), tuple(sorted(withheld)))

    def _announce(self, body: str, exclude: str | None = None) -> Delivery:
        message = Message("system", body, MessageType.SYSTEM, timestamp=self.clock())
        self._record(message)
        return self._fan_out(message, exclude=exclude)

    def _record(self, message: Message) -> None:
        self.history.append(message)
        if len(self.history) > self.history_limit:
            del self.history[: len(self.history) - self.history_limit]

    def _replay_history(self, user: User) -> None:
        for message in self.history:
            user.receive(message)

    def _require_member(self, user: User) -> None:
        if user.name not in self._members:
            raise NotInRoom(f"{user.name} is not in {self.name}")

    def transcript(self) -> list[str]:
        return [message.render() for message in self.history]

    def __repr__(self) -> str:
        return f"ChatRoom({self.name!r}, {len(self._members)} members)"
