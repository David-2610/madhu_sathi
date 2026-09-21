"""
Razorpay payment provider interface stub.

Isolates payment gateway SDK calls from core marketplace business logic.
Does not require live credentials during unit tests or development.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from app.models.payment import PaymentStatus
from app.services.payment.base import PaymentProvider, PaymentReceipt


class RazorpayPaymentProvider(PaymentProvider):
    """Stub implementation for future live Razorpay payment integration."""

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
    ) -> None:
        self.key_id = key_id
        self.key_secret = key_secret
        self.provider_name = "RAZORPAY"

    def create_payment_intent(
        self,
        order_id: int,
        order_number: str,
        amount: Decimal,
        currency: str = "INR",
        customer_info: Optional[Dict[str, Any]] = None,
    ) -> PaymentReceipt:
        """Create a payment order on Razorpay."""
        # When live credentials are provided in a future phase, this invokes razorpay.Client().order.create()
        # In this preparation phase, it safely returns an unconfigured or placeholder response.
        return PaymentReceipt(
            is_success=False,
            payment_reference="RZP-UNCONFIGURED",
            provider=self.provider_name,
            amount=amount,
            currency=currency,
            status=PaymentStatus.FAILED,
            is_mock=False,
            provider_metadata={"error": "Razorpay live credentials not configured"},
            created_at=datetime.now(timezone.utc),
        )

    def verify_or_capture_payment(
        self,
        payment_reference: str,
        amount: Decimal,
        currency: str = "INR",
        payload: Optional[Dict[str, Any]] = None,
    ) -> PaymentReceipt:
        """Verify webhook signature or capture payment."""
        return PaymentReceipt(
            is_success=False,
            payment_reference=payment_reference,
            provider=self.provider_name,
            amount=amount,
            currency=currency,
            status=PaymentStatus.FAILED,
            is_mock=False,
            provider_metadata={"error": "Razorpay signature verification unconfigured"},
            created_at=datetime.now(timezone.utc),
        )
