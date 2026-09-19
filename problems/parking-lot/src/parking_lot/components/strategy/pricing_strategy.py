"""Strategy: how a stay turns into a bill.

Kept separate from the parking strategy because the two change for completely
different reasons -- one is an operations decision, the other is a pricing one.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...model.ticket import Ticket

SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60


class PricingStrategy(ABC):
    name: str = "pricing"

    @abstractmethod
    def calculate(self, ticket: Ticket, exit_time: float) -> float:
        """Return what this stay costs, in whole currency units."""

    @staticmethod
    def _duration(ticket: Ticket, exit_time: float) -> tuple[int, int]:
        """Split the stay into whole hours and leftover minutes."""
        seconds = max(0.0, exit_time - ticket.entry_time)
        return int(seconds // SECONDS_PER_HOUR), int(
            (seconds % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
        )


class HourlyPricingStrategy(PricingStrategy):
    """Charge the spot's hourly rate, plus a per-minute rate for the remainder."""

    name = "hourly"

    def calculate(self, ticket: Ticket, exit_time: float) -> float:
        hours, minutes = self._duration(ticket, exit_time)
        spot = ticket.parking_spot
        return hours * spot.hour_charge + minutes * spot.minute_charge


class FlatRatePricingStrategy(PricingStrategy):
    """One price, however long you stay."""

    name = "flat"

    def __init__(self, amount: float = 150.0):
        if amount < 0:
            raise ValueError("A flat rate cannot be negative")
        self.amount = amount

    def calculate(self, ticket: Ticket, exit_time: float) -> float:
        return self.amount


class FreeFirstHourStrategy(HourlyPricingStrategy):
    """Hourly pricing, but the first hour is on the house.

    Subclassing HourlyPricingStrategy rather than copying it is the point: the
    discount rule is the only thing that differs.
    """

    name = "free-first-hour"

    def calculate(self, ticket: Ticket, exit_time: float) -> float:
        hours, minutes = self._duration(ticket, exit_time)
        if hours == 0:
            return 0.0

        spot = ticket.parking_spot
        return (hours - 1) * spot.hour_charge + minutes * spot.minute_charge


PRICING_STRATEGIES: dict[str, type[PricingStrategy]] = {
    HourlyPricingStrategy.name: HourlyPricingStrategy,
    FlatRatePricingStrategy.name: FlatRatePricingStrategy,
    FreeFirstHourStrategy.name: FreeFirstHourStrategy,
    "default": HourlyPricingStrategy,
}


def get_pricing_strategy(name: str = "default") -> PricingStrategy:
    try:
        return PRICING_STRATEGIES[name]()
    except KeyError:
        known = ", ".join(sorted(set(PRICING_STRATEGIES) - {"default"}))
        raise ValueError(f"{name!r} is not a pricing strategy. Try one of: {known}") from None
