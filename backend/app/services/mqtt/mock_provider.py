"""
In-memory Mock MQTT Provider for Honey Chain local development and testing.

Explicitly identifies as MOCK and never claims real broker hardware connection.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from app.core.config import get_settings
from app.services.mqtt.base import MQTTMessage, MQTTProvider

settings = get_settings()


class MockMQTTProvider(MQTTProvider):
    """Local in-memory mock MQTT provider."""

    def __init__(self) -> None:
        self.provider_name: str = "MOCK_MQTT"
        self.is_mock: bool = True
        self.message_history: List[MQTTMessage] = []
        self._handlers: List[Callable[[MQTTMessage], None]] = []

    def publish_telemetry(
        self,
        hive_id: int,
        payload: Dict[str, Any],
    ) -> bool:
        """Publish payload to in-memory topic and dispatch to handlers."""
        topic = f"{settings.MQTT_TOPIC_PREFIX}/{hive_id}/telemetry"
        message = MQTTMessage(
            topic=topic,
            hive_id=hive_id,
            payload=payload,
            received_at=datetime.now(timezone.utc),
            is_mock=True,
        )
        self.message_history.append(message)
        for handler in self._handlers:
            try:
                handler(message)
            except Exception:
                pass
        return True

    def register_handler(
        self,
        callback: Callable[[MQTTMessage], None],
    ) -> None:
        """Register a callback for published messages."""
        self._handlers.append(callback)

    def is_connected(self) -> bool:
        """Mock provider is always active in development."""
        return True

    def clear_history(self) -> None:
        """Helper for test suites to reset message history."""
        self.message_history.clear()
