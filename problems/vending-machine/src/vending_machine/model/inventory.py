"""The shelves, and the coin box behind them."""

from __future__ import annotations

from collections import Counter

from .coin import Coin
from .item import Item, Slot


class SoldOut(Exception):
    """The requested item has no stock."""


class CannotMakeChange(Exception):
    """The coin box cannot pay out the exact change owed."""


class Inventory:
    """Item slots, keyed by the code a buyer types."""

    def __init__(self):
        self._slots: dict[str, Slot] = {}

    def add_item(self, item: Item, quantity: int = 0) -> Slot:
        code = item.code.upper()
        if code in self._slots:
            raise KeyError(f"Slot {code} is already taken by {self._slots[code].item.name}")

        slot = Slot(item, quantity)
        self._slots[code] = slot
        return slot

    def get_slot(self, code: str) -> Slot:
        slot = self._slots.get(str(code).strip().upper())
        if slot is None:
            known = ", ".join(sorted(self._slots)) or "(none)"
            raise KeyError(f"No slot {code}. This machine has: {known}")
        return slot

    def price_of(self, code: str) -> int:
        return self.get_slot(code).item.price

    def dispense(self, code: str) -> Item:
        slot = self.get_slot(code)
        if slot.is_empty:
            raise SoldOut(f"{slot.item.name} is sold out")
        return slot.dispense_one()

    def restock(self, code: str, count: int) -> None:
        self.get_slot(code).restock(count)

    @property
    def slots(self) -> list[Slot]:
        return [self._slots[code] for code in sorted(self._slots)]


class CoinBox:
    """The float the machine pays change from.

    Change-making is greedy here, which is correct for any canonical coin
    system (1/5/10/25/100 included). It is worth saying out loud in an
    interview that greedy is not correct for every possible denomination set --
    with coins of 1, 3 and 4, greedy makes 6 as 4+1+1 when 3+3 is better.
    """

    def __init__(self, coins: dict[Coin, int] | None = None):
        self._coins: Counter[Coin] = Counter(coins or {})

    def add(self, *coins: Coin) -> None:
        self._coins.update(coins)

    @property
    def total(self) -> int:
        return sum(coin.value * count for coin, count in self._coins.items())

    def counts(self) -> dict[Coin, int]:
        return {coin: count for coin, count in self._coins.items() if count > 0}

    def make_change(self, amount: int) -> list[Coin]:
        """Take `amount` out of the box, or raise without taking anything."""
        if amount < 0:
            raise ValueError(f"Cannot make negative change: {amount}")
        if amount == 0:
            return []

        remaining = amount
        change: list[Coin] = []
        available = Counter(self._coins)

        for coin in sorted(Coin, key=lambda c: c.value, reverse=True):
            while remaining >= coin.value and available[coin] > 0:
                change.append(coin)
                available[coin] -= 1
                remaining -= coin.value

        if remaining:
            # Nothing has been removed from the real box yet, so a failure here
            # leaves the machine exactly as it was. That ordering is the whole
            # reason the work happens on a copy.
            raise CannotMakeChange(
                f"Cannot make {amount} from {self.total} in the box (short by {remaining})"
            )

        self._coins = available
        return change
