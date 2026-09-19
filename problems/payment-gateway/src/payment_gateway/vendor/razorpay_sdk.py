"""A Razorpay-shaped SDK.

Amounts in **paise** (hundredths). Never raises -- returns a status dict and
expects you to check it. Different method names, different field names.
"""

from __future__ import annotations

import itertools

_ids = itertools.count(1)


class RazorpayClient:
    def __init__(self, key_id: str, key_secret: str, decline: set[str] | None = None):
        self.key_id = key_id
        self.key_secret = key_secret
        self.decline = decline or set()
        self.payments: dict[str, dict] = {}
        self.calls = 0

    def capture_payment(self, payment_id: str, amount_in_paise: int, reference: str = "") -> dict:
        """Returns {"status": "captured"|"failed", ...}. Never raises."""
        self.calls += 1

        if reference:
            for payment in self.payments.values():
                if payment.get("reference") == reference:
                    return payment

        if amount_in_paise <= 0:
            return {
                "status": "failed",
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "amount must be positive",
            }
        if payment_id in self.decline:
            return {
                "status": "failed",
                "error_code": "PAYMENT_DECLINED",
                "error_description": "payment declined by the issuing bank",
            }

        payment = {
            "razorpay_payment_id": f"pay_{next(_ids):08d}",
            "amount": amount_in_paise,
            "currency": "INR",
            "status": "captured",
            "method": payment_id,
            "reference": reference,
        }
        self.payments[payment["razorpay_payment_id"]] = payment
        return payment

    def initiate_refund(self, razorpay_payment_id: str, amount_in_paise: int | None = None):
        self.calls += 1
        payment = self.payments.get(razorpay_payment_id)
        if payment is None:
            return {
                "status": "failed",
                "error_code": "NOT_FOUND",
                "error_description": f"unknown payment {razorpay_payment_id}",
            }

        return {
            "razorpay_refund_id": f"rfnd_{next(_ids):08d}",
            "payment_id": razorpay_payment_id,
            "amount": amount_in_paise if amount_in_paise is not None else payment["amount"],
            "status": "processed",
        }
