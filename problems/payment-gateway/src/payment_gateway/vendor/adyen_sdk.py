"""An Adyen-shaped SDK.

Amounts as an object with a value and a currency. Raises its own exception
type. Calls a successful result "Authorised", with an s.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

_ids = itertools.count(1)


class AdyenRefused(Exception):
    def __init__(self, reason: str, result_code: str = "Refused"):
        super().__init__(reason)
        self.result_code = result_code


@dataclass
class Amount:
    value: int
    currency: str


class AdyenClient:
    def __init__(self, merchant_account: str, refuse: set[str] | None = None):
        self.merchant_account = merchant_account
        self.refuse = refuse or set()
        self.payments: dict[str, dict] = {}
        self.calls = 0

    def payments_request(self, amount: Amount, payment_method: dict, reference: str = "") -> dict:
        self.calls += 1

        if reference:
            for payment in self.payments.values():
                if payment.get("reference") == reference:
                    return payment

        if amount.value <= 0:
            raise AdyenRefused("Invalid amount", result_code="Error")

        method_type = payment_method.get("type", "")
        if method_type in self.refuse:
            raise AdyenRefused(f"Refused: {method_type}", result_code="Refused")

        payment = {
            "pspReference": f"ADY{next(_ids):010d}",
            "resultCode": "Authorised",
            "amount": {"value": amount.value, "currency": amount.currency},
            "reference": reference,
        }
        self.payments[payment["pspReference"]] = payment
        return payment

    def payments_refund(self, psp_reference: str, amount: Amount | None = None) -> dict:
        self.calls += 1
        payment = self.payments.get(psp_reference)
        if payment is None:
            raise AdyenRefused(f"Unknown pspReference {psp_reference}", result_code="Error")

        value = amount.value if amount is not None else payment["amount"]["value"]
        return {
            "pspReference": f"ADY{next(_ids):010d}",
            "status": "received",
            "amount": {"value": value, "currency": payment["amount"]["currency"]},
        }
