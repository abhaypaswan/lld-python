"""Third-party SDKs, as they would actually arrive.

Nothing in this package is ours. These classes stand in for vendor libraries:
you cannot change them, they disagree with each other about everything, and at
least one of them will do something you consider a mistake.

They are deliberately awkward, because that awkwardness is the entire reason
the Adapter layer exists. If the fakes were tidy, the adapters would look like
pointless indirection.
"""

from .adyen_sdk import AdyenClient, AdyenRefused
from .razorpay_sdk import RazorpayClient
from .stripe_sdk import StripeClient, StripeError

__all__ = [
    "StripeClient",
    "StripeError",
    "RazorpayClient",
    "AdyenClient",
    "AdyenRefused",
]
