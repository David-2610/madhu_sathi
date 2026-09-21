"""
Payment provider factory for Honey Chain.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.services.payment.base import PaymentProvider
from app.services.payment.mock_provider import MockPaymentProvider
from app.services.payment.razorpay_provider import RazorpayPaymentProvider


@lru_cache
def get_payment_provider() -> PaymentProvider:
    """
    Resolve and return configured PaymentProvider instance.

    Defaults safely to MockPaymentProvider.
    """
    settings = get_settings()
    provider_type = getattr(settings, "PAYMENT_PROVIDER", "mock").lower()

    if provider_type == "razorpay":
        return RazorpayPaymentProvider()

    return MockPaymentProvider()
