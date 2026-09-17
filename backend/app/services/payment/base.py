"""
Abstract base class and data structures for Honey Chain payment provider abstraction.

SECURITY INVARIANTS:
- Payment credentials/secrets are never exposed to client or logs.
- Mock providers clearly identify as MOCK and never fabricate real gateway payment IDs.
- Amounts use Decimal for financial precision.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.models.payment import PaymentStatus


class PaymentReceipt(BaseModel):
    """Result of payment intent creation or payment capture/verification."""

    is_success: bool = Field(..., description="Whether the operation succeeded")
    payment_reference: str = Field(..., description="Unique provider transaction or intent identifier")
    provider: str = Field(..., description="Payment provider identifier")
    amount: Decimal = Field(..., description="Transaction amount")
    currency: str = Field("INR", description="Three-letter currency code")
    status: PaymentStatus = Field(..., description="Current payment status")
    is_mock: bool = Field(True, description="Whether this is a local mock simulation")
    provider_metadata: Optional[Dict[str, Any]] = Field(None, description="Safe metadata from provider")
    created_at: datetime = Field(..., description="Timestamp of payment action")


class PaymentProvider(ABC):
    """Abstract payment gateway provider."""

    @abstractmethod
    def create_payment_intent(
        self,
        order_id: int,
        order_number: str,
        amount: Decimal,
        currency: str = "INR",
        customer_info: Optional[Dict[str, Any]] = None,
    ) -> PaymentReceipt:
        """Initialize a payment intent for an order."""
        pass

    @abstractmethod
    def verify_or_capture_payment(
        self,
        payment_reference: str,
        amount: Decimal,
        currency: str = "INR",
        payload: Optional[Dict[str, Any]] = None,
    ) -> PaymentReceipt:
        """Verify, authorize, or capture a payment."""
        pass
