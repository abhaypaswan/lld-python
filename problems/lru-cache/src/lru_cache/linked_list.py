"""A doubly linked list with sentinels, which is what makes LRU O(1).

This is the data structure the problem is really about. A plain list gives you
O(n) removal from the middle; an OrderedDict hides the mechanism behind a
built-in. Writing the list out is the point of the exercise, and the sentinel
nodes are what remove every null check from the pointer surgery.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


class Node:
    """One entry. Holds its key so eviction can find the map entry to delete."""

    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: Any = None, value: Any = None):
        self.key = key
        self.value = value
        self.prev: Node | None = None
        self.next: Node | None = None

    def __repr__(self) -> str:
        return f"Node({self.key!r}, {self.value!r})"


class DoublyLinkedList:
    """Ordered from most recent at the head to least recent at the tail.

    The head and tail are permanent sentinel nodes that never hold data. That
    single trick means insert and remove never have to ask "am I at the end?" --
    every real node always has a node on both sides of it.
    """

    def __init__(self):
        self._head = Node()
        self._tail = Node()
        self._head.next = self._tail
        self._tail.prev = self._head
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def add_to_front(self, node: Node) -> Node:
        node.prev = self._head
        node.next = self._head.next
        self._head.next.prev = node
        self._head.next = node
        self._size += 1
        return node

    def remove(self, node: Node) -> Node:
        if node.prev is None or node.next is None:
            raise ValueError(f"{node!r} is not currently in the list")

        node.prev.next = node.next
        node.next.prev = node.prev
        node.prev = node.next = None
        self._size -= 1
        return node

    def move_to_front(self, node: Node) -> Node:
        """The whole reason for a linked list: reorder in constant time."""
        return self.add_to_front(self.remove(node))

    def pop_back(self) -> Node | None:
        """Remove and return the least recent node, or None if empty."""
        if self._size == 0:
            return None
        return self.remove(self._tail.prev)

    def peek_back(self) -> Node | None:
        return self._tail.prev if self._size else None

    def __iter__(self) -> Iterator[Node]:
        """Walk from most recent to least recent."""
        node = self._head.next
        while node is not self._tail:
            yield node
            node = node.next

    def keys(self) -> list:
        return [node.key for node in self]
