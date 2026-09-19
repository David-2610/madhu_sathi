"""
Hive Health Engine & Anomaly Detection Service.

Provides:
- Rule-based threshold evaluation
- Rate-of-change analysis (sudden weight loss, temperature spikes)
- Alert generation with deduplication / cooldown
- Comprehensive health status summarization

SECURITY & BIOLOGICAL INVARIANTS:
- An anomaly is NOT automatically a confirmed bee disease.
- Always use non-diagnostic phrasing: "Possible abnormal hive condition detected."
- Never claim "Disease confirmed."
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.hive import Hive
from app.models.hive_alert import AlertSeverity, AlertStatus, AlertType, HiveAlert
from app.models.hive_device import HiveDevice
from app.models.hive_telemetry import HiveTelemetry
from app.schemas.iot import (
    HiveAlertResponse,
    HiveHealthMetrics,
    HiveHealthSummaryResponse,
    HiveTelemetryResponse,
)

settings = get_settings()


class HealthEngine:
    """Service evaluating telemetry, detecting anomalies, and managing alerts."""

    @staticmethod
    def evaluate_telemetry(
        db: Session,
        hive: Hive,
        reading: HiveTelemetry,
    ) -> Tuple[AlertSeverity, List[str], List[HiveAlert]]:
        """
        Evaluate a single telemetry reading against historical baselines and thresholds.

        Returns:
            (max_severity, detected_anomalies_list, new_or_existing_alerts_list)
        """
        anomalies: List[str] = []
        max_severity = AlertSeverity.NORMAL
        alerts_to_emit: List[dict] = []

        temp = float(reading.temperature_c)
        hum = float(reading.humidity_percent)
        weight = float(reading.weight_kg)
        sound = float(reading.sound_level)
        vibration = float(reading.vibration_level)

        # 1. Temperature Analysis
        if temp >= settings.HIVE_TEMP_CRITICAL_HIGH_C:
            anomalies.append("CRITICAL_HIGH_TEMPERATURE")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.CRITICAL)
            alerts_to_emit.append({
                "alert_type": AlertType.HIGH_TEMPERATURE.value,
                "severity": AlertSeverity.CRITICAL,
                "title": "Possible abnormal hive condition detected: Critical high temperature",
                "message": (
                    f"Brood nest temperature reached {temp:.1f}°C, critically exceeding safe limit "
                    f"({settings.HIVE_TEMP_CRITICAL_HIGH_C:.1f}°C). Severe thermal stress possible."
                ),
                "recommended_action": (
                    "Inspect hive immediately. Provide emergency shade, ensure top ventilation is unobstructed, "
                    "and supply clean drinking water near the hive stand."
                ),
            })
        elif temp > settings.HIVE_TEMP_BROOD_MAX_C:
            anomalies.append("HIGH_TEMPERATURE")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.HIGH)
            alerts_to_emit.append({
                "alert_type": AlertType.HIGH_TEMPERATURE.value,
                "severity": AlertSeverity.HIGH,
                "title": "Possible abnormal hive condition detected: High temperature",
                "message": (
                    f"Brood temperature recorded at {temp:.1f}°C, above normal brood nest range "
                    f"({settings.HIVE_TEMP_BROOD_MIN_C:.1f}°C - {settings.HIVE_TEMP_BROOD_MAX_C:.1f}°C)."
                ),
                "recommended_action": (
                    "Check hive ventilation and shade during peak sun hours. Verify water availability."
                ),
            })
        elif temp <= settings.HIVE_TEMP_CRITICAL_LOW_C:
            anomalies.append("CRITICAL_LOW_TEMPERATURE")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.CRITICAL)
            alerts_to_emit.append({
                "alert_type": AlertType.LOW_TEMPERATURE.value,
                "severity": AlertSeverity.CRITICAL,
                "title": "Possible abnormal hive condition detected: Critical low temperature",
                "message": (
                    f"Internal temperature plummeted to {temp:.1f}°C, below critical cluster threshold "
                    f"({settings.HIVE_TEMP_CRITICAL_LOW_C:.1f}°C). Brood chilling risk."
                ),
                "recommended_action": (
                    "Inspect hive for wind drafts, dampness, or broken cluster. Reduce entrance size."
                ),
            })
        elif temp < settings.HIVE_TEMP_BROOD_MIN_C:
            anomalies.append("LOW_TEMPERATURE")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.MEDIUM)
            alerts_to_emit.append({
                "alert_type": AlertType.LOW_TEMPERATURE.value,
                "severity": AlertSeverity.MEDIUM,
                "title": "Possible abnormal hive condition detected: Low temperature",
                "message": (
                    f"Temperature dropped to {temp:.1f}°C, lower than normal brood thermoregulation range."
                ),
                "recommended_action": (
                    "Monitor night temperatures and check entrance reducers."
                ),
            })

        # 2. Humidity Analysis
        if hum < settings.HIVE_HUMIDITY_MIN_PERCENT:
            anomalies.append("LOW_HUMIDITY")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.MEDIUM)
            alerts_to_emit.append({
                "alert_type": AlertType.LOW_HUMIDITY.value,
                "severity": AlertSeverity.MEDIUM,
                "title": "Possible abnormal hive condition detected: Low humidity",
                "message": (
                    f"Internal humidity measured at {hum:.1f}%, below minimum recommended level "
                    f"({settings.HIVE_HUMIDITY_MIN_PERCENT:.1f}%). Larval dehydration risk."
                ),
                "recommended_action": (
                    "Ensure adequate clean water source is accessible near apiary."
                ),
            })
        elif hum > settings.HIVE_HUMIDITY_MAX_PERCENT:
            anomalies.append("HIGH_HUMIDITY")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.MEDIUM)
            alerts_to_emit.append({
                "alert_type": AlertType.HIGH_HUMIDITY.value,
                "severity": AlertSeverity.MEDIUM,
                "title": "Possible abnormal hive condition detected: High humidity",
                "message": (
                    f"Internal humidity reached {hum:.1f}%, exceeding recommended maximum "
                    f"({settings.HIVE_HUMIDITY_MAX_PERCENT:.1f}%). Condensation or poor air circulation possible."
                ),
                "recommended_action": (
                    "Check bottom board debris and ensure roof ventilation prevents moisture accumulation."
                ),
            })

        # 3. Rate-of-change: Sudden Hive Weight Drop
        prev_reading = (
            db.query(HiveTelemetry)
            .filter(
                HiveTelemetry.hive_id == hive.id,
                HiveTelemetry.id != reading.id,
                HiveTelemetry.timestamp < reading.timestamp,
            )
            .order_by(HiveTelemetry.timestamp.desc())
            .first()
        )

        if prev_reading is not None:
            prev_weight = float(prev_reading.weight_kg)
            weight_drop = prev_weight - weight
            if weight_drop >= settings.HIVE_WEIGHT_DROP_ALERT_KG:
                anomalies.append("RAPID_WEIGHT_DROP")
                max_severity = HealthEngine._escalate(max_severity, AlertSeverity.HIGH)
                alerts_to_emit.append({
                    "alert_type": AlertType.RAPID_WEIGHT_DROP.value,
                    "severity": AlertSeverity.HIGH,
                    "title": "Possible abnormal hive condition detected: Rapid weight reduction",
                    "message": (
                        f"Hive scale recorded a sudden drop of {weight_drop:.2f} kg (from {prev_weight:.2f} kg "
                        f"to {weight:.2f} kg). Potential swarming event or unauthorized supers removal."
                    ),
                    "recommended_action": (
                        "Perform an immediate visual inspection of the hive and surrounding trees for a newly "
                        "emerged swarm cluster. Check brood frames for presence of queen and swarm cells."
                    ),
                })

        # 4. Sound & Vibration Agitation Analysis
        if sound >= settings.HIVE_SOUND_ALERT_DB and vibration >= settings.HIVE_VIBRATION_ALERT:
            anomalies.append("COMBINED_AGITATION_ANOMALY")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.HIGH)
            alerts_to_emit.append({
                "alert_type": AlertType.COMBINED_ANOMALY.value,
                "severity": AlertSeverity.HIGH,
                "title": "Possible abnormal hive condition detected: High sound and vibration",
                "message": (
                    f"Elevated acoustic activity ({sound:.1f} dB) and vibration ({vibration:.1f}) detected simultaneously. "
                    "Colony appears heavily agitated. Possible physical disturbance or pest intrusion."
                ),
                "recommended_action": (
                    "Inspect hive stand stability and perimeter for predators, wasps, rodents, or physical disturbance."
                ),
            })
        elif sound >= settings.HIVE_SOUND_ALERT_DB:
            anomalies.append("ABNORMAL_SOUND")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.MEDIUM)
            alerts_to_emit.append({
                "alert_type": AlertType.ABNORMAL_SOUND.value,
                "severity": AlertSeverity.MEDIUM,
                "title": "Possible abnormal hive condition detected: High acoustic level",
                "message": (
                    f"Sound level reached {sound:.1f} dB, exceeding threshold ({settings.HIVE_SOUND_ALERT_DB:.1f} dB). "
                    "May indicate piping, queenlessness roar, or defensive buzz."
                ),
                "recommended_action": (
                    "Observe flight activity at entrance; check colony temperament during next inspection."
                ),
            })
        elif vibration >= settings.HIVE_VIBRATION_ALERT:
            anomalies.append("ABNORMAL_VIBRATION")
            max_severity = HealthEngine._escalate(max_severity, AlertSeverity.MEDIUM)
            alerts_to_emit.append({
                "alert_type": AlertType.ABNORMAL_VIBRATION.value,
                "severity": AlertSeverity.MEDIUM,
                "title": "Possible abnormal hive condition detected: Abnormal vibration",
                "message": (
                    f"Vibration level ({vibration:.1f}) exceeded threshold ({settings.HIVE_VIBRATION_ALERT:.1f}). "
                    "Physical shaking or wind gusts detected."
                ),
                "recommended_action": (
                    "Verify hive strapping and ensure hive body is securely anchored against heavy wind."
                ),
            })

        # 5. Alert Deduplication / Cooldown
        created_or_active_alerts: List[HiveAlert] = []
        cooldown_delta = timedelta(minutes=settings.ALERT_COOLDOWN_MINUTES)
        now_utc = datetime.now(timezone.utc)

        for alert_spec in alerts_to_emit:
            # Check for existing OPEN alert for same hive and alert_type within cooldown
            existing = (
                db.query(HiveAlert)
                .filter(
                    HiveAlert.hive_id == hive.id,
                    HiveAlert.alert_type == alert_spec["alert_type"],
                    HiveAlert.status == AlertStatus.OPEN,
                    HiveAlert.created_at >= (now_utc - cooldown_delta),
                )
                .first()
            )

            if existing is not None:
                # Deduplicate: do not spam new alert
                created_or_active_alerts.append(existing)
            else:
                # Create and persist new alert
                new_alert = HiveAlert(
                    hive_id=hive.id,
                    telemetry_id=reading.id,
                    alert_type=alert_spec["alert_type"],
                    severity=alert_spec["severity"],
                    title=alert_spec["title"],
                    message=alert_spec["message"],
                    recommended_action=alert_spec["recommended_action"],
                    status=AlertStatus.OPEN,
                    created_at=now_utc,
                )
                db.add(new_alert)
                db.commit()
                db.refresh(new_alert)
                created_or_active_alerts.append(new_alert)

        return max_severity, anomalies, created_or_active_alerts

    @staticmethod
    def get_health_summary(
        db: Session,
        hive: Hive,
    ) -> HiveHealthSummaryResponse:
        """
        Generate full health status summary for a hive including 24h trends,
        active alerts, and staleness detection.
        """
        now_utc = datetime.now(timezone.utc)
        one_day_ago = now_utc - timedelta(hours=24)

        # 1. Latest Reading
        latest = (
            db.query(HiveTelemetry)
            .filter(HiveTelemetry.hive_id == hive.id)
            .order_by(HiveTelemetry.timestamp.desc())
            .first()
        )

        anomalies: List[str] = []
        max_severity = AlertSeverity.NORMAL

        # 2. Check Missing / Stale Telemetry
        # Production-safe heuristic: only evaluate missing telemetry if the hive has active devices.
        active_devices = (
            db.query(HiveDevice)
            .filter(HiveDevice.hive_id == hive.id, HiveDevice.is_active.is_(True))
            .all()
        )

        stale_cutoff = now_utc - timedelta(minutes=settings.HIVE_TELEMETRY_STALE_MINUTES)
        if latest is None:
            if not active_devices:
                # Newly registered hive with no hardware installed yet - unmonitored state (no false alarm)
                anomalies.append("UNMONITORED_HIVE")
            else:
                # Hardware active and installed, but waiting for initial reading
                anomalies.append("NO_TELEMETRY_RECORDED")
                max_severity = AlertSeverity.LOW
        else:
            latest_ts = latest.timestamp
            if latest_ts.tzinfo is None:
                latest_ts = latest_ts.replace(tzinfo=timezone.utc)
            if latest_ts < stale_cutoff:
                anomalies.append("MISSING_TELEMETRY")
                max_severity = AlertSeverity.MEDIUM

                # Check if MISSING_TELEMETRY alert exists or create
                cooldown_delta = timedelta(minutes=settings.ALERT_COOLDOWN_MINUTES)
                existing_missing_alert = (
                    db.query(HiveAlert)
                    .filter(
                        HiveAlert.hive_id == hive.id,
                        HiveAlert.alert_type == AlertType.MISSING_TELEMETRY.value,
                        HiveAlert.status == AlertStatus.OPEN,
                        HiveAlert.created_at >= (now_utc - cooldown_delta),
                    )
                    .first()
                )
                if not existing_missing_alert:
                    new_missing_alert = HiveAlert(
                        hive_id=hive.id,
                        telemetry_id=latest.id,
                        alert_type=AlertType.MISSING_TELEMETRY.value,
                        severity=AlertSeverity.MEDIUM,
                        title="Possible abnormal hive condition detected: Missing telemetry",
                        message=(
                            f"No telemetry has been received from Hive {hive.hive_code} since "
                            f"{latest_ts.strftime('%Y-%m-%d %H:%M:%S UTC')}, exceeding timeout "
                            f"({settings.HIVE_TELEMETRY_STALE_MINUTES} minutes)."
                        ),
                        recommended_action=(
                            "Inspect device power, battery level, antenna connection, and local wireless coverage."
                        ),
                        status=AlertStatus.OPEN,
                        created_at=now_utc,
                    )
                    db.add(new_missing_alert)
                    db.commit()

        # 3. 24h Statistics
        stats = (
            db.query(
                func.avg(HiveTelemetry.temperature_c).label("avg_temp"),
                func.avg(HiveTelemetry.humidity_percent).label("avg_hum"),
            )
            .filter(
                HiveTelemetry.hive_id == hive.id,
                HiveTelemetry.timestamp >= one_day_ago,
            )
            .first()
        )

        avg_temp = Decimal(str(round(stats.avg_temp, 2))) if stats and stats.avg_temp else None
        avg_hum = Decimal(str(round(stats.avg_hum, 2))) if stats and stats.avg_hum else None

        # 24h weight delta (first vs latest in window)
        first_in_24h = (
            db.query(HiveTelemetry)
            .filter(
                HiveTelemetry.hive_id == hive.id,
                HiveTelemetry.timestamp >= one_day_ago,
            )
            .order_by(HiveTelemetry.timestamp.asc())
            .first()
        )
        weight_delta = None
        if latest and first_in_24h:
            weight_delta = Decimal(str(round(latest.weight_kg - first_in_24h.weight_kg, 2)))

        # 4. Query Active Alerts
        active_alerts = (
            db.query(HiveAlert)
            .filter(
                HiveAlert.hive_id == hive.id,
                HiveAlert.status != AlertStatus.RESOLVED,
            )
            .order_by(HiveAlert.created_at.desc())
            .all()
        )

        for a in active_alerts:
            max_severity = HealthEngine._escalate(max_severity, a.severity)
            if a.alert_type not in anomalies:
                anomalies.append(a.alert_type)

        # 5. Determine Overall Health Status
        if max_severity in (AlertSeverity.CRITICAL, AlertSeverity.HIGH):
            health_status = "CRITICAL"
            summary = (
                f"Hive {hive.hive_code} exhibits significant environmental or mechanical deviations. "
                "Immediate inspection is recommended."
            )
        elif max_severity in (AlertSeverity.MEDIUM, AlertSeverity.LOW):
            health_status = "NEEDS_ATTENTION"
            summary = (
                f"Hive {hive.hive_code} has minor telemetry deviations. "
                "Monitor conditions and check apiary during next scheduled visit."
            )
        else:
            health_status = "HEALTHY"
            summary = f"Hive {hive.hive_code} telemetry is stable and within normal colony operating parameters."

        metrics = HiveHealthMetrics(
            latest_reading=HiveTelemetryResponse.model_validate(latest) if latest else None,
            avg_temperature_24h=avg_temp,
            avg_humidity_24h=avg_hum,
            weight_delta_24h=weight_delta,
            active_alerts_count=len(active_alerts),
            last_seen_at=latest.timestamp if latest else None,
        )

        return HiveHealthSummaryResponse(
            hive_id=hive.id,
            hive_code=hive.hive_code,
            health_status=health_status,
            severity=max_severity,
            summary=summary,
            metrics=metrics,
            anomalies=anomalies,
            active_alerts=[HiveAlertResponse.model_validate(a) for a in active_alerts],
        )

    @staticmethod
    def _escalate(current: AlertSeverity, new_sev: AlertSeverity) -> AlertSeverity:
        order = [
            AlertSeverity.NORMAL,
            AlertSeverity.LOW,
            AlertSeverity.MEDIUM,
            AlertSeverity.HIGH,
            AlertSeverity.CRITICAL,
        ]
        if order.index(new_sev) > order.index(current):
            return new_sev
        return current
