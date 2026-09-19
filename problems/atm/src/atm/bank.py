"""Accounts, and the bank behind the machine.

Deliberately separate from the ATM. A machine that owns its accounts cannot be
tested against a stub bank, and in reality the bank is over a network and can
be slow, wrong, or unreachable -- all of which the ATM has to survive.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class InsufficientFunds(Exception):
    """The account does not hold enough to cover this."""


class AuthenticationFailed(Exception):
    """Wrong PIN, unknown card, or a blocked card."""


@dataclass
class Account:
    """A balance in the smallest currency unit, plus a daily withdrawal cap."""

    account_number: str
    pin: str
    balance: int = 0
    daily_limit: int = 50_000
    withdrawn_today: int = 0
    blocked: bool = False
    history: list = field(default_factory=list)

    @property
    def remaining_today(self) -> int:
        return max(0, self.daily_limit - self.withdrawn_today)

    def debit(self, amount: int) -> int:
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")
        if amount > self.balance:
            raise InsufficientFunds(f"Balance is {self.balance}, which will not cover {amount}")
        if amount > self.remaining_today:
            raise InsufficientFunds(
                f"Daily limit reached: {self.remaining_today} of {self.daily_limit} left today"
            )

        self.balance -= amount
        self.withdrawn_today += amount
        self.history.append(("withdraw", amount, self.balance))
        return self.balance

    def credit(self, amount: int) -> int:
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        self.balance += amount
        self.history.append(("deposit", amount, self.balance))
        return self.balance

    def start_new_day(self) -> None:
        self.withdrawn_today = 0


class Bank:
    """Holds accounts and checks PINs."""

    #: A card is blocked after this many wrong PINs.
    max_pin_attempts = 3

    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self._failed_attempts: dict[str, int] = {}

    def open_account(self, account_number: str, pin: str, balance: int = 0, **kwargs) -> Account:
        if account_number in self.accounts:
            raise KeyError(f"Account {account_number} already exists")

        account = Account(account_number, pin, balance, **kwargs)
        self.accounts[account_number] = account
        return account

    def get(self, account_number: str) -> Account:
        account = self.accounts.get(account_number)
        if account is None:
            raise AuthenticationFailed(f"No account {account_number}")
        return account

    def authenticate(self, account_number: str, pin: str) -> Account:
        account = self.get(account_number)

        if account.blocked:
            raise AuthenticationFailed(f"Card for {account_number} is blocked")

        if account.pin != pin:
            attempts = self._failed_attempts.get(account_number, 0) + 1
            self._failed_attempts[account_number] = attempts

            if attempts >= self.max_pin_attempts:
                account.blocked = True
                raise AuthenticationFailed(
                    f"Incorrect PIN. Card blocked after {attempts} attempts."
                )
            remaining = self.max_pin_attempts - attempts
            raise AuthenticationFailed(f"Incorrect PIN. {remaining} attempt(s) left.")

        self._failed_attempts.pop(account_number, None)
        return account

    def transfer(self, source: Account, target_number: str, amount: int) -> None:
        target = self.get(target_number)
        if target is source:
            raise ValueError("Cannot transfer to the same account")

        # Debit first: it is the step that can fail. Crediting first and then
        # failing to debit invents money.
        source.debit(amount)
        target.credit(amount)
