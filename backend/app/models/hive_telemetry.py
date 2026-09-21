"""
HiveTelemetry ORM model.

Stores periodic time-series sensor telemetry readings recorded from a beehive.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.hive import Hive
    from app.models.hive_alert import HiveAlert


class HiveTelemetry(Base):
    """Periodic sensor telemetry reading from a Hive."""

    __tablename__ = "hive_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    hive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    device_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    temperature_c: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    humidity_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    sound_level: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    vibration_level: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=False,
    )

    battery_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    is_simulated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    hive: Mapped["Hive"] = relationship("Hive", back_populates="telemetry")
    alerts: Mapped[List["HiveAlert"]] = relationship(
        "HiveAlert", back_populates="telemetry"
    )

    __table_args__ = (
        UniqueConstraint("hive_id", "timestamp", name="uq_hive_telemetry_hive_timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<HiveTelemetry id={self.id!r} hive_id={self.hive_id!r} "
            f"temp={self.temperature_c!r}C hum={self.humidity_percent!r}% "
            f"weight={self.weight_kg!r}kg ts={self.timestamp!r}>"
        )
