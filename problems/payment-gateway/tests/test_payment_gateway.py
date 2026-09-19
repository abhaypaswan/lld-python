"""Adapters over hostile SDKs, and families that must stay consistent."""

import pytest
from payment_gateway import (
    AdyenAdapter,
    EuropePaymentFactory,
    IndiaPaymentFactory,
    Money,
    NoUsableProvider,
    PaymentGateway,
    PaymentStatus,
    RazorpayAdapter,
    StripeAdapter,
    USPaymentFactory,
    factory_for,
)
from payment_gateway.regions import GSTCalculator, SalesTaxCalculator, VATCalculator
from payment_gateway.vendor import AdyenClient, RazorpayClient, StripeClient


@pytest.fixture
def stripe():
    return StripeAdapter(StripeClient("sk_test_1", fail_on={"tok_declined"}))


@pytest.fixture
def razorpay():
    return RazorpayAdapter(RazorpayClient("rzp", "secret", decline={"upi_declined"}))


@pytest.fixture
def adyen():
    return AdyenAdapter(AdyenClient("Merchant", refuse={"refused_card"}))


# -- money ----------------------------------------------------------------


def test_major_units_convert_to_minor():
    assert Money.of(12.50, "USD").minor_units == 1250


def test_a_currency_without_minor_units_is_handled():
    """Not every currency is hundredths. The yen has none."""
    assert Money.of(1250, "JPY").minor_units == 1250


def test_money_round_trips():
    assert Money.of(99.99, "EUR").major_units == 99.99


def test_currencies_cannot_be_mixed_silently():
    with pytest.raises(ValueError, match="without a rate"):
        Money.of(1, "USD") + Money.of(1, "EUR")


def test_an_unknown_currency_lists_the_known_ones():
    with pytest.raises(ValueError, match="EUR, GBP"):
        Money(100, "XYZ")


def test_money_cannot_be_negative():
    with pytest.raises(ValueError, match="cannot be negative"):
        Money(-1, "USD")


# -- adapters: one interface over three shapes ----------------------------


def test_every_adapter_answers_the_same_interface(stripe, razorpay, adyen):
    charges = [
        stripe.charge(Money.of(10, "USD"), "tok_ok"),
        razorpay.charge(Money.of(10, "INR"), "upi_ok"),
        adyen.charge(Money.of(10, "EUR"), "scheme"),
    ]

    assert all(result.succeeded for result in charges)
    assert {r.provider for r in charges} == {"stripe", "razorpay", "adyen"}


def test_an_exception_becomes_a_declined_result(stripe):
    """Stripe raises. Our callers must not have to catch a vendor exception."""
    result = stripe.charge(Money.of(10, "USD"), "tok_declined")

    assert not result.succeeded
    assert result.status is PaymentStatus.DECLINED
    assert result.error_code == "card_declined"


def test_a_status_field_becomes_a_declined_result(razorpay):
    """Razorpay never raises; it returns a status nobody remembers to check."""
    result = razorpay.charge(Money.of(10, "INR"), "upi_declined")

    assert not result.succeeded
    assert result.status is PaymentStatus.DECLINED


def test_a_vendor_specific_exception_becomes_a_declined_result(adyen):
    result = adyen.charge(Money.of(10, "EUR"), "refused_card")

    assert not result.succeeded
    assert result.status is PaymentStatus.DECLINED


def test_a_bad_request_is_failed_not_declined(stripe):
    """A decline is worth retrying elsewhere; a malformed request is not."""
    result = stripe.charge(Money(0, "USD"), "tok_ok")

    assert result.status is PaymentStatus.FAILED


def test_each_adapter_reports_its_own_reference_field(stripe, razorpay, adyen):
    assert stripe.charge(Money.of(5, "USD"), "tok_ok").reference.startswith("ch_")
    assert razorpay.charge(Money.of(5, "INR"), "upi_ok").reference.startswith("pay_")
    assert adyen.charge(Money.of(5, "EUR"), "scheme").reference.startswith("ADY")


def test_the_adapter_converts_units_at_the_boundary(stripe):
    """The 100x bug: the SDK wants cents, the caller thinks in dollars."""
    stripe.charge(Money.of(12.34, "USD"), "tok_ok")

    charge = next(iter(stripe.client.charges.values()))
    assert charge["amount"] == 1234


def test_adapters_declare_the_currencies_they_take(stripe, razorpay):
    assert stripe.supports("USD")
    assert not stripe.supports("INR")
    assert razorpay.supports("INR")


def test_a_refund_goes_back_through_the_same_shape(stripe):
    charge = stripe.charge(Money.of(20, "USD"), "tok_ok")

    refund = stripe.refund(charge.reference)

    assert refund.succeeded


def test_a_partial_refund_is_supported(razorpay):
    charge = razorpay.charge(Money.of(100, "INR"), "upi_ok")

    refund = razorpay.refund(charge.reference, Money.of(40, "INR"))

    assert refund.succeeded
    assert refund.amount == Money.of(40, "INR")


def test_refunding_an_unknown_reference_fails_cleanly(adyen):
    result = adyen.refund("ADY-nope")

    assert not result.succeeded
    assert result.status is PaymentStatus.FAILED


# -- abstract factory -----------------------------------------------------


@pytest.mark.parametrize(
    "factory_class,currency,tax,processor",
    [
        (USPaymentFactory, "USD", SalesTaxCalculator, "stripe"),
        (IndiaPaymentFactory, "INR", GSTCalculator, "razorpay"),
        (EuropePaymentFactory, "EUR", VATCalculator, "adyen"),
    ],
)
def test_a_factory_produces_a_consistent_family(factory_class, currency, tax, processor):
    """The point of Abstract Factory: the members must agree with each other."""
    factory = factory_class()

    assert factory.currency == currency
    assert isinstance(factory.create_tax_calculator(), tax)
    assert factory.create_processor().name == processor


def test_a_factorys_processor_accepts_its_own_currency():
    for code in ("US", "IN", "EU"):
        factory = factory_for(code)

        assert factory.create_processor().supports(factory.currency)


def test_formatters_differ_per_region():
    amount = 1234567.0

    us = USPaymentFactory()
    india = IndiaPaymentFactory()
    europe = EuropePaymentFactory()

    assert us.create_formatter().format(us.money(amount)) == "$1,234,567.00"
    assert india.create_formatter().format(india.money(amount)) == "₹12,34,567.00"
    assert europe.create_formatter().format(europe.money(amount)) == "1.234.567,00 €"


def test_tax_rates_differ_per_region():
    hundred_us = USPaymentFactory().money(100)
    hundred_in = IndiaPaymentFactory().money(100)

    assert SalesTaxCalculator().tax_on(hundred_us) == Money.of(8.75, "USD")
    assert GSTCalculator().tax_on(hundred_in) == Money.of(18, "INR")


def test_tax_is_added_in_the_same_currency():
    factory = IndiaPaymentFactory()
    total = factory.create_tax_calculator().total_with_tax(factory.money(100))

    assert total.currency == "INR"
    assert total == Money.of(118, "INR")


def test_an_unknown_region_lists_the_known_ones():
    with pytest.raises(ValueError, match="EU, IN, US"):
        factory_for("ZZ")


# -- the gateway ----------------------------------------------------------


def test_the_gateway_charges_through_its_processor(stripe):
    gateway = PaymentGateway([stripe])

    assert gateway.charge(Money.of(10, "USD"), "tok_ok").succeeded


def test_a_decline_falls_back_to_the_next_provider(stripe, adyen):
    gateway = PaymentGateway([stripe, adyen])

    result = gateway.charge(Money.of(10, "USD"), "tok_declined")

    assert result.succeeded
    assert result.provider == "adyen"
    assert [name for name, _ in gateway.attempts] == ["stripe", "adyen"]


def test_a_bad_request_does_not_fall_back(stripe, adyen):
    """Retrying a malformed request just produces the same error more slowly."""
    gateway = PaymentGateway([stripe, adyen])

    gateway.charge(Money(0, "USD"), "tok_ok")

    assert [name for name, _ in gateway.attempts] == ["stripe"]


def test_a_provider_that_cannot_take_the_currency_is_skipped(stripe, razorpay):
    gateway = PaymentGateway([razorpay, stripe])

    result = gateway.charge(Money.of(10, "USD"), "tok_ok")

    assert result.provider == "stripe"
    assert [name for name, _ in gateway.attempts] == ["stripe"]


def test_no_provider_for_the_currency_is_an_error(razorpay):
    gateway = PaymentGateway([razorpay])

    with pytest.raises(NoUsableProvider, match="accepts USD"):
        gateway.charge(Money.of(10, "USD"), "tok_ok")


def test_every_provider_declining_returns_the_last_failure(stripe, adyen):
    gateway = PaymentGateway([stripe, adyen])

    result = gateway.charge(Money.of(10, "USD"), "tok_declined")
    assert result.succeeded  # adyen accepts this token

    gateway_all_bad = PaymentGateway(
        [
            StripeAdapter(StripeClient("sk_a", fail_on={"tok_x"})),
            AdyenAdapter(AdyenClient("M", refuse={"tok_x"})),
        ]
    )
    result = gateway_all_bad.charge(Money.of(10, "USD"), "tok_x")

    assert not result.succeeded


# -- idempotency ----------------------------------------------------------


def test_the_same_key_charges_once(stripe):
    gateway = PaymentGateway([stripe])
    first = gateway.charge(Money.of(10, "USD"), "tok_ok", idempotency_key="order-1")
    second = gateway.charge(Money.of(10, "USD"), "tok_ok", idempotency_key="order-1")

    assert first.reference == second.reference
    assert len(stripe.client.charges) == 1


def test_a_repeated_key_does_not_contact_the_provider(stripe):
    """The gateway answers from its own record, so a retry costs nothing."""
    gateway = PaymentGateway([stripe])
    gateway.charge(Money.of(10, "USD"), "tok_ok", idempotency_key="order-1")
    calls_after_first = stripe.client.calls

    gateway.charge(Money.of(10, "USD"), "tok_ok", idempotency_key="order-1")

    assert stripe.client.calls == calls_after_first


def test_different_keys_charge_separately(stripe):
    gateway = PaymentGateway([stripe])
    gateway.charge(Money.of(10, "USD"), "tok_ok", idempotency_key="order-1")
    gateway.charge(Money.of(10, "USD"), "tok_ok", idempotency_key="order-2")

    assert len(stripe.client.charges) == 2


def test_no_key_means_no_deduplication(stripe):
    gateway = PaymentGateway([stripe])
    gateway.charge(Money.of(10, "USD"), "tok_ok")
    gateway.charge(Money.of(10, "USD"), "tok_ok")

    assert len(stripe.client.charges) == 2


def test_idempotency_survives_at_the_provider_too(stripe):
    """Belt and braces: the SDK honours the key even without our record."""
    first = stripe.charge(Money.of(10, "USD"), "tok_ok", idempotency_key="k1")
    second = stripe.charge(Money.of(10, "USD"), "tok_ok", idempotency_key="k1")

    assert first.reference == second.reference


def test_a_declined_charge_is_not_remembered_as_complete(stripe, adyen):
    gateway = PaymentGateway([stripe])
    gateway.charge(Money.of(10, "USD"), "tok_declined", idempotency_key="order-9")

    gateway.add_processor(adyen)
    retry = gateway.charge(Money.of(10, "USD"), "tok_declined", idempotency_key="order-9")

    assert retry.succeeded, "a failed attempt must not block a later successful one"


# -- refunds through the gateway ------------------------------------------


def test_a_refund_goes_to_the_provider_that_took_the_money(stripe, adyen):
    gateway = PaymentGateway([stripe, adyen])
    charge = gateway.charge(Money.of(10, "USD"), "tok_declined")
    assert charge.provider == "adyen"

    refund = gateway.refund(charge)

    assert refund.provider == "adyen"


def test_refunding_through_a_removed_provider_is_an_error(stripe):
    gateway = PaymentGateway([stripe])
    charge = gateway.charge(Money.of(10, "USD"), "tok_ok")
    gateway.processors.clear()

    with pytest.raises(NoUsableProvider, match="no longer configured"):
        gateway.refund(charge)


# -- end to end -----------------------------------------------------------


@pytest.mark.parametrize("region", ["US", "IN", "EU"])
def test_a_full_regional_charge(region):
    factory = factory_for(region)
    gateway = PaymentGateway.for_region(factory)
    tax = factory.create_tax_calculator()

    total = tax.total_with_tax(factory.money(100))
    result = gateway.charge(total, "tok_ok")

    assert result.succeeded
    assert result.amount.currency == factory.currency
