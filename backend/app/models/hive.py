"""
Hive ORM model.

Represents a beehive installed within an apiary.
"""

from datetime import date, datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.apiary import Apiary
    from app.models.hive_alert import HiveAlert
    from app.models.hive_device import HiveDevice
    from app.models.hive_telemetry import HiveTelemetry
    from app.models.honey_harvest import HoneyHarvest


class HiveStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    REMOVED = "REMOVED"


class Hive(Base):
    """Beehive belonging to an apiary."""

    __tablename__ = "hives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    apiary_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("apiaries.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    hive_code: Mapped[str] = mapped_column(String(50), nullable=False)
    hive_type: Mapped[str] = mapped_column(String(50), nullable=False)
    installation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    status: Mapped[HiveStatus] = mapped_column(
        Enum(HiveStatus, name="hivestatus", create_type=True),
        nullable=False,
        default=HiveStatus.ACTIVE,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    apiary: Mapped["Apiary"] = relationship("Apiary", back_populates="hives")
    harvests: Mapped[List["HoneyHarvest"]] = relationship(
        "HoneyHarvest", back_populates="hive"
    )
    devices: Mapped[List["HiveDevice"]] = relationship(
        "HiveDevice", back_populates="hive"
    )
    telemetry: Mapped[List["HiveTelemetry"]] = relationship(
        "HiveTelemetry", back_populates="hive"
    )
    alerts: Mapped[List["HiveAlert"]] = relationship(
        "HiveAlert", back_populates="hive"
    )

    __table_args__ = (
        UniqueConstraint("apiary_id", "hive_code", name="uq_apiary_hive_code"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Hive id={self.id!r} code={self.hive_code!r} apiary_id={self.apiary_id!r} status={self.status!r}>"
