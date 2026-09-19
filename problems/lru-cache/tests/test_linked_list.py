"""The doubly linked list on its own, since it is the load-bearing part."""

import pytest
from lru_cache.linked_list import DoublyLinkedList, Node


def test_a_new_list_is_empty():
    assert len(DoublyLinkedList()) == 0
    assert DoublyLinkedList().pop_back() is None


def test_nodes_come_out_most_recent_first():
    dll = DoublyLinkedList()
    for key in "abc":
        dll.add_to_front(Node(key))

    assert dll.keys() == ["c", "b", "a"]


def test_moving_a_node_to_the_front_reorders_it():
    dll = DoublyLinkedList()
    nodes = {key: dll.add_to_front(Node(key)) for key in "abc"}

    dll.move_to_front(nodes["a"])

    assert dll.keys() == ["a", "c", "b"]


def test_moving_the_front_node_to_the_front_changes_nothing():
    dll = DoublyLinkedList()
    nodes = {key: dll.add_to_front(Node(key)) for key in "ab"}

    dll.move_to_front(nodes["b"])

    assert dll.keys() == ["b", "a"]
    assert len(dll) == 2


def test_popping_the_back_takes_the_oldest():
    dll = DoublyLinkedList()
    for key in "abc":
        dll.add_to_front(Node(key))

    assert dll.pop_back().key == "a"
    assert dll.keys() == ["c", "b"]


def test_removing_the_only_node_leaves_a_working_empty_list():
    dll = DoublyLinkedList()
    node = dll.add_to_front(Node("a"))

    dll.remove(node)

    assert len(dll) == 0
    assert dll.keys() == []
    dll.add_to_front(Node("b"))
    assert dll.keys() == ["b"]


def test_removing_a_node_twice_is_an_error():
    dll = DoublyLinkedList()
    node = dll.add_to_front(Node("a"))
    dll.remove(node)

    with pytest.raises(ValueError, match="not currently in the list"):
        dll.remove(node)
