"""Money, in the smallest unit, with the currency attached.

The bug this exists to prevent is the most expensive one in the whole problem:
Stripe wants cents, Razorpay wants paise, Adyen wants a value object, and every
one of them is "the amount". A bare int passed between them is a 100x error
waiting to happen, and it will not raise -- it will just charge the wrong
amount.
"""

from __future__ import annotations

from dataclasses import dataclass

#: How many minor units make one major unit. Not every currency uses 100:
#: the yen has none, and getting this wrong is a 100x error, not a rounding one.
MINOR_UNITS: dict[str, int] = {
    "USD": 100,
    "EUR": 100,
    "GBP": 100,
    "INR": 100,
    "JPY": 1,
}


@dataclass(frozen=True)
class Money:
    """An amount in minor units, plus its currency."""

    minor_units: int
    currency: str = "USD"

    def __post_init__(self):
        currency = self.currency.upper()
        object.__setattr__(self, "currency", currency)

        if currency not in MINOR_UNITS:
            known = ", ".join(sorted(MINOR_UNITS))
            raise ValueError(f"{currency} is not a supported currency. Known: {known}")
        if self.minor_units < 0:
            raise ValueError(f"Money cannot be negative, got {self.minor_units}")

    @classmethod
    def of(cls, major: float, currency: str = "USD") -> Money:
        """`Money.of(12.50, 'USD')` -> 1250 cents."""
        factor = MINOR_UNITS.get(currency.upper(), 100)
        return cls(round(major * factor), currency)

    @property
    def major_units(self) -> float:
        return self.minor_units / MINOR_UNITS[self.currency]

    def _same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"Cannot combine {self.currency} and {other.currency} without a rate")

    def __add__(self, other: Money) -> Money:
        self._same_currency(other)
        return Money(self.minor_units + other.minor_units, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._same_currency(other)
        return Money(self.minor_units - other.minor_units, self.currency)

    def __mul__(self, factor: float) -> Money:
        return Money(round(self.minor_units * factor), self.currency)

    def __lt__(self, other: Money) -> bool:
        self._same_currency(other)
        return self.minor_units < other.minor_units

    def __bool__(self) -> bool:
        return self.minor_units > 0

    def __str__(self) -> str:
        return f"{self.major_units:,.2f} {self.currency}"
