"""
Mock payment provider for development and testing.

RULES:
- Always identifies with is_mock = True.
- Never fabricates real Razorpay payment identifiers (uses prefix 'MOCK-PAY-').
- Supports deterministic capture success and failure simulation.
"""

from datetime import datetime, timezone
from decimal import Decimal
import secrets
from typing import Any, Dict, Optional

from app.models.payment import PaymentStatus
from app.services.payment.base import PaymentProvider, PaymentReceipt


class MockPaymentProvider(PaymentProvider):
    """Local in-memory mock payment provider for checkout testing."""

    def __init__(self) -> None:
        self.provider_name = "MOCK_PAYMENT"

    def create_payment_intent(
        self,
        order_id: int,
        order_number: str,
        amount: Decimal,
        currency: str = "INR",
        customer_info: Optional[Dict[str, Any]] = None,
    ) -> PaymentReceipt:
        """Create a mock payment intent with a distinctive MOCK-PAY- prefix."""
        ref = f"MOCK-PAY-{order_id:04d}-{secrets.token_hex(6).upper()}"
        return PaymentReceipt(
            is_success=True,
            payment_reference=ref,
            provider=self.provider_name,
            amount=amount,
            currency=currency,
            status=PaymentStatus.CREATED,
            is_mock=True,
            provider_metadata={
                "order_number": order_number,
                "customer_info": customer_info or {},
            },
            created_at=datetime.now(timezone.utc),
        )

    def verify_or_capture_payment(
        self,
        payment_reference: str,
        amount: Decimal,
        currency: str = "INR",
        payload: Optional[Dict[str, Any]] = None,
    ) -> PaymentReceipt:
        """Simulate payment capture or failure based on mock_success flag."""
        payload = payload or {}
        simulate_success = payload.get("mock_success", True)

        new_status = PaymentStatus.CAPTURED if simulate_success else PaymentStatus.FAILED

        return PaymentReceipt(
            is_success=simulate_success,
            payment_reference=payment_reference,
            provider=self.provider_name,
            amount=amount,
            currency=currency,
            status=new_status,
            is_mock=True,
            provider_metadata={
                "simulated": True,
                "capture_attempt_at": datetime.now(timezone.utc).isoformat(),
            },
            created_at=datetime.now(timezone.utc),
        )
