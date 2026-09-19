"""Money is in. Waiting for a selection, or for more money."""

from __future__ import annotations

from ..model.coin import Coin
from ..model.inventory import SoldOut
from .state import VendingMachineState


class HasMoneyState(VendingMachineState):
    name = "has-money"
    prompt = "Insert more coins, select an item, or ask for a refund."

    def insert_coin(self, coin: Coin) -> str:
        self.machine.balance += coin.value
        self.machine.inserted_coins.append(coin)
        return f"Accepted {coin}. Balance: {self.machine.balance}."

    def select_item(self, code: str) -> str:
        slot = self.machine.inventory.get_slot(code)

        if slot.is_empty:
            # Deliberately not a state change. The buyer still has their money
            # in the machine and can pick something else.
            raise SoldOut(f"{slot.item.name} is sold out. Pick something else or ask for a refund.")

        if self.machine.balance < slot.item.price:
            short = slot.item.price - self.machine.balance
            raise ValueError(
                f"{slot.item.name} costs {slot.item.price}. "
                f"Balance is {self.machine.balance}, so you are {short} short."
            )

        self.machine.selected_code = slot.item.code
        self.machine.set_state(self.machine.dispensing_state)
        return f"Selected {slot.item.name} at {slot.item.price}."

    def refund(self) -> list[Coin]:
        return self.machine.return_balance()
