"""Abstract Factory: a matched set of region-specific pieces.

A region needs three things that must agree with each other:

- a **processor** that supports the local currency
- a **tax calculator** with the local rules
- a **formatter** that renders money the way the region writes it

Mixing them is not a style problem, it is a wrong invoice: a GST calculator
with a USD formatter produces a document that is incorrect twice over.

That is exactly what Abstract Factory is for -- creating *families* of related
objects where the members must be consistent. A plain factory per product would
let a caller assemble an inconsistent set; here there is no way to ask for one.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .adapters import AdyenAdapter, RazorpayAdapter, StripeAdapter
from .money import Money
from .processor import PaymentProcessor
from .vendor import AdyenClient, RazorpayClient, StripeClient


class TaxCalculator(ABC):
    name: str = "tax"

    @abstractmethod
    def tax_on(self, amount: Money) -> Money: ...

    def total_with_tax(self, amount: Money) -> Money:
        return amount + self.tax_on(amount)


class GSTCalculator(TaxCalculator):
    name = "GST"

    def __init__(self, rate: float = 0.18):
        self.rate = rate

    def tax_on(self, amount: Money) -> Money:
        return amount * self.rate


class SalesTaxCalculator(TaxCalculator):
    name = "Sales Tax"

    def __init__(self, rate: float = 0.0875):
        self.rate = rate

    def tax_on(self, amount: Money) -> Money:
        return amount * self.rate


class VATCalculator(TaxCalculator):
    name = "VAT"

    def __init__(self, rate: float = 0.20):
        self.rate = rate

    def tax_on(self, amount: Money) -> Money:
        return amount * self.rate


class MoneyFormatter(ABC):
    @abstractmethod
    def format(self, amount: Money) -> str: ...


class IndianFormatter(MoneyFormatter):
    """Lakh/crore grouping: 12,34,567.00 rather than 1,234,567.00."""

    def format(self, amount: Money) -> str:
        whole, _, fraction = f"{amount.major_units:.2f}".partition(".")
        if len(whole) > 3:
            head, tail = whole[:-3], whole[-3:]
            groups = []
            while len(head) > 2:
                groups.insert(0, head[-2:])
                head = head[:-2]
            if head:
                groups.insert(0, head)
            whole = ",".join([*groups, tail])
        return f"₹{whole}.{fraction}"


class USFormatter(MoneyFormatter):
    def format(self, amount: Money) -> str:
        return f"${amount.major_units:,.2f}"


class EuroFormatter(MoneyFormatter):
    """Dots for thousands, comma for decimals, symbol trailing."""

    def format(self, amount: Money) -> str:
        text = f"{amount.major_units:,.2f}"
        return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".") + " €"


class RegionalPaymentFactory(ABC):
    """Creates one consistent set of region-specific collaborators."""

    region: str = ""
    currency: str = ""

    @abstractmethod
    def create_processor(self) -> PaymentProcessor: ...

    @abstractmethod
    def create_tax_calculator(self) -> TaxCalculator: ...

    @abstractmethod
    def create_formatter(self) -> MoneyFormatter: ...

    def money(self, major: float) -> Money:
        """Build an amount already in this region's currency."""
        return Money.of(major, self.currency)

    def __str__(self) -> str:
        return f"{self.region} ({self.currency})"


class IndiaPaymentFactory(RegionalPaymentFactory):
    region = "India"
    currency = "INR"

    def __init__(self, decline: set[str] | None = None):
        self._client = RazorpayClient("rzp_test", "secret", decline=decline)

    def create_processor(self) -> PaymentProcessor:
        return RazorpayAdapter(self._client)

    def create_tax_calculator(self) -> TaxCalculator:
        return GSTCalculator()

    def create_formatter(self) -> MoneyFormatter:
        return IndianFormatter()


class USPaymentFactory(RegionalPaymentFactory):
    region = "United States"
    currency = "USD"

    def __init__(self, fail_on: set[str] | None = None):
        self._client = StripeClient("sk_test_123", fail_on=fail_on)

    def create_processor(self) -> PaymentProcessor:
        return StripeAdapter(self._client)

    def create_tax_calculator(self) -> TaxCalculator:
        return SalesTaxCalculator()

    def create_formatter(self) -> MoneyFormatter:
        return USFormatter()


class EuropePaymentFactory(RegionalPaymentFactory):
    region = "Europe"
    currency = "EUR"

    def __init__(self, refuse: set[str] | None = None):
        self._client = AdyenClient("MerchantAccount", refuse=refuse)

    def create_processor(self) -> PaymentProcessor:
        return AdyenAdapter(self._client)

    def create_tax_calculator(self) -> TaxCalculator:
        return VATCalculator()

    def create_formatter(self) -> MoneyFormatter:
        return EuroFormatter()


FACTORIES: dict[str, type[RegionalPaymentFactory]] = {
    "IN": IndiaPaymentFactory,
    "US": USPaymentFactory,
    "EU": EuropePaymentFactory,
}


def factory_for(region_code: str, **kwargs) -> RegionalPaymentFactory:
    try:
        return FACTORIES[region_code.upper()](**kwargs)
    except KeyError:
        known = ", ".join(sorted(FACTORIES))
        raise ValueError(f"No factory for region {region_code!r}. Known: {known}") from None
