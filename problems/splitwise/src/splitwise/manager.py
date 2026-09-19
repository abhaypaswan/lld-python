"""The ledger: running balances, and the settlement plan that clears them."""

from __future__ import annotations

from collections.abc import Sequence

from .expense import Expense
from .splits import EqualSplit, SplitStrategy
from .user import User


class ExpenseManager:
    """Holds the expenses and the net balance per person.

    Balances are kept as a single net figure per user rather than a matrix of
    who-owes-whom. The matrix is what people reach for first, and it makes
    settlement harder than it needs to be: if Alice owes Bob 10 and Bob owes
    Carol 10, the matrix records two debts where the group really has one.
    """

    def __init__(self):
        self.users: dict[str, User] = {}
        self.expenses: list[Expense] = []
        #: Positive means the group owes them, negative means they owe it.
        self.balances: dict[User, int] = {}
        self._observers: list = []

    # -- setup ------------------------------------------------------------

    def add_user(self, user: User) -> User:
        if user.user_id in self.users:
            raise KeyError(f"User {user.user_id} is already in this group")
        self.users[user.user_id] = user
        self.balances.setdefault(user, 0)
        return user

    def subscribe(self, observer) -> None:
        """Observer: anything that wants to hear about expenses and settlements."""
        self._observers.append(observer)

    # -- recording --------------------------------------------------------

    def add_expense(
        self,
        payer: User,
        amount: int,
        participants: Sequence[User],
        strategy: SplitStrategy | None = None,
        description: str = "",
    ) -> Expense:
        expense = Expense(
            payer=payer,
            amount=amount,
            participants=participants,
            strategy=strategy or EqualSplit(),
            description=description,
        )

        for user, delta in expense.balance_deltas().items():
            self.balances[user] = self.balances.get(user, 0) + delta

        self.expenses.append(expense)
        for observer in self._observers:
            observer.on_expense_added(expense)
        return expense

    def settle(self, payer: User, payee: User, amount: int) -> None:
        """Record a real payment between two people."""
        if amount <= 0:
            raise ValueError(f"A settlement must be positive, got {amount}")

        self.balances[payer] = self.balances.get(payer, 0) + amount
        self.balances[payee] = self.balances.get(payee, 0) - amount

        for observer in self._observers:
            observer.on_settlement(payer, payee, amount)

    # -- reading ----------------------------------------------------------

    def balance_of(self, user: User) -> int:
        return self.balances.get(user, 0)

    def owes(self) -> dict[User, int]:
        """Everyone with a negative balance, as a positive amount owed."""
        return {user: -balance for user, balance in self.balances.items() if balance < 0}

    def owed(self) -> dict[User, int]:
        """Everyone the group owes money to."""
        return {user: balance for user, balance in self.balances.items() if balance > 0}

    def simplify(self) -> list[tuple[User, User, int]]:
        """The payments that clear every balance, as (payer, payee, amount).

        Greedy: repeatedly match the largest debtor against the largest
        creditor. Each round zeroes at least one person, so the plan never
        needs more than n-1 payments for n people -- usually far fewer.

        This is not guaranteed to be the theoretical minimum. Finding that is
        equivalent to a subset-sum problem and is NP-hard, which is worth
        saying out loud rather than claiming optimality the algorithm does not
        have. Greedy is what production apps ship, because it is close enough
        and it terminates.
        """
        debtors = sorted(self.owes().items(), key=lambda pair: (-pair[1], str(pair[0])))
        creditors = sorted(self.owed().items(), key=lambda pair: (-pair[1], str(pair[0])))

        payments: list[tuple[User, User, int]] = []
        debtors = [[user, amount] for user, amount in debtors]
        creditors = [[user, amount] for user, amount in creditors]

        i = j = 0
        while i < len(debtors) and j < len(creditors):
            debtor, owed = debtors[i]
            creditor, due = creditors[j]

            payment = min(owed, due)
            payments.append((debtor, creditor, payment))

            debtors[i][1] -= payment
            creditors[j][1] -= payment

            if debtors[i][1] == 0:
                i += 1
            if creditors[j][1] == 0:
                j += 1

        return payments

    def summary(self) -> str:
        if not any(self.balances.values()):
            return "Everyone is settled up."

        lines = ["Balances:"]
        for user in sorted(self.balances, key=str):
            balance = self.balances[user]
            if balance > 0:
                lines.append(f"  {user} is owed {balance}")
            elif balance < 0:
                lines.append(f"  {user} owes {-balance}")

        lines.append("Settle up with:")
        for payer, payee, amount in self.simplify():
            lines.append(f"  {payer} pays {payee} {amount}")
        return "\n".join(lines)
