"""Runnable demo for the payment gateway.

python3 src/main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from payment_gateway import (  # noqa: E402
    AdyenAdapter,
    Money,
    NoUsableProvider,
    PaymentGateway,
    StripeAdapter,
    factory_for,
)
from payment_gateway.vendor import AdyenClient, StripeClient  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run the payment gateway demo.").parse_args(argv)

    print("1. Three SDKs that agree on nothing, behind one interface.\n")
    print(f"   {'provider':<10} {'units':<18} {'failure':<22} reference field")
    print(f"   {'-' * 10} {'-' * 18} {'-' * 22} {'-' * 16}")
    print(f"   {'stripe':<10} {'cents (int)':<18} {'raises StripeError':<22} id")
    print(
        f"   {'razorpay':<10} {'paise (int)':<18} {'returns status field':<22} razorpay_payment_id"
    )
    print(f"   {'adyen':<10} {'Amount object':<18} {'raises AdyenRefused':<22} pspReference")

    print("\n2. One call shape, whichever one answers.\n")
    for region in ("US", "IN", "EU"):
        factory = factory_for(region)
        gateway = PaymentGateway.for_region(factory)
        result = gateway.charge(factory.money(49.99), "tok_ok")
        print(f"   {region}  {result}")

    print("\n3. Abstract Factory: the family members have to agree.\n")
    for region in ("US", "IN", "EU"):
        factory = factory_for(region)
        formatter = factory.create_formatter()
        tax = factory.create_tax_calculator()
        net = factory.money(1234567)
        print(
            f"   {factory.region:<14} {formatter.format(net):>18}"
            f"  + {tax.name:<10} = {formatter.format(tax.total_with_tax(net)):>18}"
        )
    print("\n   A GST calculator with a US formatter would be wrong twice over,")
    print("   so there is no way to ask for one.")

    print("\n4. A decline falls back. A bad request does not.\n")
    gateway = PaymentGateway(
        [
            StripeAdapter(StripeClient("sk_test", fail_on={"tok_declined"})),
            AdyenAdapter(AdyenClient("Merchant")),
        ]
    )
    result = gateway.charge(Money.of(25, "USD"), "tok_declined")
    print(f"   declined card: tried {[n for n, _ in gateway.attempts]} -> {result}")

    gateway.attempts.clear()
    result = gateway.charge(Money(0, "USD"), "tok_ok")
    print(f"   zero amount:   tried {[n for n, _ in gateway.attempts]} -> {result}")
    print("   (retrying a malformed request just produces the same error, slower)")

    print("\n5. Idempotency: a flaky client retrying must not charge twice.\n")
    stripe_client = StripeClient("sk_test")
    gateway = PaymentGateway([StripeAdapter(stripe_client)])
    for attempt in range(4):
        result = gateway.charge(Money.of(99, "USD"), "tok_ok", idempotency_key="order-42")
        print(f"   attempt {attempt + 1}: {result.reference}")
    print(
        f"   {len(stripe_client.charges)} charge created, "
        f"{stripe_client.calls} SDK call for 4 attempts"
    )

    print("\n6. A currency nobody configured is an error, not a wrong charge.\n")
    try:
        PaymentGateway.for_region(factory_for("IN")).charge(Money.of(10, "USD"), "tok_ok")
    except NoUsableProvider as exc:
        print(f"   {exc}")

    print("\n7. Refunds go back through whoever actually took the money.\n")
    gateway = PaymentGateway(
        [
            StripeAdapter(StripeClient("sk_test", fail_on={"tok_declined"})),
            AdyenAdapter(AdyenClient("Merchant")),
        ]
    )
    charge = gateway.charge(Money.of(30, "EUR"), "tok_declined")
    print(f"   charged via {charge.provider}")
    print(f"   refunded via {gateway.refund(charge).provider}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
