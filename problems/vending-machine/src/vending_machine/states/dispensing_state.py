"""An item is paid for and on its way out."""

from __future__ import annotations

from ..model.coin import Coin
from ..model.item import Item
from .state import VendingMachineState


class DispensingState(VendingMachineState):
    name = "dispensing"
    prompt = "Press dispense to collect your item."

    def dispense(self) -> Item:
        machine = self.machine
        code = machine.selected_code
        price = machine.inventory.price_of(code)

        # Change comes out of the box BEFORE the item leaves the shelf. If the
        # machine cannot pay, the buyer keeps their money and their choice --
        # dispensing first would mean handing over goods it cannot settle for.
        change = machine.coin_box.make_change(machine.balance - price)

        item = machine.inventory.dispense(code)
        machine.coin_box.add(*machine.inserted_coins)

        machine.last_change = change
        machine.balance = 0
        machine.inserted_coins.clear()
        machine.selected_code = None
        machine.set_state(machine.idle_state)
        # That may have been the last item on the shelves.
        machine.refresh_availability()
        return item

    def refund(self) -> list[Coin]:
        """Change your mind before the item drops."""
        self.machine.selected_code = None
        return self.machine.return_balance()
