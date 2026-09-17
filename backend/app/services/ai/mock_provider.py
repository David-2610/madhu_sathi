"""
Mock AI Provider for Honey Chain local development and testing.

Provides deterministic, expert-level explanations of telemetry patterns and anomalies
without making external API calls or hallucinating disease certainty.
"""

from typing import Any, Dict, List, Optional

from app.services.ai.base import AIExplanation, AIProvider


class MockAIProvider(AIProvider):
    """Deterministic mock AI assistance provider."""

    def __init__(self) -> None:
        self.provider_name: str = "MOCK_AI"
        self.is_mock: bool = True

    def generate_explanation(
        self,
        hive_id: int,
        hive_code: str,
        metrics_summary: Dict[str, Any],
        anomalies: List[str],
        query: Optional[str] = None,
    ) -> AIExplanation:
        """Generate structured contextual explanation and inspection recommendations."""
        # 1. Condition Summary
        temp = metrics_summary.get("temperature_c")
        hum = metrics_summary.get("humidity_percent")
        weight = metrics_summary.get("weight_kg")

        if not anomalies:
            condition_summary = (
                f"Hive {hive_code} telemetry is within normal parameters. "
                f"Temperature is steady at {temp}°C, humidity at {hum}%, and scale weight at {weight} kg."
            )
            explanation = (
                "The brood nest climate appears well-regulated by the colony. "
                "No environmental stress, overheating, or acute weight fluctuations detected."
            )
            recommended_steps = [
                "Continue standard bi-weekly apiary monitoring routine.",
                "Ensure fresh water sources remain available near the apiary.",
                "Verify hive entrance reducer position according to current seasonal weather.",
            ]
        else:
            anomaly_str = ", ".join(anomalies)
            condition_summary = (
                f"Possible abnormal hive condition detected in Hive {hive_code}. "
                f"Active anomalies identified: {anomaly_str}."
            )
            explanation_parts: List[str] = []
            steps: List[str] = []

            for anomaly in anomalies:
                anomaly_upper = anomaly.upper()
                if "TEMPERATURE" in anomaly_upper or "HEAT" in anomaly_upper:
                    explanation_parts.append(
                        f"Internal temperature reading ({temp}°C) deviates from optimal brood maintenance range (32.0°C - 37.0°C). "
                        "This may be caused by direct sun exposure, high ambient temperature, or reduced cluster thermoregulation."
                    )
                    steps.extend([
                        "Check hive exterior for shade and ensure upper ventilation vents are not blocked with propolis.",
                        "Verify clean water availability within 100 meters to aid colony evaporative cooling.",
                    ])
                elif "HUMIDITY" in anomaly_upper:
                    explanation_parts.append(
                        f"Internal humidity ({hum}%) is outside target levels (40% - 75%). "
                        "Extreme humidity shifts can affect nectar curing or cause condensation."
                    )
                    steps.extend([
                        "Inspect hive bottom board and roof for condensation or moisture accumulation.",
                        "Check hive entrance orientation relative to prevailing winds.",
                    ])
                elif "WEIGHT" in anomaly_upper:
                    explanation_parts.append(
                        f"A sudden scale weight reduction was recorded (current weight: {weight} kg). "
                        "Rapid weight loss may suggest swarming activity, supers removal, or predator disturbance."
                    )
                    steps.extend([
                        "Conduct an immediate gentle physical check to see if a swarm has left the hive.",
                        "Inspect brood frames for swarm cells and check remaining honey stores.",
                    ])
                elif "SOUND" in anomaly_upper or "VIBRATION" in anomaly_upper:
                    explanation_parts.append(
                        "Elevated sound or vibration telemetry indicates heightened colony agitation or potential physical disturbance."
                    )
                    steps.extend([
                        "Inspect hive perimeter for signs of pests, ants, wasps, or animals bumping the hive stand.",
                        "Listen at the hive entrance during dusk to observe if agitation calms down.",
                    ])
                elif "MISSING" in anomaly_upper or "STALE" in anomaly_upper:
                    explanation_parts.append(
                        "Telemetry data has not been received within the expected timeframe. "
                        "The sensor node may have suffered power loss or radio connection interruption."
                    )
                    steps.extend([
                        "Verify device battery level and solar panel charging status.",
                        "Check antenna position and local gateway or cellular connectivity.",
                    ])

            if not explanation_parts:
                explanation_parts.append(
                    f"Sensor patterns showed unusual readings: {anomaly_str}. "
                    "Physical verification is recommended."
                )
                steps.append("Perform a standard visual inspection of the hive entrance and bottom board.")

            explanation = " ".join(explanation_parts)
            # Deduplicate steps preserving order
            seen = set()
            recommended_steps = [s for s in steps if not (s in seen or seen.add(s))]

        # If user asked a specific question, integrate answer
        if query:
            explanation = (
                f"In response to your question ('{query}'): {explanation}"
            )

        return AIExplanation(
            condition_summary=condition_summary,
            explanation=explanation,
            recommended_steps=recommended_steps,
            disclaimer=(
                "Possible abnormal hive condition detected. Note: Telemetry anomalies indicate "
                "environmental or behavioral variations and do NOT constitute a confirmed disease diagnosis. "
                "Physical hive inspection is required."
            ),
            is_mock=True,
            provider="MOCK_AI",
        )
