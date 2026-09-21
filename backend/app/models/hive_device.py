"""
HiveDevice ORM model.

Represents an IoT sensor node hardware device deployed on a beehive.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.hive import Hive


class HiveDevice(Base):
    """IoT sensor node attached to a Hive."""

    __tablename__ = "hive_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    hive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    device_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    device_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ESP32_SENSOR_NODE",
    )

    firmware_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    device_token_hash: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    hive: Mapped["Hive"] = relationship("Hive", back_populates="devices")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<HiveDevice id={self.id!r} device_id={self.device_id!r} hive_id={self.hive_id!r} is_active={self.is_active!r}>"
