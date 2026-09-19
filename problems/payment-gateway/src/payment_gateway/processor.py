"""The interface we own, and the results that come back through it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from .money import Money


class PaymentStatus(Enum):
    SUCCEEDED = "succeeded"
    DECLINED = "declined"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PaymentResult:
    """One normalised outcome, whichever provider produced it.

    Every provider signals failure differently -- Stripe raises, Razorpay
    returns a status field, Adyen raises its own type and calls success
    "Authorised". Normalising to one result type here is what stops that
    variety from leaking into every caller.
    """

    status: PaymentStatus
    amount: Money
    provider: str
    reference: str = ""
    error_code: str = ""
    message: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def succeeded(self) -> bool:
        return self.status is PaymentStatus.SUCCEEDED

    def __bool__(self) -> bool:
        return self.succeeded

    def __str__(self) -> str:
        if self.succeeded:
            return f"{self.provider}: charged {self.amount} ({self.reference})"
        return f"{self.provider}: {self.status} — {self.message or self.error_code}"


class PaymentProcessor(ABC):
    """The interface our code is written against.

    Every provider gets an adapter conforming to this. Nothing above this line
    ever imports a vendor SDK, which is the property that makes swapping a
    provider a configuration change rather than a migration.
    """

    name: str = "processor"
    supported_currencies: frozenset[str] = frozenset()

    @abstractmethod
    def charge(self, amount: Money, token: str, idempotency_key: str = "") -> PaymentResult:
        """Take a payment. Must never raise for an ordinary decline."""

    @abstractmethod
    def refund(self, reference: str, amount: Money | None = None) -> PaymentResult:
        """Refund a previous charge, wholly or in part."""

    def supports(self, currency: str) -> bool:
        return not self.supported_currencies or currency.upper() in self.supported_currencies
