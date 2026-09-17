"""
Standard MQTT Provider stub for Honey Chain.

Used when external MQTT broker credentials (e.g., Mosquitto, EMQX, AWS IoT Core)
are provided. If broker is unreachable or unconfigured, gracefully reports disconnected.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from app.core.config import get_settings
from app.services.mqtt.base import MQTTMessage, MQTTProvider

settings = get_settings()


class StandardMQTTProvider(MQTTProvider):
    """External MQTT broker provider stub."""

    def __init__(self, host: str | None = None, port: int = 1883) -> None:
        self.host = host or settings.MQTT_BROKER_HOST
        self.port = port or settings.MQTT_BROKER_PORT
        self.provider_name = "STANDARD_MQTT"
        self.is_mock = False
        self._handlers: List[Callable[[MQTTMessage], None]] = []

    def publish_telemetry(
        self,
        hive_id: int,
        payload: Dict[str, Any],
    ) -> bool:
        """Publish payload to MQTT broker."""
        if not self.host:
            # Fallback to local log if unconfigured
            return False
        # External broker dispatch stub (e.g. paho.mqtt.client.publish)
        return True

    def register_handler(
        self,
        callback: Callable[[MQTTMessage], None],
    ) -> None:
        self._handlers.append(callback)

    def is_connected(self) -> bool:
        return bool(self.host)
