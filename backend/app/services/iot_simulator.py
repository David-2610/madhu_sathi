"""
Development IoT Telemetry Simulator for Honey Chain.

Generates realistic and anomalous time-series telemetry for testing and local development.
Explicitly sets `is_simulated = True` so simulated data is never confused with real hardware.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Tuple

from sqlalchemy.orm import Session

from app.models.hive import Hive
from app.models.hive_telemetry import HiveTelemetry
from app.schemas.iot import HiveTelemetryCreate, SimulatorScenario


class IoTSimulator:
    """Telemetry scenario generator for development and automated testing."""

    @staticmethod
    def generate_payload_for_scenario(
        scenario: SimulatorScenario,
        previous_weight: Decimal = Decimal("26.50"),
    ) -> HiveTelemetryCreate:
        """Construct a HiveTelemetryCreate payload for the requested scenario."""
        now_utc = datetime.now(timezone.utc)

        if scenario == SimulatorScenario.NORMAL:
            return HiveTelemetryCreate(
                timestamp=now_utc,
                temperature_c=Decimal("34.50"),
                humidity_percent=Decimal("62.00"),
                weight_kg=previous_weight,
                sound_level=Decimal("45.00"),
                vibration_level=Decimal("0.50"),
                battery_percent=Decimal("94.00"),
                device_id="SIM-NODE-DEV",
            )

        elif scenario == SimulatorScenario.HIGH_TEMPERATURE:
            return HiveTelemetryCreate(
                timestamp=now_utc,
                temperature_c=Decimal("41.80"),  # Above critical threshold
                humidity_percent=Decimal("48.00"),
                weight_kg=previous_weight,
                sound_level=Decimal("56.00"),
                vibration_level=Decimal("0.80"),
                battery_percent=Decimal("91.00"),
                device_id="SIM-NODE-DEV",
            )

        elif scenario == SimulatorScenario.LOW_HUMIDITY:
            return HiveTelemetryCreate(
                timestamp=now_utc,
                temperature_c=Decimal("35.20"),
                humidity_percent=Decimal("24.00"),  # Well below 40%
                weight_kg=previous_weight,
                sound_level=Decimal("46.00"),
                vibration_level=Decimal("0.60"),
                battery_percent=Decimal("89.00"),
                device_id="SIM-NODE-DEV",
            )

        elif scenario == SimulatorScenario.RAPID_WEIGHT_DROP:
            # Drops 2.5kg from previous weight
            dropped_weight = max(Decimal("0.00"), previous_weight - Decimal("2.50"))
            return HiveTelemetryCreate(
                timestamp=now_utc,
                temperature_c=Decimal("34.80"),
                humidity_percent=Decimal("60.00"),
                weight_kg=dropped_weight,
                sound_level=Decimal("68.00"),
                vibration_level=Decimal("1.20"),
                battery_percent=Decimal("92.00"),
                device_id="SIM-NODE-DEV",
            )

        elif scenario == SimulatorScenario.ABNORMAL_SOUND:
            return HiveTelemetryCreate(
                timestamp=now_utc,
                temperature_c=Decimal("35.50"),
                humidity_percent=Decimal("58.00"),
                weight_kg=previous_weight,
                sound_level=Decimal("82.50"),      # Well above 75 dB
                vibration_level=Decimal("5.20"),    # Above 4.0
                battery_percent=Decimal("88.00"),
                device_id="SIM-NODE-DEV",
            )

        elif scenario == SimulatorScenario.MISSING_TELEMETRY:
            # Emits a reading timestamped 3 hours in the past
            stale_time = now_utc - timedelta(hours=3)
            return HiveTelemetryCreate(
                timestamp=stale_time,
                temperature_c=Decimal("34.20"),
                humidity_percent=Decimal("61.00"),
                weight_kg=previous_weight,
                sound_level=Decimal("44.00"),
                vibration_level=Decimal("0.40"),
                battery_percent=Decimal("12.00"),
                device_id="SIM-NODE-DEV",
            )

        # Default fallback to NORMAL
        return HiveTelemetryCreate(
            timestamp=now_utc,
            temperature_c=Decimal("34.50"),
            humidity_percent=Decimal("62.00"),
            weight_kg=previous_weight,
            sound_level=Decimal("45.00"),
            vibration_level=Decimal("0.50"),
            battery_percent=Decimal("94.00"),
            device_id="SIM-NODE-DEV",
        )
