"""
IoT Hive State ORM model.

Shared table used by both the FastAPI backend and the Node.js IoT Mock Server.
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class IoTHiveState(Base):
    __tablename__ = "iot_hive_states"

    hive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hives.id", ondelete="CASCADE"),
        primary_key=True,
    )

    temperature: Mapped[float] = mapped_column(Float, default=34.0, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    sound_level: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    co2_level: Mapped[float] = mapped_column(Float, default=700.0, nullable=False)
    
    activity_level: Mapped[str] = mapped_column(String(50), default="Normal", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Healthy", nullable=False)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    hive = relationship("Hive")

    def __repr__(self) -> str:
        return f"<IoTHiveState hive_id={self.hive_id!r} temp={self.temperature!r} status={self.status!r}>"
