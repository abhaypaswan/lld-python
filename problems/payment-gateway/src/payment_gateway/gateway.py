"""The gateway: idempotency, and falling back to the next provider."""

from __future__ import annotations

from .money import Money
from .processor import PaymentProcessor, PaymentResult, PaymentStatus
from .regions import RegionalPaymentFactory


class NoUsableProvider(Exception):
    """No configured provider can take this payment."""


class PaymentGateway:
    """Routes a charge to a processor, with retries onto the next one.

    Two things live here rather than in any adapter, because both are policy
    rather than translation:

    - **Idempotency.** The same key must never charge twice, however many times
      a flaky client retries. Each provider has its own mechanism; the gateway
      also keeps its own record, so a retry is answered without a network call
      at all.
    - **Fallback.** A *declined* card is worth trying elsewhere; a *malformed
      request* is not, and retrying it just produces the same error three times
      more slowly.
    """

    def __init__(self, processors: list[PaymentProcessor] | None = None):
        self.processors: list[PaymentProcessor] = list(processors or [])
        self._completed: dict[str, PaymentResult] = {}
        self.attempts: list[tuple[str, PaymentStatus]] = []

    @classmethod
    def for_region(cls, factory: RegionalPaymentFactory, *fallbacks: PaymentProcessor):
        return cls([factory.create_processor(), *fallbacks])

    def add_processor(self, processor: PaymentProcessor) -> PaymentProcessor:
        self.processors.append(processor)
        return processor

    def usable_for(self, currency: str) -> list[PaymentProcessor]:
        return [p for p in self.processors if p.supports(currency)]

    def charge(self, amount: Money, token: str, idempotency_key: str = "") -> PaymentResult:
        if idempotency_key and idempotency_key in self._completed:
            # Answered from our own record: no provider is contacted at all.
            return self._completed[idempotency_key]

        candidates = self.usable_for(amount.currency)
        if not candidates:
            raise NoUsableProvider(
                f"No configured provider accepts {amount.currency}. "
                f"Configured: {', '.join(p.name for p in self.processors) or '(none)'}"
            )

        last = None
        for processor in candidates:
            result = processor.charge(amount, token, idempotency_key)
            self.attempts.append((processor.name, result.status))

            if result.succeeded:
                if idempotency_key:
                    self._completed[idempotency_key] = result
                return result

            last = result
            if result.status is PaymentStatus.FAILED:
                # A bad request will be just as bad at the next provider.
                break

        return last

    def refund(self, result: PaymentResult, amount: Money | None = None) -> PaymentResult:
        """Refund through the provider that took the money, not just any."""
        processor = next((p for p in self.processors if p.name == result.provider), None)
        if processor is None:
            raise NoUsableProvider(
                f"{result.provider} took this payment but is no longer configured"
            )

        return processor.refund(result.reference, amount)
