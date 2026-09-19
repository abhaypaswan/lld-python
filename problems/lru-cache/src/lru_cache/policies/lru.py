"""Least Recently Used: drop whatever was touched longest ago."""

from __future__ import annotations

from typing import Any

from ..linked_list import DoublyLinkedList, Node
from .policy import EvictionPolicy


class LRUPolicy(EvictionPolicy):
    """A recency list plus a key -> node map.

    Either structure alone is not enough. The list gives ordering but O(n)
    lookup; the map gives O(1) lookup but no ordering. Together, every
    operation is O(1) -- which is the entire reason this pairing shows up in
    every LRU answer.
    """

    name = "lru"

    def __init__(self):
        self._order = DoublyLinkedList()
        self._nodes: dict[Any, Node] = {}

    def record_access(self, key: Any) -> None:
        node = self._nodes.get(key)
        if node is not None:
            self._order.move_to_front(node)

    def record_insert(self, key: Any) -> None:
        if key in self._nodes:
            self.record_access(key)
            return
        self._nodes[key] = self._order.add_to_front(Node(key))

    def record_removal(self, key: Any) -> None:
        node = self._nodes.pop(key, None)
        if node is not None:
            self._order.remove(node)

    def evict(self) -> Any:
        node = self._order.pop_back()
        if node is None:
            raise KeyError("Nothing to evict: the policy is tracking no keys")

        del self._nodes[node.key]
        return node.key

    def clear(self) -> None:
        self._order = DoublyLinkedList()
        self._nodes.clear()

    def order(self) -> list:
        return self._order.keys()
