"""What is in the machine, and how much of it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """A product. Immutable -- a Coke's name and price do not change in a slot."""

    code: str
    name: str
    price: int

    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"{self.name} needs a positive price, got {self.price}")


@dataclass
class Slot:
    """One shelf position: an item plus how many are left."""

    item: Item
    quantity: int = 0

    @property
    def is_empty(self) -> bool:
        return self.quantity <= 0

    def dispense_one(self) -> Item:
        if self.is_empty:
            raise ValueError(f"{self.item.name} is sold out")
        self.quantity -= 1
        return self.item

    def restock(self, count: int) -> None:
        if count <= 0:
            raise ValueError(f"Restock count must be positive, got {count}")
        self.quantity += count
