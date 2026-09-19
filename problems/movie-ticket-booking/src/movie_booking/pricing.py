"""Strategy: what a seat costs.

Separate from the show because pricing is a commercial decision that changes on
its own schedule, and a cinema runs several at once -- weekday discounts,
weekend surge, loyalty rates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Seat, Show


class PricingStrategy(ABC):
    name: str = "pricing"

    @abstractmethod
    def price_for(self, show: Show, seat: Seat) -> int:
        """Price one seat, in the smallest currency unit."""

    def total(self, show: Show, seats: list[Seat]) -> int:
        return sum(self.price_for(show, seat) for seat in seats)


class StandardPricing(PricingStrategy):
    """Base price, scaled by seat class."""

    name = "standard"

    def price_for(self, show: Show, seat: Seat) -> int:
        return show.price_of(seat)


class SurgePricing(StandardPricing):
    """Standard, marked up once the house is filling.

    Applied on occupancy rather than on a clock, which is what makes it
    testable: a show that is 80% full is 80% full regardless of the hour.
    """

    name = "surge"

    def __init__(self, threshold: float = 0.6, multiplier: float = 1.3):
        if not 0 < threshold <= 1:
            raise ValueError(f"Threshold must be between 0 and 1, got {threshold}")
        if multiplier < 1:
            raise ValueError(f"A surge multiplier below 1 is a discount, got {multiplier}")

        self.threshold = threshold
        self.multiplier = multiplier

    def price_for(self, show: Show, seat: Seat) -> int:
        base = super().price_for(show, seat)
        occupancy = len(show.booked_seats()) / show.screen.capacity

        return round(base * self.multiplier) if occupancy >= self.threshold else base


class WeekdayDiscount(StandardPricing):
    """A flat percentage off. Decorating would compose better than subclassing
    for a real system; this stays a subclass to keep the example short, and the
    README says so rather than pretending otherwise."""

    name = "weekday"

    def __init__(self, percent_off: float = 20.0):
        if not 0 <= percent_off < 100:
            raise ValueError(f"Discount must be between 0 and 100, got {percent_off}")
        self.percent_off = percent_off

    def price_for(self, show: Show, seat: Seat) -> int:
        return round(super().price_for(show, seat) * (1 - self.percent_off / 100))


PRICING_STRATEGIES: dict[str, type[PricingStrategy]] = {
    StandardPricing.name: StandardPricing,
    SurgePricing.name: SurgePricing,
    WeekdayDiscount.name: WeekdayDiscount,
}


def get_pricing_strategy(name: str = "standard") -> PricingStrategy:
    try:
        return PRICING_STRATEGIES[name]()
    except KeyError:
        known = ", ".join(sorted(PRICING_STRATEGIES))
        raise ValueError(f"{name!r} is not a pricing strategy. Try one of: {known}") from None
