"""The machine itself: a context holding the current state."""

from __future__ import annotations

from .model.coin import Coin
from .model.inventory import CoinBox, Inventory
from .model.item import Item
from .states import DispensingState, HasMoneyState, IdleState, SoldOutState


class VendingMachine:
    """Holds the money, the stock, and whichever state is currently in charge.

    Every public method here is a one-line delegation to `self.state`. That is
    the shape to aim for: the context owns the data, the state owns the
    decisions, and neither one grows an `if` about the other.
    """

    def __init__(self, inventory: Inventory | None = None, coin_box: CoinBox | None = None):
        self.inventory = inventory or Inventory()
        self.coin_box = coin_box or CoinBox()

        self.balance: int = 0
        self.inserted_coins: list[Coin] = []
        self.selected_code: str | None = None
        self.last_change: list[Coin] = []

        # One instance per state, created once. States hold no per-transaction
        # data -- that all lives on the machine -- so they are safe to reuse.
        self.idle_state = IdleState(self)
        self.has_money_state = HasMoneyState(self)
        self.dispensing_state = DispensingState(self)
        self.sold_out_state = SoldOutState(self)

        self.state = self.idle_state

    # -- state plumbing ---------------------------------------------------

    def set_state(self, state) -> None:
        self.state = state

    def refresh_availability(self) -> None:
        """Move in or out of sold-out, if stock changed while idle.

        Only called when no transaction is underway. Flipping a mid-purchase
        machine to sold-out would strand the buyer's money.
        """
        if self.state in (self.idle_state, self.sold_out_state):
            everything_gone = all(slot.is_empty for slot in self.inventory.slots)
            self.state = self.sold_out_state if everything_gone else self.idle_state

    # -- what a buyer can do ----------------------------------------------

    def insert_coin(self, coin: Coin | str | int) -> str:
        return self.state.insert_coin(Coin.parse(coin))

    def select_item(self, code: str) -> str:
        return self.state.select_item(code)

    def dispense(self) -> Item:
        return self.state.dispense()

    def refund(self) -> list[Coin]:
        return self.state.refund()

    # -- what an operator can do ------------------------------------------

    def add_item(self, code: str, name: str, price: int, quantity: int = 0):
        slot = self.inventory.add_item(Item(code.upper(), name, price), quantity)
        self.refresh_availability()
        return slot

    def restock(self, code: str, count: int) -> None:
        self.inventory.restock(code, count)
        self.refresh_availability()

    def load_coins(self, **coins: int) -> None:
        """Seed the change float, e.g. `load_coins(quarter=10, dime=10)`."""
        for name, count in coins.items():
            self.coin_box.add(*[Coin.parse(name)] * count)

    # -- shared helper ----------------------------------------------------

    def return_balance(self) -> list[Coin]:
        """Hand back exactly the coins that were inserted.

        Returning the same physical coins rather than making change avoids the
        machine ever failing to refund because its float is low. A real machine
        holds inserted coins in escrow for precisely this reason.
        """
        returned = list(self.inserted_coins)
        self.inserted_coins.clear()
        self.balance = 0
        self.selected_code = None
        self.state = self.idle_state
        self.refresh_availability()
        return returned

    # -- display ----------------------------------------------------------

    def status(self) -> str:
        lines = [f"State: {self.state} — {self.state.prompt}", f"Balance: {self.balance}"]
        for slot in self.inventory.slots:
            stock = "sold out" if slot.is_empty else f"{slot.quantity} left"
            lines.append(f"  {slot.item.code}  {slot.item.name:<14} {slot.item.price:>4}  ({stock})")
        return "\n".join(lines)
