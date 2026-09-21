"""
Abstract base class and schemas for Honey Chain MQTT ingestion abstraction.

SECURITY & ARCHITECTURAL INVARIANTS:
- Backend owns MQTT processing; mobile clients (Android) must never subscribe directly to MQTT brokers.
- Ingestion providers must support mock execution when broker credentials are not configured.
- Mock providers must clearly declare `is_mock = True`.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class MQTTMessage(BaseModel):
    """Normalized payload received from or published to an MQTT topic."""

    topic: str
    hive_id: int
    payload: Dict[str, Any]
    received_at: datetime
    is_mock: bool = True


class MQTTProvider(ABC):
    """Abstract MQTT ingestion service provider."""

    @abstractmethod
    def publish_telemetry(
        self,
        hive_id: int,
        payload: Dict[str, Any],
    ) -> bool:
        """Publish a telemetry payload to topic honeychain/hives/{hive_id}/telemetry."""
        pass

    @abstractmethod
    def register_handler(
        self,
        callback: Callable[[MQTTMessage], None],
    ) -> None:
        """Register a message callback handler for incoming telemetry."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if connected to broker or active mock."""
        pass
