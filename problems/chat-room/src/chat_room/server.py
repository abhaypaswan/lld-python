"""The server: rooms and registered users, one level up.

A second mediator, over rooms rather than over users. It exists so that a user
can be looked up, moved between rooms, or messaged across them without any room
holding a reference to another room.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from .message import Delivery
from .room import ChatRoom
from .user import User


class ChatServer:
    """Holds the users and the rooms, and nothing holds it."""

    def __init__(self, clock: Callable[[], float] = time.time):
        self.clock = clock
        self._users: dict[str, User] = {}
        self._rooms: dict[str, ChatRoom] = {}

    # -- registry ---------------------------------------------------------

    def register(self, name: str) -> User:
        if name in self._users:
            raise ValueError(f"{name} is already registered")

        user = User(name)
        self._users[user.name] = user
        return user

    def user(self, name: str) -> User:
        found = self._users.get(name)
        if found is None:
            known = ", ".join(sorted(self._users)) or "(nobody)"
            raise KeyError(f"No user {name!r}. Registered: {known}")
        return found

    def create_room(self, name: str, **kwargs) -> ChatRoom:
        if name in self._rooms:
            raise ValueError(f"Room {name} already exists")

        room = ChatRoom(name, clock=self.clock, **kwargs)
        self._rooms[name] = room
        return room

    def room(self, name: str) -> ChatRoom:
        found = self._rooms.get(name)
        if found is None:
            known = ", ".join(sorted(self._rooms)) or "(none)"
            raise KeyError(f"No room {name!r}. Rooms: {known}")
        return found

    @property
    def rooms(self) -> list[str]:
        return sorted(self._rooms)

    @property
    def users(self) -> list[str]:
        return sorted(self._users)

    # -- convenience ------------------------------------------------------

    def join(self, user_name: str, room_name: str) -> Delivery:
        return self.room(room_name).join(self.user(user_name))

    def broadcast(self, body: str) -> dict[str, Delivery]:
        """A server-wide announcement, room by room."""
        return {name: room._announce(body) for name, room in self._rooms.items()}

    def where_is(self, user_name: str) -> list[str]:
        return self.user(user_name).rooms
