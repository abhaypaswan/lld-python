"""Every slot is empty. The machine takes no money at all."""

from __future__ import annotations

from ..model.coin import Coin
from .state import VendingMachineState


class SoldOutState(VendingMachineState):
    name = "sold-out"
    prompt = "This machine is sold out."

    def refund(self) -> list[Coin]:
        """Always allowed. Refusing to return money already inserted would be theft."""
        return self.machine.return_balance()
