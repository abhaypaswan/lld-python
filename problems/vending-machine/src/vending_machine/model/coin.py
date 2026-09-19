"""Money. Only the denominations the machine physically accepts."""

from __future__ import annotations

from enum import Enum


class Coin(Enum):
    """Accepted denominations, in the smallest unit of currency.

    An enum rather than free integers because a vending machine does not accept
    arbitrary amounts -- it accepts the coins its slot is cut for. Modelling
    that as an enum means "insert 7" is rejected at the boundary instead of
    corrupting the float.
    """

    PENNY = 1
    NICKEL = 5
    DIME = 10
    QUARTER = 25
    DOLLAR = 100

    @classmethod
    def parse(cls, value: str | int) -> Coin:
        if isinstance(value, Coin):
            return value

        try:
            return cls(int(value))
        except (ValueError, TypeError):
            pass

        name = str(value).strip().upper()
        if name in cls.__members__:
            return cls[name]

        known = ", ".join(f"{c.name.lower()}({c.value})" for c in cls)
        raise ValueError(f"{value!r} is not a coin this machine takes. Accepted: {known}")

    def __str__(self) -> str:
        return self.name.lower()
