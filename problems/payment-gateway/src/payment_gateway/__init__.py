"""A payment gateway that speaks to three incompatible providers."""

from .adapters import AdyenAdapter, RazorpayAdapter, StripeAdapter
from .gateway import NoUsableProvider, PaymentGateway
from .money import Money
from .processor import PaymentProcessor, PaymentResult, PaymentStatus
from .regions import (
    EuropePaymentFactory,
    IndiaPaymentFactory,
    RegionalPaymentFactory,
    USPaymentFactory,
    factory_for,
)

__all__ = [
    "Money",
    "PaymentProcessor",
    "PaymentResult",
    "PaymentStatus",
    "StripeAdapter",
    "RazorpayAdapter",
    "AdyenAdapter",
    "PaymentGateway",
    "NoUsableProvider",
    "RegionalPaymentFactory",
    "IndiaPaymentFactory",
    "USPaymentFactory",
    "EuropePaymentFactory",
    "factory_for",
]
