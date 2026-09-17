"""
HiveAlert ORM model and enums.

Tracks health and environmental anomaly alerts generated for beehives.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.hive import Hive
    from app.models.hive_telemetry import HiveTelemetry


class AlertSeverity(str, PyEnum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, PyEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertType(str, PyEnum):
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    LOW_TEMPERATURE = "LOW_TEMPERATURE"
    HIGH_HUMIDITY = "HIGH_HUMIDITY"
    LOW_HUMIDITY = "LOW_HUMIDITY"
    RAPID_WEIGHT_DROP = "RAPID_WEIGHT_DROP"
    ABNORMAL_SOUND = "ABNORMAL_SOUND"
    ABNORMAL_VIBRATION = "ABNORMAL_VIBRATION"
    MISSING_TELEMETRY = "MISSING_TELEMETRY"
    COMBINED_ANOMALY = "COMBINED_ANOMALY"


class HiveAlert(Base):
    """Health or anomaly alert for a beehive."""

    __tablename__ = "hive_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    hive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    telemetry_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("hive_telemetry.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alertseverity", create_type=True),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommended_action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alertstatus", create_type=True),
        nullable=False,
        default=AlertStatus.OPEN,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    hive: Mapped["Hive"] = relationship("Hive", back_populates="alerts")
    telemetry: Mapped[Optional["HiveTelemetry"]] = relationship(
        "HiveTelemetry", back_populates="alerts"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<HiveAlert id={self.id!r} hive_id={self.hive_id!r} "
            f"type={self.alert_type!r} severity={self.severity!r} status={self.status!r}>"
        )
