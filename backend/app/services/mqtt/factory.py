"""
MQTT Provider factory for Honey Chain.
"""

from functools import lru_cache

from app.core.config import get_settings
from app.services.mqtt.base import MQTTProvider
from app.services.mqtt.client_provider import StandardMQTTProvider
from app.services.mqtt.mock_provider import MockMQTTProvider

settings = get_settings()


@lru_cache
def get_mqtt_provider() -> MQTTProvider:
    """Return configured MQTT provider instance."""
    provider_type = (settings.MQTT_PROVIDER or "mock").lower()
    if provider_type == "paho" and settings.MQTT_BROKER_HOST:
        return StandardMQTTProvider(
            host=settings.MQTT_BROKER_HOST,
            port=settings.MQTT_BROKER_PORT,
        )
    return MockMQTTProvider()
