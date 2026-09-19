"""Waiting for the first coin."""

from __future__ import annotations

from ..model.coin import Coin
from .state import VendingMachineState


class IdleState(VendingMachineState):
    name = "idle"
    prompt = "Insert a coin to begin."

    def insert_coin(self, coin: Coin) -> str:
        self.machine.balance += coin.value
        self.machine.inserted_coins.append(coin)
        self.machine.set_state(self.machine.has_money_state)
        return f"Accepted {coin}. Balance: {self.machine.balance}."
