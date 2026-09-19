"""Adapter: make three incompatible SDKs answer to one interface.

This is Adapter in its purest form -- the interface you need on one side, an
interface you cannot change on the other, and a thin class in between doing
the translation.

Each adapter absorbs four kinds of mismatch, and the fourth is the dangerous one:

1. **Method names** -- create_charge, capture_payment, payments_request
2. **Failure signalling** -- an exception, a status field, a different exception
3. **Result shape** -- "id", "razorpay_payment_id", "pspReference"
4. **Units** -- cents, paise, and a value object

Number 4 is why this layer is not optional. A bare integer amount passed to the
wrong SDK does not raise; it charges the wrong number. Every adapter takes
`Money` and converts at the boundary, so the mistake cannot be made upstream.
"""

from __future__ import annotations

from .money import Money
from .processor import PaymentProcessor, PaymentResult, PaymentStatus
from .vendor import AdyenClient, AdyenRefused, RazorpayClient, StripeClient, StripeError
from .vendor.adyen_sdk import Amount


class StripeAdapter(PaymentProcessor):
    """Stripe: amounts in cents, raises on failure."""

    name = "stripe"
    supported_currencies = frozenset({"USD", "EUR", "GBP"})

    def __init__(self, client: StripeClient):
        self.client = client

    def charge(self, amount: Money, token: str, idempotency_key: str = "") -> PaymentResult:
        try:
            charge = self.client.create_charge(
                amount_cents=amount.minor_units,
                currency=amount.currency,
                source=token,
                idempotency_key=idempotency_key or None,
            )
        except StripeError as exc:
            # A declined card is an ordinary outcome, not an exception our
            # callers should have to catch. Translating it here is the point.
            return PaymentResult(
                status=_status_for(exc.code),
                amount=amount,
                provider=self.name,
                error_code=exc.code,
                message=str(exc),
            )

        return PaymentResult(
            status=PaymentStatus.SUCCEEDED,
            amount=amount,
            provider=self.name,
            reference=charge["id"],
            raw=charge,
        )

    def refund(self, reference: str, amount: Money | None = None) -> PaymentResult:
        try:
            refund = self.client.create_refund(reference, amount.minor_units if amount else None)
        except StripeError as exc:
            return PaymentResult(
                PaymentStatus.FAILED,
                amount or Money(0),
                self.name,
                error_code=exc.code,
                message=str(exc),
            )

        return PaymentResult(
            PaymentStatus.SUCCEEDED,
            amount or Money(refund["amount"]),
            self.name,
            reference=refund["id"],
            raw=refund,
        )


class RazorpayAdapter(PaymentProcessor):
    """Razorpay: paise, and a status field instead of an exception."""

    name = "razorpay"
    supported_currencies = frozenset({"INR"})

    def __init__(self, client: RazorpayClient):
        self.client = client

    def charge(self, amount: Money, token: str, idempotency_key: str = "") -> PaymentResult:
        # Minor units are already paise for INR, but going through Money means
        # the conversion is stated rather than assumed.
        response = self.client.capture_payment(
            payment_id=token,
            amount_in_paise=amount.minor_units,
            reference=idempotency_key,
        )

        if response.get("status") != "captured":
            return PaymentResult(
                status=_status_for(response.get("error_code", "")),
                amount=amount,
                provider=self.name,
                error_code=response.get("error_code", ""),
                message=response.get("error_description", ""),
                raw=response,
            )

        return PaymentResult(
            PaymentStatus.SUCCEEDED,
            amount,
            self.name,
            reference=response["razorpay_payment_id"],
            raw=response,
        )

    def refund(self, reference: str, amount: Money | None = None) -> PaymentResult:
        response = self.client.initiate_refund(reference, amount.minor_units if amount else None)

        if response.get("status") == "failed":
            return PaymentResult(
                PaymentStatus.FAILED,
                amount or Money(0, "INR"),
                self.name,
                error_code=response.get("error_code", ""),
                message=response.get("error_description", ""),
            )

        return PaymentResult(
            PaymentStatus.SUCCEEDED,
            amount or Money(response["amount"], "INR"),
            self.name,
            reference=response["razorpay_refund_id"],
            raw=response,
        )


class AdyenAdapter(PaymentProcessor):
    """Adyen: an amount object, its own exception, and 'Authorised'."""

    name = "adyen"
    supported_currencies = frozenset({"EUR", "GBP", "USD"})

    def __init__(self, client: AdyenClient):
        self.client = client

    def charge(self, amount: Money, token: str, idempotency_key: str = "") -> PaymentResult:
        try:
            response = self.client.payments_request(
                amount=Amount(amount.minor_units, amount.currency),
                payment_method={"type": token},
                reference=idempotency_key,
            )
        except AdyenRefused as exc:
            return PaymentResult(
                status=_status_for(exc.result_code),
                amount=amount,
                provider=self.name,
                error_code=exc.result_code,
                message=str(exc),
            )

        if response.get("resultCode") != "Authorised":
            return PaymentResult(
                PaymentStatus.DECLINED,
                amount,
                self.name,
                error_code=response.get("resultCode", ""),
            )

        return PaymentResult(
            PaymentStatus.SUCCEEDED,
            amount,
            self.name,
            reference=response["pspReference"],
            raw=response,
        )

    def refund(self, reference: str, amount: Money | None = None) -> PaymentResult:
        try:
            response = self.client.payments_refund(
                reference, Amount(amount.minor_units, amount.currency) if amount else None
            )
        except AdyenRefused as exc:
            return PaymentResult(
                PaymentStatus.FAILED,
                amount or Money(0, "EUR"),
                self.name,
                error_code=exc.result_code,
                message=str(exc),
            )

        return PaymentResult(
            PaymentStatus.SUCCEEDED,
            amount or Money(response["amount"]["value"], response["amount"]["currency"]),
            self.name,
            reference=response["pspReference"],
            raw=response,
        )


#: Codes that mean "the bank said no" rather than "we sent a bad request".
#: The distinction matters: a decline is worth retrying on another provider, a
#: malformed request is not.
_DECLINE_CODES = {"card_declined", "PAYMENT_DECLINED", "Refused"}


def _status_for(code: str) -> PaymentStatus:
    return PaymentStatus.DECLINED if code in _DECLINE_CODES else PaymentStatus.FAILED
