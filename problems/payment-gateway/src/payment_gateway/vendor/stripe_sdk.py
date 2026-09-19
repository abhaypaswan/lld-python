"""A Stripe-shaped SDK.

Amounts in **cents**. Raises on failure. Returns a dict.
"""

from __future__ import annotations

import itertools

_ids = itertools.count(1)


class StripeError(Exception):
    """Raised for a declined card or a bad request."""

    def __init__(self, message: str, code: str = "card_declined"):
        super().__init__(message)
        self.code = code


class StripeClient:
    def __init__(self, api_key: str, fail_on: set[str] | None = None):
        if not api_key.startswith("sk_"):
            raise ValueError("Stripe keys start with sk_")

        self.api_key = api_key
        #: Card tokens that should be declined, so the demo can show failure.
        self.fail_on = fail_on or set()
        self.charges: dict[str, dict] = {}
        self.calls = 0

    def create_charge(
        self, amount_cents: int, currency: str, source: str, idempotency_key: str | None = None
    ) -> dict:
        self.calls += 1

        if idempotency_key:
            for charge in self.charges.values():
                if charge.get("idempotency_key") == idempotency_key:
                    return charge

        if amount_cents <= 0:
            raise StripeError("Amount must be positive", code="invalid_request")
        if source in self.fail_on:
            raise StripeError(f"Your card was declined ({source})", code="card_declined")

        charge = {
            "id": f"ch_{next(_ids):08d}",
            "amount": amount_cents,
            "currency": currency.lower(),
            "source": source,
            "status": "succeeded",
            "idempotency_key": idempotency_key,
        }
        self.charges[charge["id"]] = charge
        return charge

    def create_refund(self, charge_id: str, amount_cents: int | None = None) -> dict:
        self.calls += 1
        charge = self.charges.get(charge_id)
        if charge is None:
            raise StripeError(f"No such charge: {charge_id}", code="resource_missing")

        return {
            "id": f"re_{next(_ids):08d}",
            "charge": charge_id,
            "amount": amount_cents if amount_cents is not None else charge["amount"],
            "status": "succeeded",
        }
