"""A participant. Holds no reference to any other participant."""

from __future__ import annotations

from .message import Message


class User:
    """A colleague, in Mediator terms.

    The thing to notice is what is *absent*: no list of peers, no `send_to`
    taking another User. A user talks to the room and the room decides who
    hears it.

    That is the whole pattern. With direct references, ten users in a room is
    ninety references to keep correct as people join and leave; with a
    mediator it is ten.
    """

    def __init__(self, name: str):
        if not name.strip():
            raise ValueError("A user needs a name")

        self.name = name.strip()
        self.inbox: list[Message] = []
        #: Names this user has blocked. Stored here, enforced by the room --
        #: the user states the preference, the mediator applies it.
        self.blocked: set[str] = set()
        self.online = True
        #: Rooms this user is in. A back-reference to the mediator is fine;
        #: a reference to another colleague is not.
        self._rooms: list = []

    # -- talking ----------------------------------------------------------

    def send(self, room, body: str):
        """Say something to a room."""
        return room.send(self, body)

    def whisper(self, room, recipient: str, body: str):
        """Say something to one person in a room."""
        return room.send_direct(self, recipient, body)

    def receive(self, message: Message) -> None:
        """Called by the room. Never called by another user."""
        self.inbox.append(message)

    # -- preferences ------------------------------------------------------

    def block(self, name: str) -> None:
        if name == self.name:
            raise ValueError("You cannot block yourself")
        self.blocked.add(name)

    def unblock(self, name: str) -> None:
        self.blocked.discard(name)

    def has_blocked(self, name: str) -> bool:
        return name in self.blocked

    def go_offline(self) -> None:
        self.online = False

    def go_online(self) -> None:
        self.online = True

    # -- reading ----------------------------------------------------------

    @property
    def rooms(self) -> list[str]:
        return sorted(room.name for room in self._rooms)

    def unread(self) -> list[Message]:
        return list(self.inbox)

    def transcript(self) -> list[str]:
        return [message.render() for message in self.inbox]

    def __repr__(self) -> str:
        return f"User({self.name!r})"
