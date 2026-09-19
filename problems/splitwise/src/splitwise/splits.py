"""Strategy: how one expense is divided among the people on it.

Every strategy answers the same question -- given a total and a set of people,
who owes what -- and the four differ only in what extra input they need. That
is a textbook Strategy: same signature, different rule, chosen per expense
rather than per group.

Amounts are integers in the smallest currency unit throughout. Money in floats
is a bug waiting for a rounding boundary: 0.1 + 0.2 != 0.3, and a split that
does not add back up to the total is exactly the kind of thing that surfaces
three months later as a one-cent discrepancy nobody can explain.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .user import User


class SplitStrategy(ABC):
    """Divides an amount between participants."""

    name: str = "split"

    @abstractmethod
    def split(self, amount: int, participants: Sequence[User]) -> dict[User, int]:
        """Return what each participant owes. Must sum exactly to `amount`."""

    @staticmethod
    def _check_participants(participants: Sequence[User]) -> None:
        if not participants:
            raise ValueError("An expense needs at least one participant")
        if len(set(participants)) != len(participants):
            raise ValueError("The same person cannot appear twice in one split")

    @staticmethod
    def _verify(shares: dict[User, int], amount: int) -> dict[User, int]:
        """The invariant that makes every other guarantee hold."""
        total = sum(shares.values())
        if total != amount:
            raise ValueError(f"Shares sum to {total}, but the expense was {amount}")
        return shares


class EqualSplit(SplitStrategy):
    """Everyone pays the same, give or take the remainder.

    The case worth getting right: 100 split three ways. Each share is 33 and
    there is 1 left over. Dropping it loses money; giving everyone 34 invents
    it. The remainder is handed out one unit at a time to the first few
    participants, so the total is exact and the largest gap between any two
    people is one cent.

    Real apps rotate who absorbs the remainder across expenses so it evens out.
    Deterministic order is enough here, and saying which one you chose and why
    is the point.
    """

    name = "equal"

    def split(self, amount: int, participants: Sequence[User]) -> dict[User, int]:
        self._check_participants(participants)

        count = len(participants)
        base, remainder = divmod(amount, count)
        shares = {
            user: base + (1 if index < remainder else 0)
            for index, user in enumerate(participants)
        }
        return self._verify(shares, amount)


class ExactSplit(SplitStrategy):
    """Each person's share is stated outright."""

    name = "exact"

    def __init__(self, amounts: dict[User, int]):
        self.amounts = dict(amounts)

    def split(self, amount: int, participants: Sequence[User]) -> dict[User, int]:
        self._check_participants(participants)

        missing = set(participants) - set(self.amounts)
        if missing:
            raise ValueError(f"No amount given for: {', '.join(str(u) for u in sorted(missing, key=str))}")

        extra = set(self.amounts) - set(participants)
        if extra:
            raise ValueError(
                f"Amounts given for people not on the expense: "
                f"{', '.join(str(u) for u in sorted(extra, key=str))}"
            )

        return self._verify({user: self.amounts[user] for user in participants}, amount)


class PercentageSplit(SplitStrategy):
    """Shares stated as percentages, which must total 100."""

    name = "percentage"

    def __init__(self, percentages: dict[User, float]):
        self.percentages = dict(percentages)

    def split(self, amount: int, participants: Sequence[User]) -> dict[User, int]:
        self._check_participants(participants)

        missing = set(participants) - set(self.percentages)
        if missing:
            raise ValueError(
                f"No percentage given for: {', '.join(str(u) for u in sorted(missing, key=str))}"
            )

        total = sum(self.percentages[user] for user in participants)
        if abs(total - 100.0) > 1e-9:
            raise ValueError(f"Percentages must add up to 100, got {total}")

        return self._verify(
            _largest_remainder(
                amount, {user: self.percentages[user] for user in participants}
            ),
            amount,
        )


class ShareSplit(SplitStrategy):
    """Shares as weights: 2 shares to one person, 1 each to two others.

    Useful when three people take a flat and one gets the big bedroom. The
    weights need not add up to anything in particular.
    """

    name = "share"

    def __init__(self, shares: dict[User, int]):
        self.shares = dict(shares)

    def split(self, amount: int, participants: Sequence[User]) -> dict[User, int]:
        self._check_participants(participants)

        missing = set(participants) - set(self.shares)
        if missing:
            raise ValueError(
                f"No share count given for: {', '.join(str(u) for u in sorted(missing, key=str))}"
            )

        weights = {user: self.shares[user] for user in participants}
        if any(weight < 0 for weight in weights.values()):
            raise ValueError("Share counts cannot be negative")
        if sum(weights.values()) == 0:
            raise ValueError("Share counts cannot all be zero")

        return self._verify(_largest_remainder(amount, weights), amount)


def _largest_remainder(amount: int, weights: dict[User, float]) -> dict[User, int]:
    """Apportion `amount` by weight so the parts sum exactly to the whole.

    This is the largest remainder method: floor every share, then hand the
    leftover units to whoever was rounded down hardest. Rounding each share
    independently is what produces totals that are a cent or two off, and the
    error compounds across a group's history.
    """
    total_weight = sum(weights.values())
    exact = {user: amount * weight / total_weight for user, weight in weights.items()}
    shares = {user: int(value) for user, value in exact.items()}

    leftover = amount - sum(shares.values())
    by_remainder = sorted(
        exact, key=lambda user: (-(exact[user] - shares[user]), str(user))
    )

    for user in by_remainder[:leftover]:
        shares[user] += 1
    return shares
